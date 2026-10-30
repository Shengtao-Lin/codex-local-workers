"""Freeze Reviewer controls from verified Coder-only canonical archives."""

import argparse
import time
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import installed_scope_trial as I
import packaged_profile_trial as P
import reviewer_profile_screen as V
import stable_execution_tasks as TASKS

BATCH = I.BASE / "reviewer-profile-screen-20261022-3"


def prepare(used):
    original = S.save
    pending = {}

    def save(path, value):
        if Path(path) == BATCH / "registration.json":
            pending["registration"] = value
        else:
            original(path, value)

    P.BATCH, P.ORDER = BATCH, V.ORDER
    S.save = save
    try:
        P.prepare(used)
    finally:
        S.save = original
    cells = S.read(BATCH / "cells.json")
    specs = TASKS.tasks(T.extract)
    controls = {}
    for cell in V.ORDER:
        row = cells[cell]
        topic = row["topic"]
        source = specs[topic]["reference"]
        if topic == "hash":
            source = source.replace('None if source_revision == "" else source_revision',
                                    'None if not source_revision or not source_revision.strip() else source_revision')
        elif topic == "collector":
            source = source.replace('if application.get("enabled") is not True:',
                                    'if not application.get("enabled"):')
        root = Path(row["root"])
        replay = BATCH / "oracle" / (cell + "-proposal.json")
        S.save(replay, [{"kind": "replacement", "content": source}])
        result = T.run(I.command(root, "coder", replay=replay), root, timeout=180)
        S.save(BATCH / "offline" / (cell + ".json"), result)
        assert result["exit_code"] == 0, result
        report = S.read(root / ".agent/unit-report.json")
        assert report["consolidated_harness"]["actual"]["model_requests"] == 0
        assert report["status"] == "validation_passed_pending_review"
        # Invoke the exact installed product verifier; do not forge handoff identity.
        import importlib.util
        spec = importlib.util.spec_from_file_location("screen_gate_" + cell, root / ".local-agents/local-unit.py")
        gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gate)
        config = S.read(root / ".agent/config.json")
        identity = gate.verify_handoff(root, report, config=config)
        run = root / ".agent/tasks" / identity["task_id"] / "runs" / identity["run_id"]
        assert not (run / "host-review-dispatch.json").exists()
        request = {"schema_version": 1, **identity, "review_id": "screen-" + identity["run_id"],
                   "execution_protocol": report["execution_protocol"]}
        S.save(run / "review-request.json", request)
        S.save(run / "review-config.json", {**config, "reviewer_compact_report": True, "reviewer_evidence_state": True})
        S.save(root / ".agent/screen-request.json", request)
        private = T.run([S.PYTHON, "-B", "-m", "pytest", "-q", "tests", row["private_tests"]], root)
        S.save(BATCH / "oracle" / (cell + "-checks.json"), private)
        assert (private["exit_code"] == 0) == (topic == "binding")
        controls[cell] = {"source_sha256": S.sha(root / row["target"]),
                          "config_sha256": S.sha(run / "review-config.json"),
                          "request_sha256": S.sha(root / ".agent/screen-request.json")}
    S.save(BATCH / "controls.json", controls)
    S.save(BATCH / "oracle.json", S.read(V.BATCH / "oracle.json"))
    reg = pending["registration"]
    reg.update(registered=3, gate="Correct positive pass1/1 and source-backed true defect rework2/2; first valid semantic outcome final",
               candidate="Unchanged packaged flat-v1 Reviewer; scripted Coder-only archives; normal product handoff verifier",
               scope="Reviewer semantic controls; no Coder model credit or feature acceptance",
               continue_rule="Complete three outcomes; stop infrastructure/safety/weekly60; no semantic resampling",
               preparation="All public/static/private controls observed; fresh dispatch records absent; independent full-chain offline replays passed")
    for path in (Path(__file__), BATCH / "oracle.json", BATCH / "controls.json"):
        reg["pins"][str(path)] = S.sha(path)
    S.save(BATCH / "registration.json", reg)
    print("Three verified archives frozen with unconsumed Reviewer dispatch")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=("prepare", "run"))
    p.add_argument("--cell", choices=V.ORDER)
    p.add_argument("--weekly-used", type=int, required=True)
    a = p.parse_args()
    if a.mode == "prepare":
        old = I.BASE / "reviewer-profile-screen-20261022-2"
        if not (old / "decision.json").exists():
            S.save(old / "decision.json", {"status": "PREPARATION_FAILED_NO_LIVE",
                "reason": "Coder-only mode intentionally does not materialize review-request; preparation assumed unit-mode side effect",
                "model_requests": 0, "registered_live": 0, "preservation": "All partial evidence retained"})
        prepare(a.weekly_used)
    else:
        V.BATCH = BATCH
        V.run(a.cell, a.weekly_used, time.time())
