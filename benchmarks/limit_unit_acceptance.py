"""Independent closure verification; immutable facts, never model success inference."""

import argparse
import json
from pathlib import Path

import limit_recovery_v3 as version
from capability_fit import WORK, write
from inherited_context_recovery import digest, read
from layer_isolation import command


def verify(root):
    root = root.resolve()
    root.relative_to(WORK.resolve())
    packet = read(root / ".agent/packet.json")
    manifest = read(root / ".agent/manifest.json")
    changed_protected = [
        path
        for path, expected in manifest["files"].items()
        if path not in packet["scope"]["modify"] and digest(root / path) != expected
    ]
    commands = [
        [
            "pytest",
            "tests",
            "-q",
            "-p",
            "no:cacheprovider",
            "--basetemp=.agent/primary-closure-temp",
            "--junitxml=.agent/primary-closure.xml",
        ],
        ["ruff", "format", "--check", "src", "tests"],
        ["ruff", "check", "src", "tests"],
        [
            "pyright",
            "--project",
            ".agent/pyright.json",
            "--pythonpath",
            str(version.trial.PYTHON),
        ],
    ]
    checks = [
        command(root, [str(version.trial.PYTHON), "-B", "-m", *argv])
        for argv in commands
    ]
    counts = version.trial.selection.evidence.counts(
        root / ".agent/primary-closure.xml"
    )
    facts = {
        "checks": checks,
        "junit": counts,
        "changed_protected": changed_protected,
        "source_hash": digest(root / version.trial.COMMON),
        "passed": not changed_protected
        and all(c["exit"] == 0 for c in checks)
        and counts == {"tests": 38, "failures": 0, "errors": 0, "skipped": 0},
        "primary_accepted": False,
        "scope": "Frozen 31-file closure, not complete sibling project",
    }
    write(root / ".agent/primary-closure-facts.json", facts)
    print(json.dumps({"passed": facts["passed"], "junit": counts}))
    return facts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("root", type=Path)
    verify(parser.parse_args().root)
