"""Explicit Primary acceptance; no production policy/state or old reviews changed.

Trusted Primary records are evidence, not cryptographic proof of human judgment.
The frozen host gate remains responsible for deterministic validation integrity.
"""

import argparse
import json
import re
from pathlib import Path

import bounded_evidence_support as S
import capture_fixture_support as F


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value
    ):
        raise ValueError("Invalid canonical identity")
    return value


def bound_path(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("Evidence path outside repository or missing")
    return path


def adjudication(report, report_sha, completed, payload):
    if completed.get("decision") != report.get("decision"):
        raise ValueError("Reviewer did not complete this report")
    facts = report.get("runtime_facts", {})
    if facts.get("read_only") is not True or facts.get("inputs_unchanged") is not True:
        raise ValueError("Reviewer integrity not established")
    rule = F.load(
        S.KIT / ".local-agents/review-disposition.py", "supervised_disposition"
    )
    result = rule.adjudicate(report, report_sha, payload)
    if result["primary_decision"] != "accept":
        raise ValueError("Confirmed defect or unresolved evidence blocks acceptance")
    # Escalations are unresolved architecture/contract decisions, not false-positive repairs.
    if report["decision"] not in {"pass_to_primary", "rework"}:
        raise ValueError("Escalation requires replanning")
    return result


def evaluate(root, task_id, run_id, payload, primary):
    root = Path(root).resolve()
    task = root / ".agent/tasks" / identifier(task_id)
    run = task / "runs" / identifier(run_id)
    coder = S.read(run / "handoff.json")
    gate = F.load(root / ".local-agents/local-unit.py", "supervised_existing_host_gate")
    identity = gate.verify_handoff(
        root, coder, config=S.read(root / ".agent/config.json")
    )
    if identity["task_id"] != task_id or identity["run_id"] != run_id:
        raise ValueError("Canonical run differs")
    # Never pick a favorable report among semantic re-samples.
    reports = []
    for path in (task / "reviews").glob("*/handoff.json"):
        report = S.read(path)
        if all(report.get("identity", {}).get(k) == v for k, v in identity.items()):
            reports.append((path, report))
    if len(reports) != 1:
        raise ValueError("Exactly one matching Reviewer report required")
    report_path, report = reports[0]
    decision = adjudication(
        report,
        S.sha(report_path),
        S.read(report_path.with_name("completed.json")),
        payload,
    )
    hashes = report["runtime_facts"].get("observed_read_hashes")
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError("Reviewer read evidence missing")
    for path, digest in hashes.items():
        if S.sha(bound_path(root, path)) != digest:
            raise ValueError("Reviewer read source changed")
    if primary.get("authority") != "primary" or primary.get("identity") != identity:
        raise ValueError("Primary identity missing or foreign")
    if primary.get("decision") != "accept" or not primary.get("reason", "").strip():
        raise ValueError("Independent Primary acceptance required")
    if primary.get("assisted") is not False or primary.get("takeover") is not False:
        raise ValueError("Assisted/takeover must be reported separately")
    bindings = primary.get("bindings", {})
    required = {
        p.relative_to(root).as_posix()
        for p in (
            run / "handoff.json",
            run / "packet.json",
            run / "validation.json",
            run / "cumulative.diff",
            report_path,
            root / ".agent/config.json",
        )
    } | set(hashes)
    required |= set(S.read(run / "post-state.json")["validation_inputs"])
    if not required <= set(bindings):
        raise ValueError("Primary evidence does not cover current inputs")
    for path, digest in bindings.items():
        if S.sha(bound_path(root, path)) != digest:
            raise ValueError("Primary evidence is stale")
    checks = primary.get("checks", [])
    if not checks or any(c.get("exit_code") != 0 or not c.get("argv") for c in checks):
        raise ValueError("Independent complete checks failed or missing")
    if primary.get("complete_profile") is not True:
        raise ValueError("Independent full profile required")
    return {
        "schema_version": 1,
        "mode": "supervised-primary-adjudication-v1",
        "identity": identity,
        "decision": "accept",
        "automatic_acceptance": False,
        "strict_reviewer_pass": report["decision"] == "pass_to_primary",
        "reviewer_decision": report["decision"],
        "disposition": decision,
        "primary": primary,
        "qualification": "this run only; no R4/R5 promotion",
    }


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--disposition", type=Path, required=True)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(
        args.root,
        args.task_id,
        args.run_id,
        S.read(args.disposition),
        S.read(args.primary),
    )
    S.save(args.output, result)
    print(
        json.dumps(
            {
                k: result[k]
                for k in ("mode", "identity", "decision", "strict_reviewer_pass")
            }
        )
    )


if __name__ == "__main__":
    main()
