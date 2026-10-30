"""Executed independent current-input evidence; never records acceptance itself."""

import argparse
import os
import xml.etree.ElementTree as ET
from pathlib import Path

from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read
from layer_isolation import command, verify_hashes
from tool_awaitable_trial import PYTHON, TARGET


def junit_counts(path):
    cases = list(ET.parse(path).getroot().iter("testcase"))
    return {
        "tests": len(cases),
        **{
            tag: sum(case.find(tag) is not None for case in cases)
            for tag in ("failure", "error", "skipped")
        },
    }


def verify(root, fixture_version, label):
    root = root.resolve()
    root.relative_to(WORK.resolve())
    if not label or any(
        c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in label
    ):
        raise ValueError("unique safe verification label required")
    provenance = read(
        KIT / f"benchmarks/fixtures/tool-awaitable-v{fixture_version}/provenance.json"
    )
    verify_hashes(KIT.parent / "agent-runtime-kit", provenance["original_files"])
    verify_hashes(
        root, {p: sha for p, sha in provenance["files"].items() if p != TARGET}
    )
    destination = root / ".agent" / label
    if destination.with_suffix(".json").exists():
        raise ValueError("existing verification cannot be overwritten")
    source_before = digest(root / TARGET)
    checks = []
    static_tests = [
        "tests/unit/test_awaitable.py",
        "tests/unit/test_async_preservation.py",
    ]
    if fixture_version >= 9:
        static_tests.append("tests/unit/test_async_generality.py")
    if fixture_version >= 10:
        static_tests.append("tests/unit/test_caller_context.py")
    if fixture_version == 12:
        static_tests.append("tests/unit/test_plain_result.py")
    expected_tests = {8: 13, 9: 16, 10: 18, 12: 19}[fixture_version]
    commands = [
        [
            "pytest",
            "-o",
            "pythonpath=src",
            "tests",
            "-q",
            "-p",
            "no:cacheprovider",
            "--basetemp=.agent/" + label + "-temp",
            "--junitxml=.agent/" + label + ".xml",
        ],
        [
            "ruff",
            "format",
            "--check",
            TARGET,
            *static_tests,
        ],
        [
            "ruff",
            "check",
            TARGET,
            *static_tests,
        ],
        ["pyright", "--project", ".agent/pyright.json", "--pythonpath", str(PYTHON)],
    ]
    for argv in commands:
        checks.append(command(root, [str(PYTHON), "-B", "-m", *argv]))
    old_value = os.environ.get("LW_COMPAT_CODE_ROOT")
    os.environ["LW_COMPAT_CODE_ROOT"] = str(root)
    try:
        extra = command(
            root,
            [
                str(PYTHON),
                "-B",
                "-m",
                "pytest",
                "-c",
                str(root / "pyproject.toml"),
                "--rootdir=" + root.as_posix(),
                "-o",
                "pythonpath=" + (root / "src").as_posix(),
                str(
                    KIT
                    / "benchmarks/fixtures/tool-awaitable-extra/primary_async_identity.py"
                ),
                "-q",
                "-p",
                "no:cacheprovider",
                "--basetemp=.agent/" + label + "-extra-temp",
                "--junitxml=.agent/" + label + "-extra.xml",
            ],
        )
    finally:
        if old_value is None:
            del os.environ["LW_COMPAT_CODE_ROOT"]
        else:
            os.environ["LW_COMPAT_CODE_ROOT"] = old_value
    counts = junit_counts(destination.with_suffix(".xml"))
    extra_counts = junit_counts(root / ".agent" / (label + "-extra.xml"))
    verify_hashes(
        root, {p: sha for p, sha in provenance["files"].items() if p != TARGET}
    )
    if digest(root / TARGET) != source_before:
        raise ValueError("source changed during independent verification")
    result = {
        "checks": checks,
        "primary_only_generality": extra,
        "tests": counts["tests"],
        "junit": counts,
        "generality_junit": extra_counts,
        "source_sha256": source_before,
        "protected_unchanged": True,
        "sibling_unchanged": True,
        "passed": all(check["exit"] == 0 for check in [*checks, extra])
        and counts == {"tests": expected_tests, "failure": 0, "error": 0, "skipped": 0}
        and extra_counts == {"tests": 3, "failure": 0, "error": 0, "skipped": 0},
        "primary_acceptance": False,
    }
    write(destination.with_suffix(".json"), result)
    print(
        {
            "passed": result["passed"],
            "tests": counts["tests"],
            "generality_exit": extra["exit"],
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("root", type=Path)
    parser.add_argument("label")
    parser.add_argument(
        "--fixture-version", type=int, choices=(8, 9, 10, 12), default=8
    )
    args = parser.parse_args()
    verify(args.root, args.fixture_version, args.label)
