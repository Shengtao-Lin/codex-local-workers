"""Pure C3 collection and explicit Primary adjudication; never launches a worker."""

import argparse
import json
from pathlib import Path

import convergence_coder_transport as trial
from convergence_coder import KIT, save
from convergence_decomposition import load
from convergence_protocol_audit import preservation
from system_convergence import junit_counts, read_object, ref, sha256


def cell_records(identity):
    record = read_object(trial.BASE / "registration.json")
    assert sha256(KIT / record["wrapper"]["path"]) == record["wrapper"]["sha256"]
    cell = next(c for c in record["cells"] if c["id"] == identity)
    root = Path(cell["root"])
    for item in [
        cell["packet"],
        cell["config"],
        *[p for p in cell["inputs"] if p["path"] not in cell["writable"]],
    ]:
        assert sha256(root / item["path"]) == item["sha256"]
    for item in record["runtime"][cell["arm"]]:
        assert sha256(trial.RUNTIME / item["path"]) == item["sha256"]
    packet = read_object(root / ".agent/packet.json")
    archive = root / f".agent/tasks/{packet['task_id']}/runs/{packet['run_id']}"
    handoff = read_object(archive / "handoff.json")
    assert all(handoff["identity"][k] == v for k, v in cell["identity"].items())
    assert read_object(archive / "completed.json")["status"] == handoff["status"]
    return cell, root, archive, packet, handoff


def adjudicate(identity, decision, note):
    _, root, archive, packet, handoff = cell_records(identity)
    if decision == "accept":
        if handoff["status"] != "ready_for_review":
            raise ValueError("not Coder ready")
        reviewer = read_object(root / ".agent/reviewer.json")
        if reviewer["decision"] != "pass_to_primary":
            raise ValueError("not independent Reviewer pass")
        gate = load("c3_current_handoff", trial.RUNTIME / "local-unit.py")
        gate.verify_handoff(root, read_object(root / ".agent/coder.json"))
    # All outcomes get an independent unchanged acceptance run; failing output remains.
    for name, argv in (
        (
            "independent-tests",
            [
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "--junitxml=" + str(root / ".agent/independent.xml"),
            ],
        ),
        ("independent-lint", ["-m", "ruff", "check", "src", "tests"]),
        ("independent-format", ["-m", "ruff", "format", "--check", "src", "tests"]),
    ):
        code = trial.controls.command(root, argv, root / (".agent/" + name + ".json"))
        if decision == "accept" and code != 0:
            raise ValueError("independent acceptance failed")
    counts = junit_counts(root / ".agent/independent.xml")
    if decision == "accept":
        assert (
            counts["executed"] > 0
            and counts["failures"] == counts["errors"] == counts["skipped"] == 0
        )
    assert (
        trial.controls.command(
            root,
            [
                trial.RUNTIME / "record-review.py",
                "--task-id",
                packet["task_id"],
                "--run-id",
                packet["run_id"],
                "--decision",
                decision,
                "--summary",
                note,
                "--repo",
                root,
            ],
            root / ".agent/primary-record-invocation.json",
        )
        == 0
    )
    save(
        root / ".agent/primary-adjudication.json",
        {
            "decision": decision,
            "note": note,
            "canonical": ref(archive, "review.json"),
            "independent": counts,
            "primary_active_seconds": None,
            "cloud_tokens": None,
        },
    )


