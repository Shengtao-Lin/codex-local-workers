"""Independent post-live audit; no model calls or edits to frozen candidates."""

import argparse
import json
from pathlib import Path

import harness_r4_dto_audit as AUDIT
import harness_r4_medium as H

B, E = H.B, H.E


def audit():
    E.prior_unchanged()
    for path, digest in B.read(H.BATCH / "live-freeze.json")["pins"].items():
        assert B.sha(Path(path)) == digest, path
    manual = B.read(H.BATCH / "primary-adjudications.json")
    judgments = {r["id"]: r for r in manual}
    assert len(judgments) == len(manual) == 20
    grid, traces = [], []
    for row in B.read(H.BATCH / "registration.json")["cells"]:
        root = Path(row["root"])
        H.R.assert_files(root, row["files"])
        H.R.assert_files(Path(row["origin"]), row["origin_files"])
        cell = root.parent
        result = B.read(cell / "result.json")
        report = B.read(cell / "reviewer.json")
        judgment = judgments.pop(row["id"])
        assert isinstance(judgment["correct"], bool) and judgment["reason"]
        assert not result["protected_drift"] and not result["infra_failure"]
        assert report["runtime_facts"]["inputs_unchanged"]
        assert report["evidence_observation_protocol"] == "reviewer-evidence-state-v1"
        assert report["reviewer_experiment"]["effective_reviewer_directive"] == "medium"
        assert row["identity"]["schema_version"] == 1
        assert report["identity"] == {
            key: row["identity"][key]
            for key in ("task_id", "unit_id", "run_id", "review_id")
        }
        for contract in report["contract_review"]:
            for ref in contract.get("source_refs", []):
                path = root / ref["path"]
                lines = path.read_text(encoding="utf-8-sig").splitlines()
                quote = "\n".join(lines[ref["start_line"] - 1 : ref["end_line"]])
                assert quote == ref["canonical_quote"]
                assert ref["source_hash"].removeprefix("sha256:") == B.sha(path)
        if judgment["correct"]:
            assert result["observed"] == result["expected"]
        wire = AUDIT.calls(cell)
        assert wire and all(c["finish_reason"] != "length" for c in wire)
        first_payload = None
        for call in wire:
            request = B.read(cell / "wire" / call["request"])
            messages = request["body"]["messages"]
            system = next(m["content"] for m in messages if m["role"] == "system")
            assert system.count("Reasoning strength: medium.") == 1
            payload = next(
                m["content"]
                for m in messages
                if (m.get("content") or "").startswith("LOCAL_REVIEW_INPUT\n")
            )
            if first_payload is None:
                first_payload = json.loads(payload.split("\n", 1)[1])
        if row["id"] == "conflicting-contract-r1":
            assert "additionally required to equal x - 1" in json.dumps(first_payload)
        traces.append(
            {
                "id": row["id"],
                "actions": wire,
                "protocol_errors": report["runtime_facts"]["protocol_error_count"],
                "initial_payload_sha256": B.sha(cell / "wire" / wire[0]["request"]),
                "initial_validation_contract_check": first_payload.get(
                    "runtime_validation", {}
                ).get("contract_check"),
            }
        )
        grid.append(
            {
                **result,
                "group": row["group"],
                "primary_adjudication": judgment,
                "report_sha256": B.sha(cell / "reviewer.json"),
                "failure_class": None if judgment["correct"] else "semantic_false_pass",
            }
        )
    assert not judgments
    baseline = B.read(E.BATCH / "baseline.json")
    for path, digest in baseline["old_decisions"].items():
        assert B.sha(Path(path)) == digest
    changed = [
        p
        for p, sha in baseline["files"].items()
        if not (B.KIT / p).is_file() or B.sha(B.KIT / p) != sha
    ]
    assert set(changed) <= {
        "benchmarks/harness_r4_evidence.py",
        "docs/local-model-harness-convergence-plan.md",
    }, changed
    preservation = {
        "original_baseline_files_checked": len(baseline["files"]),
        "intentional_changes_since_turn_baseline": changed,
        "live_pins_and_all_twenty_inputs_unchanged": True,
        "all_twenty_origins_unchanged": True,
        "old_decisions_unchanged": True,
        "production_runtime_unchanged": True,
        "sibling_writes": False,
        "git_operations": [],
    }
    return grid, traces, preservation


def main(used):
    grid, traces, preservation = audit()
    groups = [
        {
            "group": name,
            "correct": sum(
                r["primary_adjudication"]["correct"] for r in grid if r["group"] == name
            ),
            "total": sum(r["group"] == name for r in grid),
        }
        for name in ("original-sixteen", "exposed-real")
    ]
    state = "PASS" if all(g["correct"] == g["total"] for g in groups) else "HOLD"
    B.save(H.BATCH / "grid-results.json", grid)
    B.save(H.BATCH / "wire-action-audit.json", traces)
    B.save(H.BATCH / "metrics.json", AUDIT.metrics(H.BATCH))
    B.save(H.BATCH / "preservation.json", preservation)
    B.save(
        H.BATCH / "decision.json",
        {
            "stage": "R4 formal Reviewer medium diagnostic",
            "qualification": state,
            "registered": 20,
            "executed": len(grid),
            "not_run": 0,
            "groups": groups,
            "semantic_false_passes": [
                r["id"] for r in grid if r["failure_class"] == "semantic_false_pass"
            ],
            "terminal_protocol_or_transport_failures": 0,
            "input_drift": 0,
            "r4_passed": False,
            "production_promoted": False,
            "new_coder_or_holdout_credit": False,
            "weekly_used": used,
            "weekly_used_start": B.read(H.BATCH / "registration.json")[
                "weekly_used_start"
            ],
            "usage_ceiling": 45,
            "primary_active_seconds": None,
            "cloud_tokens": None,
            "stop_reason": "Fixed candidate HOLD; architecture decision before a new live candidate, not usage exhaustion.",
            "next": "Seek approval for a separately registered task-local semantic review -> host-assembled formal report candidate within the existing total budget. No promotion, parameter sweep, resampling, automatic semantic inference, or relaxed gates.",
        },
    )
    print({"qualification": state, "groups": groups, "weekly_used": used})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--used", type=int, required=True)
    main(parser.parse_args().used)
