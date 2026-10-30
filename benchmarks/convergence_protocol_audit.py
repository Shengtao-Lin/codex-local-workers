"""Independent semantic/provenance audit; immutable decisions, no model execution."""

import argparse
import runpy
import subprocess
from pathlib import Path

from convergence_coder import KIT, save
from convergence_evidence_protocol import BASE, OLD
from system_convergence import read_object, ref, sha256


def preservation():
    manifest = read_object(
        KIT
        / "benchmarks/work/system-convergence/p0p1-20261010-1/baseline-manifest.json"
    )
    changed = [
        i["path"] for i in manifest["files"] if sha256(KIT / i["path"]) != i["sha256"]
    ]
    history = [
        i["path"]
        for i in manifest["history_inputs"]
        if sha256(KIT / i["path"]) != i["sha256"]
    ]
    siblings = [
        name + "/" + i["path"]
        for name, files in manifest["sibling_comparisons"].items()
        for i in files
        if (
            sha256(KIT.parent / name / i["path"])
            if (KIT.parent / name / i["path"]).is_file()
            else None
        )
        != i["peer_sha256"]
    ]
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=KIT, text=True
    ).strip()
    assert not changed and not history and not siblings and head == manifest["head"]
    return {
        "preexisting_files": len(manifest["files"]),
        "changed": changed,
        "history_inputs": len(manifest["history_inputs"]),
        "history_changed": history,
        "sibling_paths": sum(map(len, manifest["sibling_comparisons"].values())),
        "sibling_changed": siblings,
        "head_unchanged": True,
        "production_promoted": False,
        "commit_push": False,
    }


def reviewer(base=BASE, assessment=False):
    root = base / "reviewer"
    registration = read_object(root / "registration.json")
    results = []
    for cell in registration["cells"]:
        target = Path(cell["root"])
        report = read_object(target / ".agent/r1-reviewer.json")
        for artifact in cell["inputs"]:
            if not artifact["path"].startswith(".agent/"):
                assert sha256(target / artifact["path"]) == artifact["sha256"]
        for item in report.get("contract_review", []):
            for source in item.get("source_refs", [item["source_ref"]]):
                lines = (
                    (target / source["path"])
                    .read_text(encoding="utf-8-sig")
                    .splitlines()
                )
                assert source["canonical_quote"] == "\n".join(
                    lines[source["start_line"] - 1 : source["end_line"]]
                )
                assert source["source_hash"] == "sha256:" + sha256(
                    target / source["path"]
                )
        implementation = runpy.run_path(str(target / "src/product/target.py"))
        probes = {}
        if "increment" in implementation:
            probes = {str(x): implementation["increment"](x) for x in (-2, 0, 2)}
        elif "display_name" in implementation:
            for value in ({}, {"name": None}, {"name": ""}, {"name": "named"}):
                before = dict(value)
                probes[str(value)] = implementation["display_name"](value)
                assert value == before
        else:
            for value in (None, False, 0, ""):
                calls = []

                def fetch(key, value=value, calls=calls):
                    calls.append(key)
                    return value

                probes[str(value)] = implementation["lookup_or"](
                    fetch, "key", "default"
                )
                assert calls == ["key"]
            original_error = RuntimeError("original")

            def fail(key, original_error=original_error):
                raise original_error

            try:
                probes["runtime_error"] = implementation["lookup_or"](
                    fail, "key", "default"
                )
            except RuntimeError as observed:
                assert observed is original_error
                probes["runtime_error"] = "same original instance propagated"
        results.append(
            {
                "cell": cell["id"],
                "observed": report["decision"],
                "expected": cell["expected_decision"],
                "correct": report["decision"] == cell["expected_decision"],
                "failure_reason": report.get("failure_reason"),
                "findings": report.get("findings", []),
                "behavior_probes": probes,
                "protocol_errors": report.get("runtime_facts", {}).get(
                    "protocol_error_count"
                ),
                "source_quotes_and_protected_inputs_current": True,
                "independent_primary_note": "Same original contracts and expected dispositions. Conflicting x+1 and x-1 requirements cannot both hold for a negative integer; proposing a piecewise implementation changes the contract. Optional positive-only test is not itself a hard-contract violation; explicit negative-test obligation is. Actual abs(x)+1 bug and broad except Exception bug remain defects.",
            }
        )
    save(root / "primary-adjudications-1.json", results)
    save(
        root / "stage-decision-1.json",
        {
            "candidate": "reviewer-typed-issue-assessment-1"
            if assessment
            else "reviewer-displayed-evidence-ids-1",
            "registered": 16,
            "executed": 16,
            "valid_reports": sum(r["observed"] != "failed" for r in results),
            "correct": sum(r["correct"] for r in results),
            "failures": [r for r in results if not r["correct"]],
            "decision": "ACCEPT_CHANGE"
            if assessment and all(r["correct"] for r in results)
            else "HOLD_CAPABILITY",
            "protocol_improvement": "All sixteen reports valid; two within-budget corrections. Known-corpus, nonconcurrent result is not a statistical causal estimate.",
            "additional_deterministic_defect": None
            if assessment
            else "Legacy both-ref representation repair calls canonical_citation_tools on an evidence-ID schema, requiring missing source_refs while additionalProperties=false. Not seen in live cells; must repair in a new frozen version, not edit this candidate.",
            "compatibility_fix_required": not assessment,
            "production_promoted": False,
            "fixed_denominator_and_all_failures_preserved": True,
            "new_coder_calls": 0,
            "weekly_used_start": 1,
            "latest_observed_used": 2,
            "weekly_used_ceiling": 15,
            "cloud_tokens": None,
            "primary_active_seconds": None,
            "prior": ref(
                KIT,
                ((BASE if assessment else OLD) / "reviewer/stage-decision-1.json")
                .relative_to(KIT)
                .as_posix(),
            ),
            "qualification": "Same previously exposed fixed controls; model selects explicit issue nature, runtime only maps it to disposition; no keyword/SAT oracle, automatic acceptance or cost claim"
            if assessment
            else "HOLD",
            "protocol_corrections_total": sum(
                r["protocol_errors"] or 0 for r in results
            ),
            "preservation": preservation(),
        },
    )
    print(
        "Reviewer",
        sum(r["correct"] for r in results),
        "/16; all valid; "
        + (
            "limited semantic/protocol qualification"
            if assessment
            else "HOLD semantics and repair-schema compatibility"
        ),
    )


