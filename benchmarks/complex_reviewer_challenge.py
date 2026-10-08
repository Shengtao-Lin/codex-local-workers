"""Independent synthetic-archive Reviewer control; never a Coder success claim."""

import argparse
import ast
import copy
import difflib
import hashlib
import json
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

from capability_transfer_cases import transfer_cases
from complex_fixture_cases import transaction_case

KIT = Path(__file__).resolve().parents[1]
WORK = KIT / "benchmarks/work/mixed-v1/reviewer-controls"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)


def exception_lines(source):
    return sorted(
        {
            line
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.ExceptHandler)
            or (isinstance(node, ast.Try) and node.finalbody)
            for line in range(node.lineno, node.end_lineno + 1)
        }
    )


def classify(
    report,
    variant,
    evidence_lines=(),
    path="src/product/publish.py",
    cleanup="rollback",
):
    findings = report.get("findings") or []
    if variant == "clean":
        return report.get("decision") == "pass_to_primary" and not findings
    return report.get("decision") in ("rework", "escalate") and any(
        finding.get("path") == path
        and finding.get("line") in evidence_lines
        and cleanup in str(finding.get("evidence", "")).lower()
        and any(
            word in str(finding.get("evidence", "")).lower()
            for word in ("original", "mask", "exception")
        )
        for finding in findings
        if isinstance(finding, dict)
    )


def grading_status(report, variant, structural_outcome):
    """A keyword match is triage, never proof of a correct causal finding."""
    return {
        "structural_outcome": structural_outcome,
        "effective_detection": None,
        "requires_primary_adjudication": variant == "hidden",
        "clean_control_passed": (
            variant == "clean"
            and structural_outcome
            and report.get("decision") == "pass_to_primary"
            and not report.get("findings")
        ),
    }


