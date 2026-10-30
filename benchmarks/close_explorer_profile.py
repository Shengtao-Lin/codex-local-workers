"""Separate runtime report success, verified retrieval and causal evidence quality."""

from pathlib import Path

import bounded_evidence_support as S
import explorer_locator_profile_trial as V


def main():
    rows = []
    for cell in ("revision", "request"):
        batch = V.BASE / cell
        reg = S.read(batch / "registration.json")
        assert all(S.sha(path) == digest for path, digest in reg["pins"].items())
        root = batch / "isolated"
        report = S.read(root / ".agent/explorer-report.json")
        assert report["status"] == "success" and report["semantic_verdict"] == "not_evaluated"
        for ref in report["source_refs"]:
            text = (root / ref["path"]).read_text(encoding="utf-8-sig").splitlines()
            actual = "\n".join(text[ref["start_line"] - 1:ref["end_line"]])
            assert ref["quote"].rstrip("\n") == actual
        reason = (
            "Actual common.py215-221 includes make_sample_id callee215 and source_revision argument220, not later CanonicalSample. SourceTrace definition24-27 includes actual field26. Host quotes independently verified."
            if cell == "revision" else
            "queue.py18-19 shows actual request_hash calling canonical_json; fingerprint.py14-21 shows real complete JSON encoding body, not an import. Host quotes independently verified."
        )
        S.save(batch / "decision.json", {"status": "PASS_FIXED_LOCATOR_QUESTION", "Primary": reason,
               "qualification": "Only known-path/symbol retrieval; no narrative causal verdict or whole-project acceptance",
               "Primary_cost": reg["Primary_preparation"], "prior_failures_unchanged": True})
        rows.append({"cell": cell, "retrieval_verified": True, **report["budget_usage"]})
    S.save(V.BASE / "metrics.json", {"registered": 2, "executed": 2, "verified_retrieval": 2,
           "protocol_errors": sum(r["protocol_errors"] for r in rows), "rows": rows,
           "cloud_saving": "unknown", "narrative_investigation": "HOLD, not part of this retrieval denominator"})
    S.save(V.BASE / "decision.json", {"status": "PASS_SCOPED_INSTALLED_LOCATOR_SCREEN",
           "gate": "Both actual source relationships correctly retrieved and independently quoted2/2",
           "scope": "Primary supplies known paths/symbol anchors; retrieval only. Not arbitrary investigation or causal report qualification"})
    for name in ("explorer-report-recovery-live-20261022-1", "explorer-wire-shapes-20261022-1"):
        batch = V.I.BASE / name
        report = S.read(batch / "isolated/.agent/explorer-report.json")
        S.save(batch / "decision.json", {"status": "HOLD_NARRATIVE_INVESTIGATION",
               "runtime_status": report["status"], "failure_reason": report.get("failure_reason"),
               "Primary": "Report-only recovery ran but missing relevant_files remained" if report["status"] != "success" else
               "Correct value-flow conclusion, but cited common.py219 is source_trace_id, whereas source_revision assignment is220; no source range explicitly bound to callee215. Runtime success is not causal-evidence qualification.",
               "provider_observation": "Diagnostic observed native read tools and no ignored tool call at final; final content first had one trailing character, then valid JSON. Does not prove earlier run's exact trailing character.",
               "score_policy": "Observation-only successful report does not replace preceding formal failure"})
    correction = V.I.BASE / "explorer-report-recovery-live-20261022-1/usage-correction.json"
    S.save(correction, {"registration_entered": 36, "actual_tool_observation": 35,
           "live_start_actual": 35, "budget_ceiling": 60, "effect": "No effect on eligibility/outcome; registration not overwritten"})
    before = V.I.BASE / "packaged-flat-profile-20261022-1"
    preimage = before / "preimages/.local-agents/explorer-runtime.py"
    intermediate = V.I.BASE / "explorer-obligation-live-20261022-1/isolated/.local-agents/explorer-runtime.py"
    S.save(V.I.BASE / "explorer-obligation-controls-20261022-1/source-lineage.json", {
        "original_user_dirty_preimage": {"path": str(preimage), "sha256": S.sha(preimage)},
        "obligation_candidate": {"path": str(intermediate), "sha256": S.sha(intermediate)},
        "recovery_candidate": {"path": str(S.KIT / ".local-agents/explorer-runtime.py"), "sha256": S.sha(S.KIT / ".local-agents/explorer-runtime.py")},
        "history": "Earlier batches pin their installed snapshots and remain unchanged; initial user modifications retained in original preimage"})
    print("Locator2/2 independently verified; narrative investigation remains HOLD")


if __name__ == "__main__":
    main()
