"""Experimental fact ordering only; installed runtime and Reviewer unchanged."""

import argparse
import sys
from pathlib import Path


def prioritize(facts):
    failure = facts["validation_failure"]
    if failure.get("status") != "failed":
        return facts
    focused = failure["focused_tests"]
    first = {
        key: focused[key] for key in ("failed_test_ids", "failures") if key in focused
    }
    first.update(focused)
    ordered_failure = {"focused_tests": first}
    ordered_failure.update(
        {key: value for key, value in failure.items() if key != "focused_tests"}
    )
    ordered = {"validation_failure": ordered_failure, "target": facts["target"]}
    ordered.update({key: value for key, value in facts.items() if key not in ordered})
    return ordered


def main():
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--failure-priority", action="store_true")
    args, rest = parser.parse_known_args()
    root = Path.cwd() / ".local-agents"
    sys.path.insert(0, str(root))
    from bounded.capture_fixture_support import load

    entry = load(root / "local-bounded-unit.py", "failure_priority_installed_entry")
    if args.failure_priority:
        original = entry.RULES.render
        entry.RULES.render = lambda facts: original(prioritize(facts))
    sys.argv = [str(root / "local-bounded-unit.py"), *rest]
    return entry.main()


if __name__ == "__main__":
    raise SystemExit(main())