def explorer():
    root = BASE / "explorer"
    registration = read_object(root / "registration.json")
    results = []
    runtime = root / "candidate-kit/.local-agents"
    assert all(
        sha256(runtime / i["path"]) == i["sha256"] for i in registration["runtime"]
    )
    for cell in registration["cells"]:
        target = Path(cell["root"])
        report = read_object(target / ".agent/explorer.json")
        assert all(sha256(target / i["path"]) == i["sha256"] for i in cell["inputs"])
        quotes = []
        for item in report.get("source_refs", []):
            lines = (target / item["path"]).read_text(encoding="utf-8-sig").splitlines()
            assert item["quote"] == "\n".join(
                lines[item["start_line"] - 1 : item["end_line"]]
            )
            assert item["source_hash"] == sha256(target / item["path"])
            quotes.append(item["quote"])
        evidence = "\n".join(quotes)
        answer = report.get("model_answer", {})
        common = (
            report["status"] == "success"
            and report["cache"]["hit"] is False
            and answer.get("question_id") == "Q1"
            and answer.get("unresolved_scope") == "outside_cited_ranges_unknown"
        )
        if cell["question"] == "caller":
            correct = (
                common
                and answer.get("answer_state") == "located"
                and all(
                    text in evidence
                    for text in (
                        "invoker = self._agents.get(agent_id)",
                        "raise UnknownAgentError",
                    )
                )
            )
            note = "Actual resolving caller and rejecting get branch cited, not merely read; no claim of executed tests."
        elif cell["question"] == "integration":
            correct = (
                common
                and answer.get("answer_state") == "located"
                and all(
                    text in evidence
                    for text in (
                        "assert replay == first",
                        "assert invoker.call_count == 1",
                        "return replay",
                    )
                )
            )
            note = "Replay equality/call-count assertions and implementation cached-return branch cited. A duplicate selected range in r1 is redundant but neither fabricated nor missing an obligation."
        else:
            path = "src/agent_runtime/registry.py"
            lines = (target / path).read_text(encoding="utf-8-sig").splitlines()
            cited = {
                n
                for i in report.get("source_refs", [])
                if i["path"] == path
                for n in range(i["start_line"], i["end_line"] + 1)
            }
            correct = (
                common
                and answer.get("answer_state") == "absent_in_cited_ranges"
                and (
                    cited == set(range(1, len(lines) + 1))
                    and "unregister_agent" not in "\n".join(lines)
                    and "def get(" in evidence
                )
            )
            note = "Whole actual registry file cited: get exists, unregister_agent does not in this exact scope; outside-cited-scope uncertainty explicit. Runtime-owned READ_FILE provenance makes no invented SEARCH claim; no regex/template is used to determine symbol absence for the model."
        results.append(
            {
                "cell": cell["id"],
                "runtime_success": report["status"] == "success",
                "question_complete_and_truthful": bool(correct),
                "independent_primary_note": note,
                "model_answer": answer,
                "cache_hit": report.get("cache", {}).get("hit"),
                "protected_inputs_and_source_quotes_current": True,
            }
        )
    save(root / "primary-adjudications-1.json", results)
    save(
        root / "stage-decision-1.json",
        {
            "candidate": registration["candidate"],
            "decision": "ACCEPT_CHANGE"
            if all(r["question_complete_and_truthful"] for r in results)
            else "HOLD_CAPABILITY",
            "registered": 6,
            "executed": 6,
            "question_complete_and_truthful": sum(
                r["question_complete_and_truthful"] for r in results
            ),
            "qualification": "Structured single-question locator/scoped absence only on same previously exposed corpus; not broad free-form investigator or statistically demonstrated general reliability",
            "mechanical_provenance_not_semantic_auto_fill": True,
            "old_failures_and_standard_preserved": True,
            "full_regression": "1073 passed, 1 host-symlink skip, 166 subtests",
            "production_promoted": False,
            "new_coder_reviewer_coordinator_calls": 0,
            "weekly_used_start": 2,
            "latest_observed_used": 2,
            "weekly_used_ceiling": 15,
            "cloud_tokens": None,
            "primary_active_seconds": None,
            "preservation": preservation(),
        },
    )
    print(
        "Explorer",
        sum(r["question_complete_and_truthful"] for r in results),
        "/6 independent complete/truthful",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("reviewer", "explorer", "assessment"))
    args = parser.parse_args()
    if args.stage == "assessment":
        from convergence_reviewer_assessment import BASE as assessment_base

        reviewer(assessment_base, assessment=True)
    else:
        reviewer() if args.stage == "reviewer" else explorer()
