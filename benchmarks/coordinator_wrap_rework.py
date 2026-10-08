"""Primary-authorized counterexample rework, with unchanged inherited contract."""

import argparse
import json
import subprocess
import sys

import coordinator_wrap_policy_audit as audit
from capability_fit import load_worker, write
from inherited_context_recovery import digest, read


def prepare(identity):
    _, _, root, bound, parent = audit.context(identity)
    handoff = read(parent / "handoff.json")
    if handoff["status"] != "failed":
        raise ValueError("expected failed parent")
    child = {k: bound[k] for k in ("schema_version", "task_id", "unit_id")}
    child.update(
        run_id=bound["run_id"] + "-counterexample-a2",
        parent_run_id=bound["run_id"],
        preserve_contract=True,
        attempt=2,
        plan_revision=1,
        packet_revision=2,
        review_feedback=[
            {
                "finding_id": "primary-split-policy-1",
                "contract_id": "normalize-unit",
                "source_anchor": "end",
                "verify_in_review": True,
                "text": "The actual last protected failure is tests/test_target.py:60: text='  abc', cols=2, expected [' ', ' a', 'bc'], actual [' ', ' ', 'ab', 'c']. Source src/product/target.py wrap has a zero-offset fallback at lines 7-8. It terminates but does not implement the explicitly required width-dependent split policy. Locate that branch and repair its behavior. Retain all other passing behavior and all seven protected tests. Reviewer must inspect fallback semantics, not just termination. No reference implementation or new budget is supplied.",
            }
        ],
    )
    worker = load_worker(audit.cohort.SNAPSHOT)
    resolved = worker.resolve_inherited_packet(root, child)
    worker.validate_packet(resolved)
    if resolved["_inheritance"]["parent_input_state"]["status"] != "unchanged":
        raise ValueError("parent draft drift")
    write(root / ".agent/counterexample-a2.json", child)
    write(
        root / ".agent/counterexample-registration.json",
        {
            "child_sha256": digest(root / ".agent/counterexample-a2.json"),
            "driver_sha256": digest(__import__("pathlib").Path(__file__)),
            "authorization": "Primary authorized one inherited counterexample repair, no Coordinator autonomous retry",
            "first_attempt_failure_retained": True,
        },
    )


def run(identity):
    _, _, root, _, _ = audit.context(identity)
    path = root / ".agent/counterexample-a2.json"
    if (
        digest(path)
        != read(root / ".agent/counterexample-registration.json")["child_sha256"]
    ):
        raise ValueError("packet drift")
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(audit.cohort.SNAPSHOT / ".local-agents/local-unit.py"),
            "--packet",
            str(path),
            "--config",
            str(root / ".agent/config.json"),
            "--coder-report",
            str(root / ".agent/counterexample-coder.json"),
            "--review-report",
            str(root / ".agent/counterexample-reviewer.json"),
        ],
        cwd=root,
        check=False,
    )
    print(json.dumps({"exit": result.returncode}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("identity")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.identity)
    else:
        run(args.identity)
