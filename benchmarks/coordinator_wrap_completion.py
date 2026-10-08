"""Child-run evidence and recovery-aware audit, separate from strict cohort gate."""

import argparse
import json
import subprocess
import sys

import coordinator_wrap_policy_audit as prior
from capability_fit import KIT, write
from inherited_context_recovery import read
from layer_isolation import check


def child_check(identity):
    _, _, root, _, _ = prior.context(identity)
    child = read(root / ".agent/counterexample-a2.json")
    archive = root / ".agent/tasks" / child["task_id"] / "runs" / child["run_id"]
    h = read(archive / "handoff.json")
    reviewer = read(root / ".agent/counterexample-reviewer.json")
    if h["status"] != "ready_for_review" or reviewer["decision"] != "pass_to_primary":
        raise ValueError("successful reviewed child required")
    result = check(root, "counterexample-independent-1")
    if not result["all_checks_pass"] or result["tests_executed"] != 7:
        raise ValueError("seven independent tests and static checks required")
    write(root / ".agent/counterexample-independent-1.json", result)
    print(json.dumps(result))


def record_child(identity):
    _, _, root, bound, _ = prior.context(identity)
    child = read(root / ".agent/counterexample-a2.json")
    for packet, decision, summary in (
        (
            bound,
            "rework",
            "First attempt failed exact split policy. Primary authorized one inherited concrete-counterexample repair; preserve failure, not first-attempt success.",
        ),
        (
            child,
            "accept",
            "Primary reviewed actual fallback-only child diff and parent cumulative diff, width-dependent split semantics, fresh Reviewer source-backed RF-primary-split-policy-1 and seven independent tests/static checks. Accept this supervised repair only; no unattended stability claim.",
        ),
    ):
        p = subprocess.run(
            [
                sys.executable,
                "-B",
                str(KIT / ".local-agents/record-review.py"),
                "--repo",
                str(root),
                "--task-id",
                packet["task_id"],
                "--run-id",
                packet["run_id"],
                "--decision",
                decision,
                "--summary",
                summary,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if p.returncode != 0:
            raise ValueError(p.stdout + p.stderr)
    print("Recorded separate parent rework and child acceptance")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("child-check", "record-child"))
    parser.add_argument("identity")
    args = parser.parse_args()
    if args.action == "child-check":
        child_check(args.identity)
    else:
        record_child(args.identity)
