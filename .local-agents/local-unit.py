"""Run one Coder unit and dispatch its verified result to Local Reviewer."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import sys
import uuid
from collections import Counter
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent


class HandoffError(ValueError):
    pass


def _object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise HandoffError(f"expected JSON object: {path}")
    return value


def _identifier(value: Any, name: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value):
        raise HandoffError(f"invalid {name}")
    return value


def _same_content(expected: dict[str, Any], current: Path) -> bool:
    if expected.get("exists") is False:
        return not current.exists()
    if expected.get("kind") != "file" or not current.is_file():
        return False
    return hashlib.sha256(current.read_bytes()).hexdigest() == expected.get("sha256")


def _retryable_reviewer_startup_failure(report: dict[str, Any]) -> bool:
    infra = report.get("infra_failure")
    if report.get("decision") != "failed" or not isinstance(infra, dict):
        return False
    reason = str(infra.get("reason", ""))
    return infra.get("reason_code") == "model_request_timeout" or (
        infra.get("reason_code") == "http_4xx" and "peg-native format" in reason
    )


def _cumulative_diff_paths(content: str) -> set[str]:
    """Read exact authored paths from the trusted run's forward unified diff."""
    paths: set[str] = set()
    previous: str | None = None
    for line in content.splitlines():
        if line.startswith("Binary files differ: "):
            path = line.removeprefix("Binary files differ: ")
            if not path or path.startswith("/") or ".." in Path(path).parts:
                raise HandoffError("cumulative diff has an invalid binary path")
            paths.add(path)
        elif line.startswith("--- a/"):
            previous = line[6:]
        elif line.startswith("+++ b/"):
            current = line[6:]
            if not previous or previous != current or not current or ".." in Path(current).parts:
                raise HandoffError("cumulative diff path pair is malformed")
            paths.add(current)
            previous = None
    if previous is not None:
        raise HandoffError("cumulative diff has an incomplete path pair")
    return paths


