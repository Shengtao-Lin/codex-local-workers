"""Explicit Primary navigation adjudication, with immutable evidence bindings."""

import argparse
from pathlib import Path

import bounded_evidence_support as S
import limited_explorer_trial as E


def record(cell, verdict, reason):
    registration = S.read(E.BATCH / "registration.json")
    row = registration["cells"][cell]
    root = Path(row["root"])
    report_path = root / ".agent/explorer.json"
    report = S.read(report_path)
    process = S.read(E.BATCH / "results" / cell / "process.json")
    if verdict == "pass":
        assert report["status"] == "success" and not process["protected_drift"]
        assert report["cache"]["hit"] is False
        for ref in report["source_refs"]:
            path = ref["path"]
            assert path in report["observed_files"]
            assert ref["source_hash"] == S.sha(root / path)
            source = (root / path).read_text(encoding="utf-8").splitlines()
            assert ref["quote"] == "\n".join(
                source[ref["start_line"] - 1 : ref["end_line"]]
            )
    S.save(
        E.BATCH / "primary" / (cell + ".json"),
        {
            "authority": "primary",
            "verdict": verdict,
            "reason": reason,
            "report_sha256": S.sha(report_path),
            "actual_reads": report["observed_files"],
            "budget": report["budget_usage"],
            "runtime_status": report["status"],
            "model_semantic_guidance_added": False,
            "scope": "Correct source-backed navigation only, not causal diagnosis or code acceptance",
        },
    )
    print(cell, verdict)


def close(used):
    reg = S.read(E.BATCH / "registration.json")
    assert all(S.sha(p) == h for p, h in reg["pins"].items())
    rows = []
    for cell in reg["order"]:
        path = E.BATCH / "primary" / (cell + ".json")
        if path.exists():
            row = S.read(path)
            process = S.read(E.BATCH / "results" / cell / "process.json")
            rows.append({"cell": cell, **row, "seconds": process["seconds"]})
        else:
            rows.append({"cell": cell, "verdict": "NOT_RUN_OR_UNADJUDICATED"})
    passed = sum(r["verdict"] == "pass" for r in rows)
    S.save(
        E.BATCH / "metrics.json",
        {
            "registered": 4,
            "adjudicated": sum("runtime_status" in r for r in rows),
            "passed": passed,
            "rows": rows,
            "primary_active_seconds": "unknown",
            "cloud_tokens": "unknown",
            "primary_semantic_feedback": 0,
            "weekly_used": used,
            "weekly_stop": 50,
        },
    )
    S.save(
        E.BATCH / "decision.json",
        {
            "status": "PASS_SCOPED_NAVIGATION_ONLY"
            if passed == 4
            else "HOLD_SCOPED_NAVIGATION",
            "passed": passed,
            "registered": 4,
            "causal_diagnosis": "Not tested; old misses unchanged",
            "coordinator": "NOT_ADMITTED",
            "production_defaults": "Unchanged",
        },
    )
    S.save(
        E.BATCH / "handoff.json",
        {
            "qualification": "Scoped source/test citation navigation only",
            "limits": "Required path hints supplied through existing citation mechanism; not unconstrained repository search",
            "history": "No old failures overwritten, no revised-question rescue or same-cell replacement",
        },
    )
    print({"passed": passed, "registered": 4})


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=("record", "close"))
    p.add_argument("--cell", choices=E.ORDER)
    p.add_argument("--verdict", choices=("pass", "fail"))
    p.add_argument("--reason")
    p.add_argument("--weekly-used", type=int)
    args = p.parse_args()
    if args.mode == "record":
        record(args.cell, args.verdict, args.reason)
    else:
        close(args.weekly_used)
