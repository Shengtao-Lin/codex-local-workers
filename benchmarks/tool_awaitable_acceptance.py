"""Independent current-input verification of the recovered actual artifact."""

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from capability_fit import WORK, write
from inherited_context_recovery import digest, read
from layer_isolation import command, verify_hashes
from tool_awaitable_trial import PYTHON, TARGET


def verify(root):
    root = root.resolve()
    root.relative_to(WORK.resolve())
    output = root / ".agent/primary-recovered-verification.json"
    if output.exists():
        raise ValueError("immutable verification already exists")
    manifest = read(root / ".agent/manifest.json")
    verify_hashes(root, {p: sha for p, sha in manifest["files"].items() if p != TARGET})
    before = digest(root / TARGET)
    commands = [
        [
            "pytest",
            "-o",
            "pythonpath=src",
            "tests",
            ".agent/primary_plain_once.py",
            "-q",
            "-p",
            "no:cacheprovider",
            "--basetemp=.agent/primary-recovered-temp",
            "--junitxml=.agent/primary-recovered.xml",
        ],
        ["ruff", "format", "--check", TARGET, "tests/unit/test_awaitable.py"],
        ["ruff", "check", TARGET, "tests/unit/test_awaitable.py"],
        ["pyright", "--project", ".agent/pyright.json", "--pythonpath", str(PYTHON)],
    ]
    checks = [command(root, [str(PYTHON), "-B", "-m", *argv]) for argv in commands]
    cases = list(
        ET.parse(root / ".agent/primary-recovered.xml").getroot().iter("testcase")
    )
    counts = {
        "tests": len(cases),
        **{
            tag: sum(case.find(tag) is not None for case in cases)
            for tag in ("failure", "error", "skipped")
        },
    }
    verify_hashes(root, {p: sha for p, sha in manifest["files"].items() if p != TARGET})
    facts = {
        "checks": checks,
        "junit": counts,
        "source_sha256": before,
        "new_probe_sha256": digest(root / ".agent/primary_plain_once.py"),
        "source_unchanged": before == digest(root / TARGET),
        "protected_unchanged": True,
        "passed": all(check["exit"] == 0 for check in checks)
        and counts == {"tests": 12, "failure": 0, "error": 0, "skipped": 0}
        and before == digest(root / TARGET),
        "credit": "Recovered actual artifact; not new independent fresh success",
    }
    write(output, facts)
    print(
        json.dumps(
            {"passed": facts["passed"], "junit": counts, "source_sha256": before}
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("root", type=Path)
    verify(parser.parse_args().root)
