"""Explicit, one-time wire change; the host owns eligibility and all budgets."""

import argparse
import copy
import sys
from pathlib import Path
from types import SimpleNamespace

import host_block_proposal as BLOCK


def adapt(base):
    rules = SimpleNamespace(**vars(base))
    alternate = BLOCK.adapt(base)
    switched = False

    def recover_noop(client):
        nonlocal switched
        if switched:
            return False
        for key in ("PROMPT", "SCHEMA", "decode", "materialize"):
            setattr(rules, key, getattr(alternate, key))
        client.action_schema = copy.deepcopy(rules.SCHEMA)
        switched = True
        return True

    rules.recover_noop = recover_noop
    rules.RECOVERY_PROFILE = "whole-to-exact-block-once-v1"
    return rules


def main():
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--noop-block-recovery", action="store_true")
    args, rest = parser.parse_known_args()
    root = Path.cwd() / ".local-agents"
    sys.path.insert(0, str(root))
    from bounded.capture_fixture_support import load

    entry = load(root / "local-bounded-unit.py", "noop_block_installed_entry")
    original = entry.COMPAT.proposal_rules
    if args.noop_block_recovery:
        entry.COMPAT.proposal_rules = lambda config, base: adapt(original(config, base))
    sys.argv = [str(root / "local-bounded-unit.py"), *rest]
    return entry.main()


if __name__ == "__main__":
    raise SystemExit(main())
