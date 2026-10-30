"""Replay the exact archived bad citation offline; never change its original archive."""

import copy
import shutil

import convergence_citation_binding_trial as trial


def main():
    old_root = trial.PREVIOUS / "isolated"
    old_run = (
        old_root
        / ".agent/tasks/real-trace-batch-pilot/runs/real-trace-batch-pilot-unit-1-a1"
    )
    root = trial.BASE / "controls/archived-citation-2"
    root.mkdir(parents=True, exist_ok=False)
    for path in trial.read(old_root / ".agent/brief.json")["source_hashes"]:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(old_root / path, target)
    run = (
        root
        / ".agent/tasks/real-trace-batch-pilot/runs/real-trace-batch-pilot-unit-1-a1"
    )
    run.mkdir(parents=True)
    for name in (
        "completed.json",
        "handoff.json",
        "validation.json",
        "post-state.json",
        "cumulative.diff",
    ):
        shutil.copyfile(old_run / name, run / name)
    packet = trial.read(old_run / "packet.json")
    binding = {"path": trial.SOURCE, "symbol": "MlflowTraceSource.get_many"}
    packet["required_behavior"][0]["implementation_ref"] = binding
    trial.save(run / "packet.json", packet)
    module = trial.load(
        "archived_citation_candidate", trial.KIT / ".local-agents/reviewer-runtime.py"
    )
    runtime = module.ReviewerRuntime(
        root,
        {
            "task_id": trial.FEATURE,
            "unit_id": "unit-1",
            "run_id": old_run.name,
            "review_id": "offline-exact-archived-citation-control",
        },
        trial.read(old_root / ".agent/config.json"),
        None,
    )
    runtime.initial_payload()
    for path in (
        "tests/test_mlflow_trace_source.py",
        "tests/test_get_many.py",
        trial.SOURCE,
    ):
        runtime.read_file({"path": path, "start_line": 1, "end_line": 230})
    old_report = trial.read(
        old_root / ".agent/limited" / trial.FEATURE / "unit-1/reviewer.json"
    )
    review_entry = old_report["contract_review"][0]
    bad = {
        "assessment": old_report["model_assessment"],
        "findings": old_report["findings"],
        "verified_contract_ids": old_report["verified_contract_ids"],
        "unverified_claims": old_report["unverified_claims"],
        "ordering_review": [],
        "verified_check_ids": old_report["verified_check_ids"],
        "contract_review": [
            {
                "obligation_id": review_entry["obligation_id"],
                "status": review_entry["status"],
                "evidence": review_entry["evidence"],
                "source_refs": [
                    {k: ref[k] for k in ("path", "start_line", "end_line")}
                    for ref in review_entry["source_refs"]
                ],
            }
        ],
    }
    before = copy.deepcopy(bad)
    try:
        runtime.validate_report(bad)
        raise AssertionError("Archived wrong citation accepted")
    except module.ReviewError as exc:
        error = str(exc)
        assert "bound implementation citation" in error
    assert bad == before
    repair = runtime.report_repair(error, bad)
    assert repair["required_implementation_ref"] == binding
    eligible = repair["eligible_evidence_ids"]
    assert eligible
    corrected = copy.deepcopy(bad)
    corrected["contract_review"][0].pop("source_refs")
    corrected["contract_review"][0]["evidence_ids"] = [eligible[0]]
    good = runtime.validate_report(corrected)
    assert good["decision"] == "pass_to_primary"
    trial.save(
        trial.BASE / "exact-archived-citation-control.json",
        {
            "original_report_sha256": trial.sha(
                old_root / ".agent/limited" / trial.FEATURE / "unit-1/reviewer.json"
            ),
            "bad_selected_refs_unchanged": before["contract_review"][0]["source_refs"],
            "candidate_rejection": error,
            "legal_corrected_refs": good["contract_review"][0]["source_refs"],
            "corrected_citation_passed": True,
            "verdict_and_business_contract_unchanged": True,
            "original_archive_read_only": True,
            "offline_only": True,
            "model_calls": 0,
        },
    )
    print(
        "exact archived bad citation rejected; real implementation refs passed",
        flush=True,
    )


if __name__ == "__main__":
    main()
