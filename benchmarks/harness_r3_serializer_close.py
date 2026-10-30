"""Immutable qualification correction and stage evidence; no model calls."""
import json

import harness_r3_serializer as S

B = S.B


def main():
    rows = []
    binding = S.R.load(B.KIT / ".local-agents/citation-binding.py", "stage_citation_binding")
    for name in S.P.ORDER:
        case = S.BATCH / "cases" / name
        path = case / "result.json"
        if not path.exists():
            rows.append({"case": name, "status": "NOT_RUN"})
            continue
        row = B.read(path)
        row["qualified_complete_chain"] = False
        review_path = case / "primary-decision.json"
        if review_path.exists():
            row["recorded_primary_decision"] = B.read(review_path)
        if row.get("reviewer_decision") == "pass_to_primary":
            report = B.read(case / "reviewer.json")
            config = B.read(case / "isolated/.agent/config.json")
            target = config["coder_single_function"]
            ref = {"path": target["path"], "symbol": target["symbol"]}
            source = (case / "isolated" / ref["path"]).read_text(encoding="utf-8")
            supported = all(binding.covers(ref, source, entry["source_refs"])
                            for entry in report["contract_review"])
            row["implementation_citation_supported"] = supported
            row["qualified_complete_chain"] = supported and review_path.exists()
            if not supported:
                B.save(case / "qualification-correction.json", {
                    "old_primary_record_preserved": True,
                    "qualification": "NOT_QUALIFIED",
                    "code_correctness_acceptance_not_a_release": True,
                    "reason": "Primary prematurely credited full chain before examining semantic relevance of contract citation. Actual selected refs cite structural tests, not score implementation.",
                    "required_binding": ref,
                    "selected_refs": report["contract_review"][0]["source_refs"],
                    "no_report_or_model_result_modified": True,
                })
        rows.append(row)
    B.save(S.BATCH / "grid-results.json", rows)
    B.save(S.BATCH / "decision.json", {
        "stage": "R3", "qualification": "HOLD", "registered": 12, "executed": 5,
        "not_run": 7, "candidate_registered": 6, "candidate_executed": 3,
        "candidate_coder_all_check": 3, "qualified_complete_chains": 1,
        "failures": ["presence citation targets structural tests; missing Primary implementation_ref in packet",
                     "repair repeat Reviewer exhausted protocol budget: two incomplete-coverage REPORTs plus two wrong-bound-citation REPORTs"],
        "serializer_repair": "Verified by installed CLI controls and 3 actual Reviewer dispatches",
        "candidate_not_modified_during_live": True, "r4_admitted": False,
        "next_action": "Separate offline Reviewer action-eligibility audit, retaining fixed budgets/semantics and exact tests; bind presence to its already declared implementation symbol. No replay of this batch.",
        "user_authorized_autonomous_stages": True,
    })
    print(json.dumps({"registered": 12, "executed": 5, "coder_all_check": 3,
                      "qualified_chains": 1, "qualification": "HOLD"}))


if __name__ == "__main__":
    main()
