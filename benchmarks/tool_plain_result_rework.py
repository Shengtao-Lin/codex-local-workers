"""Bounded inherited repair of a demonstrated existing plain-result regression."""

import argparse

import tool_contract_rework as repair
from capability_fit import WORK


def configure():
    repair.BASE = WORK / "tool-native-nudge-1"
    repair.SNAPSHOT = WORK / "tool-plain-result-runtime-12"
    repair.FIXTURE_VERSION = 10
    repair.FEEDBACK = (
        "Primary finding plain-result-1, owned resolved-output: your actual sync-result "
        "classification uses hasattr(result, '__await__'), which is not evidence that "
        "the value is awaitable. A normal JSON-roundtrippable dict subclass with "
        "__await__ = None is not awaitable, but your implementation attempts await "
        "and raises ToolExecutionError. A Primary-only compatibility probe fails on "
        "your exact draft and passes original source and other correct actual drafts. "
        "Preserve plain sync results while recognizing true awaitables. Inspect the "
        "current classification and make a minimal repair; retain single invocation, "
        "thread/context ownership, direct async identity and existing deadline/error/hook "
        "behavior. Do not change protected tests, scope, contracts or budgets."
    )
    repair.configure()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "run"))
    args = parser.parse_args()
    configure()
    if args.action == "prepare":
        repair.prepare("fresh-1")
        repair.register_actual("fresh-1")
    else:
        repair.run("fresh-1")
