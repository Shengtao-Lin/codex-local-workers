"""Separate UTF-8 replay after the first probe hit Windows GBK stdout."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import typed_feedback_comparison as experiment
from capability_fit import WORK
from inherited_context_recovery import digest


def facts(root, case):
    process = subprocess.run(
        [sys.executable, "-X", "utf8", "-B", ".agent/typed-probe.py", case],
        cwd=root,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=30,
        check=True,
    )
    result = json.loads(process.stdout)
    if not result["counterexamples"]:
        raise ValueError("failed pytest without probe counterexample")
    return result


def configure():
    experiment.BASE = WORK / "typed-feedback-2"
    experiment.SNAPSHOT = WORK / "typed-feedback-baseline-2"
    experiment.facts = facts
    original_write = experiment.write

    def write(path, value):
        if path == experiment.BASE / "manifest.json":
            value = dict(value)
            value["drivers"] = {
                **value["drivers"],
                str(Path(__file__).resolve()): digest(Path(__file__)),
            }
            value["supersedes"] = (
                "typed-feedback-1: probe GBK encoding failure, two model calls and original result preserved"
            )
        original_write(path, value)

    experiment.write = write


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "0", "1", "2"))
    args = parser.parse_args()
    configure()
    if args.action == "prepare":
        experiment.prepare()
    else:
        experiment.run(int(args.action))