def _introduced_local_import_violations(
    repo_root: Path, run_root: Path, packet: dict, changed_paths: set[str]
) -> list[str]:
    """Find newly added static imports of local files outside packet read scope."""
    manifest = json.loads((run_root / "preimages.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, list):
        raise HandoffError("canonical preimage manifest is malformed")
    originals = {item.get("path"): item for item in manifest if isinstance(item, dict)}
    allowed = (
        packet["scope"].get("read", []) + packet["scope"]["modify"] + packet["scope"]["create"]
    )
    forbidden = packet["scope"].get("forbidden", [])

    def covered(path: str, roots: list[str]) -> bool:
        return any(path == root or path.startswith(root + "/") for root in roots)

    def local_files(source: str, node: ast.Import | ast.ImportFrom) -> set[str]:
        paths: set[str] = set()
        if isinstance(node, ast.Import):
            module_names = [alias.name for alias in node.names]
            bases = [PurePosixPath(""), PurePosixPath("src")]
        else:
            module_names = [node.module or ""]
            module_names.extend(
                ".".join(filter(None, [node.module or "", alias.name]))
                for alias in node.names
                if alias.name != "*"
            )
            if node.level:
                parent = PurePosixPath(source).parent
                for _ in range(node.level - 1):
                    parent = parent.parent
                bases = [parent]
            else:
                bases = [PurePosixPath(""), PurePosixPath("src")]
        for base in bases:
            for module in module_names:
                components = [part for part in module.split(".") if part]
                for count in range(1, len(components) + 1):
                    stem = base.joinpath(*components[:count])
                    for candidate in (f"{stem}.py", f"{stem}/__init__.py"):
                        if (repo_root / candidate).is_file():
                            paths.add(candidate)
                if not components:
                    candidate = (base / "__init__.py").as_posix()
                    if (repo_root / candidate).is_file():
                        paths.add(candidate)
        return paths

    violations: list[str] = []
    for relative in sorted(changed_paths):
        if not relative.endswith(".py"):
            continue
        item = originals.get(relative)
        if not isinstance(item, dict):
            raise HandoffError(f"canonical preimage is missing: {relative}")
        original = run_root / "preimages" / relative
        try:
            before = original.read_text(encoding="utf-8-sig") if item.get("existed") else ""
            after = (repo_root / relative).read_text(encoding="utf-8-sig")
            previous = ast.parse(before)
            current = ast.parse(after)
        except (OSError, UnicodeError, SyntaxError) as exc:
            raise HandoffError(f"changed Python import evidence is unreadable: {relative}") from exc
        if item.get("existed") and hashlib.sha256(original.read_bytes()).hexdigest() != item.get(
            "sha256"
        ):
            raise HandoffError(f"canonical preimage hash differs: {relative}")
        prior = Counter(
            ast.dump(node, include_attributes=False)
            for node in ast.walk(previous)
            if isinstance(node, (ast.Import, ast.ImportFrom))
        )
        for node in ast.walk(current):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            signature = ast.dump(node, include_attributes=False)
            if prior[signature]:
                prior[signature] -= 1
                continue
            for target in sorted(local_files(relative, node)):
                if not covered(target, allowed) or covered(target, forbidden):
                    violations.append(f"{relative}:{node.lineno} imports out-of-scope {target}")
    return violations


def verify_handoff(repo_root: Path, coder_report: dict[str, Any]) -> dict[str, str]:
    if coder_report.get("status") != "ready_for_review":
        raise HandoffError("Coder is not ready_for_review")
    identity = coder_report.get("identity") or {}
    task_id = _identifier(identity.get("task_id"), "task_id")
    unit_id = _identifier(identity.get("unit_id"), "unit_id")
    run_id = _identifier(identity.get("run_id"), "run_id")
    run_root = repo_root / ".agent" / "tasks" / task_id / "runs" / run_id
    packet = _object(run_root / "packet.json")
    completed = _object(run_root / "completed.json")
    handoff = _object(run_root / "handoff.json")
    validation = _object(run_root / "validation.json")
    changes = _object(run_root / "changes.json")
    post_state = _object(run_root / "post-state.json")
    if (
        packet.get("task_id") != task_id
        or packet.get("unit_id") != unit_id
        or packet.get("run_id") != run_id
        or completed.get("status") != "ready_for_review"
        or handoff.get("status") != "ready_for_review"
    ):
        raise HandoffError("Coder report does not match the completed canonical run")
    focused = validation.get("focused_tests") or {}
    junit = focused.get("junit") or {}
    if (
        validation.get("status") != "passed"
        or focused.get("status") != "passed"
        or focused.get("inputs_unchanged") is not True
        or not junit.get("available")
        or type(junit.get("executed")) is not int
        or junit["executed"] < 1
        or any(item.get("status") != "passed" for item in validation.get("configured_checks", []))
    ):
        raise HandoffError("Coder deterministic validation is incomplete or failed")
    if changes.get("unattributed_relevant_changes"):
        raise HandoffError("unattributed relevant changes require Primary inspection")
    allowed = set(packet["scope"]["modify"] + packet["scope"]["create"])
    reported = {item["path"] for item in handoff.get("changed_files", [])}
    actual = {item["path"] for item in changes.get("runtime_edits", [])}
    if not reported <= allowed or reported != actual:
        raise HandoffError("Coder changed paths are not fully attributed to packet scope")
    expected_inputs = post_state.get("validation_inputs")
    if not isinstance(expected_inputs, dict) or not expected_inputs:
        raise HandoffError("canonical validation inputs are missing")
    focused_paths = packet.get("focused_tests")
    focused_argv = focused.get("argv") or []
    if (
        not isinstance(focused_paths, list)
        or not focused_paths
        or not all(
            isinstance(selector, str)
            and selector.split("::", 1)[0] in expected_inputs
            and (
                "::" not in selector
                or (isinstance(focused_argv, list) and selector in focused_argv)
            )
            for selector in focused_paths
        )
    ):
        raise HandoffError("focused tests are missing from canonical validation inputs")
    for relative, expected in expected_inputs.items():
        if not isinstance(relative, str) or not isinstance(expected, dict):
            raise HandoffError("invalid canonical validation input")
        current = (repo_root / relative).resolve()
        if repo_root not in current.parents or not _same_content(expected, current):
            raise HandoffError(f"validation input changed after Coder: {relative}")
    diff_path = run_root / "cumulative.diff"
    if not diff_path.is_file() or (reported and not diff_path.read_text(encoding="utf-8").strip()):
        raise HandoffError("canonical cumulative diff is missing")
    if _cumulative_diff_paths(diff_path.read_text(encoding="utf-8")) != reported:
        raise HandoffError("cumulative diff paths differ from authorized runtime edits")
    import_violations = _introduced_local_import_violations(repo_root, run_root, packet, reported)
    if import_violations:
        raise HandoffError(
            "new local imports exceed packet read scope: " + "; ".join(import_violations)
        )
    return {"task_id": task_id, "unit_id": unit_id, "run_id": run_id}


def run_unit(
    repo_root: Path,
    packet: Path,
    config: Path,
    coder_report_path: Path,
    review_report_path: Path,
) -> tuple[int, dict[str, Any]]:
    prior_coder_mtime = coder_report_path.stat().st_mtime_ns if coder_report_path.exists() else None
    coder = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_DIR / "local-code.py"),
            "--packet",
            str(packet),
            "--config",
            str(config),
            "--report",
            str(coder_report_path),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if (
        prior_coder_mtime is not None
        and coder_report_path.exists()
        and coder_report_path.stat().st_mtime_ns == prior_coder_mtime
    ):
        return 2, {
            "status": "failed",
            "stage": "coder_report",
            "reason": "Coder did not write a fresh report",
        }
    try:
        coder_report = _object(coder_report_path)
    except (OSError, ValueError) as exc:
        return 2, {"status": "failed", "stage": "coder_report", "reason": str(exc)}
    result: dict[str, Any] = {
        "status": coder_report.get("status"),
        "coder_report": str(coder_report_path),
        "reviewer_decision": None,
    }
    if coder.returncode != 0 or coder_report.get("status") != "ready_for_review":
        result["next_action_required"] = coder_report.get("next_action_required")
        return coder.returncode or 2, result
    try:
        identity = verify_handoff(repo_root, coder_report)
        request = {
            "schema_version": 1,
            **identity,
            "review_id": "auto-" + uuid.uuid4().hex,
        }
        request_path = (
            repo_root
            / ".agent"
            / "tasks"
            / identity["task_id"]
            / "runs"
            / identity["run_id"]
            / "auto-review-request.json"
        )
        with request_path.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(request, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        result["review_request"] = str(request_path)
    except (HandoffError, OSError, ValueError, KeyError, TypeError) as exc:
        result.update(
            {
                "stage": "handoff_gate",
                "reason": str(exc),
                "next_action_required": "primary_inspect_handoff",
            }
        )
        return 2, result
    result["review_attempts"] = []
    for attempt in (1, 2):
        prior_review_mtime = (
            review_report_path.stat().st_mtime_ns if review_report_path.exists() else None
        )
        argv = [
            sys.executable,
            str(SCRIPT_DIR / "local-review.py"),
            "--request",
            str(request_path),
            "--config",
            str(config),
            "--report",
            str(review_report_path),
        ]
        if attempt == 2:
            configured_tokens = int(_object(config).get("reviewer_max_tokens", 4096))
            argv.extend(["--max-tokens", str(max(512, configured_tokens // 2))])
        reviewed = subprocess.run(
            argv,
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if (
            prior_review_mtime is not None
            and review_report_path.exists()
            and review_report_path.stat().st_mtime_ns == prior_review_mtime
        ):
            result.update(
                {
                    "stage": "reviewer_report",
                    "reason": "Reviewer did not write a fresh report",
                    "next_action_required": "primary_inspect_reviewer_failure",
                }
            )
            return 2, result
        try:
            review_report = _object(review_report_path)
        except (OSError, ValueError) as exc:
            result.update(
                {
                    "stage": "reviewer_report",
                    "reason": str(exc),
                    "next_action_required": "primary_inspect_reviewer_failure",
                }
            )
            return 2, result
        result["review_attempts"].append(
            {
                "review_id": request["review_id"],
                "decision": review_report.get("decision"),
                "infra_failure": review_report.get("infra_failure"),
            }
        )
        if attempt == 2 or not _retryable_reviewer_startup_failure(review_report):
            break
        try:
            verify_handoff(repo_root, coder_report)
            request = {**request, "review_id": "auto-" + uuid.uuid4().hex}
            request_path = request_path.with_name("auto-review-retry-request.json")
            with request_path.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(request, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
            result["review_retry_request"] = str(request_path)
        except (HandoffError, OSError, ValueError, KeyError, TypeError) as exc:
            result.update(
                {
                    "stage": "handoff_gate",
                    "reason": str(exc),
                    "next_action_required": "primary_inspect_handoff",
                }
            )
            return 2, result
    result.update(
        {
            "reviewer_decision": review_report.get("decision"),
            "review_report": str(review_report_path),
            "next_action_required": review_report.get("next_action_required"),
        }
    )
    if reviewed.returncode != 0 or review_report.get("decision") not in {
        "pass_to_primary",
        "rework",
        "escalate",
    }:
        result["stage"] = "reviewer"
        result["reason"] = review_report.get("failure_reason") or reviewed.stderr[-500:]
        return 2, result
    return 0, result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--config", type=Path, default=SCRIPT_DIR / "config.json")
    parser.add_argument(
        "--coder-report", type=Path, default=Path(".agent/last-local-coder-report.json")
    )
    parser.add_argument(
        "--review-report", type=Path, default=Path(".agent/last-local-review-report.json")
    )
    args = parser.parse_args()
    repo_root = Path.cwd().resolve()
    code, result = run_unit(
        repo_root,
        args.packet.resolve(),
        args.config.resolve(),
        args.coder_report.resolve(),
        args.review_report.resolve(),
    )
    print(json.dumps(result, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