def run(source_root, variant, runtime_root=KIT, family="rollback", ordering=False):
    runtime_root = runtime_root.resolve()
    runtime_root.relative_to(KIT)
    source_root = source_root.resolve()
    source_root.relative_to((KIT / "benchmarks/work/mixed-v1").resolve())
    case = transaction_case()
    identity = f"review-{family}-{variant}-{uuid.uuid4().hex[:12]}"
    root = WORK / identity
    root.mkdir(parents=True, exist_ok=False)
    if family in {"lock-release", "save-cancel"}:
        template = json.loads(
            (KIT / "benchmarks/fixtures/mixed-features-v1.json").read_text(
                encoding="utf-8"
            )
        )["cases"][0]
        transfers, oracles = transfer_cases(template)
        case = next(
            item
            for item in transfers
            if item["case_id"]
            == (
                "transfer-lock-release"
                if family == "lock-release"
                else "transfer-save-cancel"
            )
        )
        oracle_text = case["files"]["tests/test_target.py"]
        if family == "lock-release":
            case["files"]["tests/test_target.py"] = oracle_text.replace(
                "(True,True),", ""
            )
        else:
            case["files"]["tests/test_target.py"] = oracle_text.split(
                '@pytest.mark.parametrize("failed",'
            )[0]
    # Old normal-path tests intentionally lack this boundary. The oracle stays
    # outside packet-readable src/tests and is executed by Primary only.
    for relative in case["files"]:
        if relative == "tests/test_rollback_failure.py":
            continue
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if family in {"lock-release", "save-cancel"}:
            path.write_text(case["files"][relative], encoding="utf-8")
        else:
            path.write_bytes((source_root / relative).read_bytes())
    source_relative = (
        "src/product/target.py"
        if family in {"lock-release", "save-cancel"}
        else "src/product/publish.py"
    )
    source = root / source_relative
    if family in {"lock-release", "save-cancel"}:
        oracle = oracles[case["case_id"]]
        source.write_text(
            oracle["reference"] if variant == "clean" else oracle["mutants"][0],
            encoding="utf-8",
        )
    text = source.read_text(encoding="utf-8")
    original = "    except Exception:\n        await store.rollback()\n        raise\n"
    corrected = "    except Exception:\n        with suppress(Exception):\n            await store.rollback()\n        raise\n"
    if family == "rollback" and original not in text:
        raise ValueError("expected frozen exception-path anchor absent")
    if family == "rollback" and variant == "clean":
        source.write_text(
            "from contextlib import suppress\n\n"
            + text.replace(original, corrected, 1),
            encoding="utf-8",
        )
    (root / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\npythonpath=["src"]\n[tool.ruff]\nline-length=100\ntarget-version="py311"\n[tool.ruff.lint]\nselect=["E4","E7","E9","F"]\n',
        encoding="utf-8",
    )
    config = json.loads(
        (source_root / ".agent/config.json").read_text(encoding="utf-8")
    )
    config["python"] = sys.executable
    config["single_model_residency"] = True
    config_path = root / ".agent/config.json"
    write(config_path, config)
    reference = json.loads(
        (source_root / ".agent/atomic-publish-reference.json").read_text()
    )
    packet = copy.deepcopy(reference)
    packet.update(task_id=identity, feature_id=identity, run_id=identity)
    packet["review_feedback"] = []
    packet["implementation_guidance"] = []
    if family in {"lock-release", "save-cancel"}:
        packet["goal"] = case["goal"]
        packet["scope"]["modify"] = [source_relative]
        packet["scope"]["readonly"] = [
            "src/product/__init__.py",
            "tests/test_target.py",
        ]
        packet["focused_tests"] = ["tests/test_target.py"]
        packet["edit_targets"] = [
            {"path": source_relative, "anchor": case["units"][0]["anchor"]}
        ]
        packet["required_behavior"] = [
            {"id": packet["unit_id"], "risk_floor": "high", "text": case["goal"]}
        ]
        packet["required_order"] = (
            case["units"][0]["required_order"] if ordering else []
        )
        packet["forbidden_orderings"] = (
            case["units"][0]["forbidden_orderings"] if ordering else []
        )
    archive = root / ".agent/tasks" / identity / "runs" / identity
    write(archive / "packet.json", packet)
    commands = [
        [sys.executable, "-m", "ruff", "format", "src", "tests"],
        [
            sys.executable,
            "-B",
            "-m",
            "pytest",
            *packet["focused_tests"],
            "-q",
            "-p",
            "no:cacheprovider",
            f"--junitxml={archive / 'pytest.xml'}",
        ],
        [sys.executable, "-m", "ruff", "format", "--check", "src", "tests"],
        [sys.executable, "-m", "ruff", "check", "src", "tests"],
    ]
    executions = [
        subprocess.run(
            command, cwd=root, capture_output=True, text=True, check=False, timeout=120
        )
        for command in commands
    ]
    if any(result.returncode for result in executions):
        raise ValueError(
            "fixture preflight failed: "
            + str([result.stdout + result.stderr for result in executions])
        )
    tests = list(ET.parse(archive / "pytest.xml").getroot().iter("testcase"))
    if not tests or any(list(test) for test in tests):
        raise ValueError("expected executed passing JUnit cases")
    facts = {}
    for relative in case["files"]:
        path = root / relative
        if path.is_file():
            raw = path.read_bytes()
            facts[relative] = {
                "path": relative,
                "exists": True,
                "kind": "file",
                "sha256": hashlib.sha256(raw).hexdigest(),
                "size": len(raw),
            }
    write(
        archive / "validation.json",
        {
            "status": "passed",
            "focused_tests": {
                "status": "passed",
                "inputs_unchanged": True,
                "junit": {"available": True, "executed": len(tests)},
            },
            "configured_checks": [
                {"id": name, "status": "passed", "exit_code": 0}
                for name in ("ruff-format", "ruff-check")
            ],
        },
    )
    write(archive / "post-state.json", {"validation_inputs": facts})
    write(archive / "handoff.json", {"status": "ready_for_review"})
    write(
        archive / "completed.json",
        {"status": "ready_for_review", "synthetic_benchmark_archive": True},
    )
    diff = ""
    for relative in packet["scope"]["modify"]:
        diff += "".join(
            difflib.unified_diff(
                case["files"][relative].splitlines(keepends=True),
                (root / relative).read_text().splitlines(keepends=True),
                fromfile="a/" + relative,
                tofile="b/" + relative,
            )
        )
    (archive / "cumulative.diff").write_text(diff, encoding="utf-8")
    oracle = (
        oracle_text
        if family in {"lock-release", "save-cancel"}
        else (source_root / ".agent/primary-rollback-probe.py").read_text(
            encoding="utf-8"
        )
    )
    oracle = oracle.replace(
        'Path(__file__).resolve().parents[1] / "src"',
        'Path(__file__).resolve().parent / "src"',
    )
    (root / "primary-oracle.py").write_text(oracle, encoding="utf-8")
    check = subprocess.run(
        (
            [
                sys.executable,
                "-B",
                "-m",
                "pytest",
                "primary-oracle.py",
                "-q",
                "-p",
                "no:cacheprovider",
            ]
            if family in {"lock-release", "save-cancel"}
            else [sys.executable, "-B", "primary-oracle.py"]
        ),
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if (check.returncode == 0) != (variant == "clean"):
        raise ValueError("oracle does not distinguish variant")
    request = root / ".agent/request.json"
    write(
        request,
        {
            "schema_version": 1,
            "task_id": identity,
            "unit_id": packet["unit_id"],
            "run_id": identity,
            "review_id": identity,
        },
    )
    report_path = root / ".agent/reviewer-report.json"
    write(
        root / "freeze.json",
        {
            "synthetic_archive": True,
            "variant": variant,
            "family": family,
            "evidence_lines": exception_lines(source.read_text(encoding="utf-8")),
            "files": facts,
            "python_version": sys.version,
            "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
            "drivers": {
                str(path.relative_to(KIT)): hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
                for path in (
                    Path(__file__),
                    runtime_root / ".local-agents/reviewer-runtime.py",
                    runtime_root / ".local-agents/worker-runtime.py",
                    runtime_root / ".local-agents/model-client.py",
                )
                if path.exists()
            },
            "feedback_supplied": False,
            "primary_accepted": False,
        },
    )
    invocation = subprocess.run(
        [
            sys.executable,
            "-B",
            str(runtime_root / ".local-agents/local-review.py"),
            "--request",
            str(request),
            "--config",
            str(config_path),
            "--report",
            str(report_path),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=720,
    )
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    result = {
        "workspace": str(root),
        "variant": variant,
        "family": family,
        "ordering_obligations_retained": ordering,
        "runtime_root": str(runtime_root),
        "synthetic_archive": True,
        "coder_invoked": False,
        "primary_accepted": False,
        "reviewer_model": config["reviewer_model"],
        "focused_tests_executed": len(tests),
        "oracle_exit": check.returncode,
        "reviewer_exit": invocation.returncode,
        "reviewer_decision": report.get("decision"),
        "findings": report.get("findings"),
        "expected_outcome": classify(
            report,
            variant,
            exception_lines(source.read_text(encoding="utf-8")),
            source_relative,
            "release" if family == "lock-release" else "rollback",
        )
        and invocation.returncode == 0,
        "output_tail": (invocation.stdout + invocation.stderr)[-1500:],
    }
    result.update(grading_status(report, variant, result["expected_outcome"]))
    result["expected_outcome_qualification"] = (
        "Legacy structural triage only, not effective defect detection or feature acceptance"
    )
    write(root / "challenge-result.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--variant", choices=("hidden", "clean"), required=True)
    parser.add_argument("--runtime-root", type=Path, default=KIT)
    parser.add_argument(
        "--ordering",
        action="store_true",
        help="Retain exact lock-release ordering obligations",
    )
    parser.add_argument(
        "--family",
        choices=("rollback", "lock-release", "save-cancel"),
        default="rollback",
    )
    args = parser.parse_args()
    result = run(
        args.source_root, args.variant, args.runtime_root, args.family, args.ordering
    )
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["expected_outcome"] else 1)