def collect(latest_used):
    registration = read_object(trial.BASE / "registration.json")
    results = []
    for cell in registration["cells"]:
        root = Path(cell["root"])
        if not (root / "invocation.json").exists():
            results.append({"cell": cell["id"], "status": "not_run"})
            continue
        _, root, archive, _, handoff = cell_records(cell["id"])
        events = [
            json.loads(line)
            for line in (archive / "events.jsonl").read_text().splitlines()
        ]
        errors = [e["facts"] for e in events if e["event"] == "tool_error"]
        targets = [
            e
            for e in errors
            if e.get("action") == "SAFE_REPLACE_LINE"
            or (
                e.get("action") == "VALIDATE" and "contract_check" in e.get("error", "")
            )
        ]
        requests = [e["facts"] for e in events if e["event"] == "model_request"]
        review_path = root / ".agent/reviewer.json"
        reviewer = read_object(review_path) if review_path.exists() else {}
        primary = read_object(archive / "review.json")
        results.append(
            {
                "cell": cell["id"],
                "kind": cell["kind"],
                "arm": cell["arm"],
                "coder_status": handoff["status"],
                "failure_reason": handoff.get("failure_reason"),
                "protocol_error_count": handoff.get("protocol_error_count"),
                "target_field_errors": targets,
                "all_tool_errors": errors,
                "local_repair_count": handoff.get("repair_count"),
                "validation": handoff.get("validation"),
                "model_requests": len(requests),
                "provider_statuses": [
                    r.get("provider_status_code")
                    for r in requests
                    if r.get("provider_status_code") is not None
                ],
                "reported_context_utilizations": [
                    r.get("reported_context_utilization") for r in requests
                ],
                "reviewer": reviewer.get("decision", "not_started"),
                "reviewer_protocol_errors": reviewer.get("runtime_facts", {}).get(
                    "protocol_error_count"
                ),
                "primary": primary["decision"],
                "run": ref(archive, "handoff.json"),
                "independent": read_object(root / ".agent/primary-adjudication.json")[
                    "independent"
                ],
                "invocation": read_object(root / "invocation.json"),
                "cloud_tokens": None,
                "primary_active_seconds": None,
            }
        )
    executed = [r for r in results if r.get("coder_status")]
    candidate = [r for r in executed if r["arm"] == "candidate"]
    baseline = [r for r in executed if r["arm"] == "baseline"]
    candidate_pass = len(candidate) == 2 and all(
        r["primary"] == "accept" for r in candidate
    )
    improved = (
        candidate_pass
        and len(baseline) == 2
        and sum(len(r["target_field_errors"]) for r in candidate)
        < sum(len(r["target_field_errors"]) for r in baseline)
    )
    decision = (
        "ACCEPT_CHANGE"
        if improved
        else "KEEP_BASELINE"
        if candidate_pass
        else "HOLD_CAPABILITY"
    )
    save(
        trial.BASE / "stage-decision-1.json",
        {
            "stage": "C3",
            "decision": decision,
            "registered": 4,
            "executed": len(executed),
            "results": results,
            "candidate_full_chains_accepted": sum(
                r["primary"] == "accept" for r in candidate
            ),
            "baseline_full_chains_accepted": sum(
                r["primary"] == "accept" for r in baseline
            ),
            "candidate_target_errors": sum(
                len(r["target_field_errors"]) for r in candidate
            ),
            "baseline_target_errors": sum(
                len(r["target_field_errors"]) for r in baseline
            ),
            "all_failure_costs_retained": True,
            "external_rework": 0,
            "primary_business_edits": False,
            "weekly_used_start": 3,
            "weekly_used_end": latest_used,
            "weekly_used_ceiling": 15,
            "preservation": preservation(),
            "production_promoted": False,
            "old_D2": "HOLD, 2/3; unchanged classification semantic failure, no substitute case credit",
            "I1": "BLOCKED_BY_D2",
            "classification": "UNQUALIFIED_PRIMARY_OWNED",
            "economic_gate": "UNMEASURED",
            "no_general_stability_or_causal_success_rate_claim": True,
            "registration": ref(trial.BASE, "registration.json"),
        },
    )
    print(
        decision,
        "candidate accepted",
        sum(r["primary"] == "accept" for r in candidate),
        "/2",
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("adjudicate", "collect"))
    parser.add_argument("cell", nargs="?")
    parser.add_argument(
        "--decision", choices=("accept", "rework", "replan", "takeover")
    )
    parser.add_argument("--note")
    parser.add_argument("--weekly-used", type=int)
    args = parser.parse_args()
    trial.bind()
    if args.action == "adjudicate":
        adjudicate(args.cell, args.decision, args.note)
    else:
        collect(args.weekly_used)
