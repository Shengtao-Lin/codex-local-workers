"""Create-only experiment closure from explicit Primary dispositions and facts.

Does not infer acceptance from green tests. Primary supplies reviewed reasons;
every accepted cell additionally needs current canonical and independent checks.
"""

import argparse
import json
import sys
from pathlib import Path

import bounded_evidence_support as S


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--reviews", type=Path, required=True)
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    batch = args.batch.resolve()
    registration = S.read(batch / "registration.json")
    notes = S.read(args.reviews)
    rows = []
    for case in registration["order"]:
        if case == "control":
            continue
        root = batch / "cells" / case / "isolated"
        result = S.read(root.parent / "result.json")
        report = S.read(root / ".agent/native-host-report.json")
        actual = report["consolidated_harness"]["actual"]
        accepted = case in notes
        if accepted:
            assert result["host_handoff_verified"] and result["exit_code"] == 0
            assert all(
                c["exit_code"] == 0
                for c in S.read(root.parent / "independent-checks.json")
            )
            sys.path.insert(0, str(root / ".local-agents"))
            from bounded import capture_fixture_support as F

            gate = F.load(
                root / ".local-agents/local-unit.py",
                "native_close_" + case.replace("-", "_"),
            )
            config = S.read(root / ".agent/prepared" / report["run_id"] / "config.json")
            gate.verify_handoff(root, report, config=config)
        target = S.read(root / ".agent/config.json")["coder_single_function"]["path"]
        archive = root / ".agent/tasks" / report["task_id"] / "runs" / report["run_id"]
        decision = {
            "decision": "accept" if accepted else "rework",
            "experiment_only": True,
            "production_acceptance": False,
            "source_sha256": S.sha(root / target),
            "report_sha256": S.sha(root / ".agent/native-host-report.json"),
            "reason": notes.get(
                case, report.get("failure_reason", "No Primary acceptance")
            ),
            "evidence": "canonical run + actual cumulative.diff + independent-checks.json for accepted cells; no Worker summary substituted",
        }
        S.save(root.parent / "primary-review.json", decision)
        requests = []
        for path in sorted(archive.glob("native-model-response-*.json")):
            response = S.read(path)
            usage = []
            for line in response.get("body", "").splitlines():
                if not line.startswith("data:"):
                    continue
                try:
                    event = json.loads(line[5:])
                except ValueError:
                    continue
                if event.get("message", {}).get("usage"):
                    usage.append(event["message"]["usage"])
                elif event.get("usage"):
                    usage.append(event["usage"])
            requests.append(
                {"file": path.name, "seconds": response.get("seconds"), "usage": usage}
            )
        rows.append(
            {
                "case": case,
                "status": result["status"],
                "primary_accept": accepted,
                "actual": actual,
                "host_seconds": report["consolidated_harness"]["seconds"],
                "requests": requests,
            }
        )
    accepted = sum(row["primary_accept"] for row in rows)
    S.save(
        batch / "metrics.json",
        {
            "rows": rows,
            "accepted": accepted,
            "executed": len(rows),
            "not_run": registration["live_registered"] - len(rows),
            "weekly_used_observed": args.weekly_used,
            "primary_cloud_tokens": "unknown",
            "primary_active_seconds": "unknown",
        },
    )
    S.save(
        batch / "decision.json",
        {
            "status": "PASS_SCOPED_MATRIX_NOT_RELEASE"
            if accepted == len(rows)
            else "HOLD_FIXED_MATRIX",
            "accepted": accepted,
            "executed": len(rows),
            "registered": registration["live_registered"],
            "production_acceptance": False,
            "historical_results_unchanged": True,
            "pending": registration.get(
                "pending_release",
                "Standalone installation/fault controls, no generality claim",
            ),
        },
    )
    print(
        f"Closed {batch.name}: {accepted}/{len(rows)} independent experimental accepts"
    )


if __name__ == "__main__":
    main()
