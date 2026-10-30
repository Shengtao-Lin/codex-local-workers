"""Diagnostic baseline comparison context; historical lines never grant current reads."""

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path


def baseline_context(runtime, reviewer):
    manifest = json.loads(
        (runtime.run_root / "preimages.json").read_text(encoding="utf-8")
    )
    changes = json.loads(
        (runtime.run_root / "changes.json").read_text(encoding="utf-8")
    )
    changed = {item["path"]: item for item in changes["actual_relevant_changes"]}
    result = []
    total_chars = 0
    for entry in manifest:
        path = entry["path"]
        if not entry["existed"] or path not in changed:
            continue
        normalized, _ = runtime._assert_read_allowed(path)
        if (
            normalized != path
            or changed[path]["before"].get("sha256") != entry["sha256"]
        ):
            raise reviewer.ReviewError("baseline identity does not match actual change")
        expected = runtime.run_root / "preimages" / Path(path)
        relative = expected.relative_to(runtime.repo_root).as_posix()
        if entry["archive_path"] != relative:
            raise reviewer.ReviewError("unexpected baseline archive path")
        runtime.editor._assert_no_reparse_components(relative)
        content = expected.read_bytes()
        if hashlib.sha256(content).hexdigest() != entry["sha256"]:
            raise reviewer.ReviewError("baseline hash drift")
        lines = content.decode("utf-8-sig").splitlines()
        # Only small full-file preimages: do not silently imply omitted baseline coverage.
        if len(lines) > 200 or total_chars + len(content) > 16000 or len(result) >= 2:
            continue
        total_chars += len(content)
        result.append(
            {
                "path": path,
                "sha256": entry["sha256"],
                "historical": True,
                "lines": [{"line": n, "text": line} for n, line in enumerate(lines, 1)],
                "current_source_read_credit": False,
            }
        )
    return result


def install(reviewer):
    original_payload = reviewer.ReviewerRuntime.initial_payload
    original_prompt = reviewer.ReviewerRuntime.system_prompt

    def payload(runtime):
        result = original_payload(runtime)
        result["historical_source_for_comparison_not_current_reads"] = baseline_context(
            runtime, reviewer
        )
        return result

    def prompt(runtime):
        return original_prompt(runtime) + (
            "\nVerified historical preimages are comparison context, not current source reads or current citation evidence. Compare old and new control flow for preservation requirements: trace the exact returned value, error and side effects on already-supported inputs, not only newly supported inputs. An extension must not transform an already-final value again unless the contract explicitly requires it. Read current source normally and cite only actual current displayed lines. If historical coverage is absent, do not assume it. Report genuine regressions, not implementation-shape preferences."
        )

    reviewer.ReviewerRuntime.initial_payload = payload
    reviewer.ReviewerRuntime.system_prompt = prompt


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--snapshot", type=Path, required=True)
    args, remaining = parser.parse_known_args()
    spec = importlib.util.spec_from_file_location(
        "baseline_review_diagnostic",
        args.snapshot / ".local-agents/reviewer-runtime.py",
    )
    reviewer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = reviewer
    spec.loader.exec_module(reviewer)
    install(reviewer)
    sys.argv = ["reviewer-runtime.py", *remaining]
    return reviewer.main()


if __name__ == "__main__":
    raise SystemExit(main())
