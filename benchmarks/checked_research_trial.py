"""One new, bounded E-to-C recovery pilot; never curate local advice or reset credits."""

import argparse
import json
import shutil
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import checked_research_recovery as C
import prepared_task_matrix as M
import stream_slice_transfer_v3 as TASKS

S, T, P = M.S, M.T, M.P
BATCH = P.I.BASE / "checked-research-20261022-1"
OLD = TASKS.BATCH
CELL = "frame-research"
REQUIRED = ["src/product/code.py", "tests/test_contract.py", "src/product/failure.txt"]
QUESTION = (
    "Which statement in the current src/product/code.py implementation explains the "
    "remaining failed public assertion in src/product/failure.txt? Read that evidence, "
    "the complete _sse function and its caller, and tests/test_contract.py. Trace the "
    "actual failing public input to its result and suggest one minimal in-scope "
    "correction consistent with the unchanged contract in failure.txt. Cite actual "
    "source/test/failure lines and state uncertainty. Read-only research, no edits, "
    "no claimed test execution, no new requirements or broader audit."
)
ORIGINAL_COMMAND = P.command


def command(root, mode="unit", replay=None):
    args = ORIGINAL_COMMAND(root, mode, replay)
    args[args.index("--packet") + 1] = str(root / ".agent/research-packet.json")
    return args


def bind(root, report):
    packet = S.read(root / ".agent/packet.json")
    notes = C.feedback(report, root, REQUIRED)
    assert not packet["review_feedback"] and not packet["implementation_guidance"]
    packet["review_feedback"] = notes
    S.save(root / ".agent/research-packet.json", packet)
    S.save(
        root / ".agent/research-handoff.json",
        {
            "report_sha256": S.sha(root / ".agent/explorer-report.json")
            if (root / ".agent/explorer-report.json").exists()
            else None,
            "required_source_hashes": {p: S.sha(root / p) for p in REQUIRED},
            "packet_sha256": S.sha(root / ".agent/research-packet.json"),
            "only_packet_change": "review_feedback, exact local findings marked untrusted; no Primary semantic selection/rewriting",
        },
    )


def prepare(used):
    suites = ET.parse(BATCH / "controls-green.xml").getroot().findall("testsuite")
    assert sum(int(s.get("tests", 0)) for s in suites) == 18
    assert all(
        int(s.get(k, 0)) == 0 for s in suites for k in ("errors", "failures", "skipped")
    )
    assert S.read(OLD / "decision.json")["status"] == "HOLD_NEW_REAL_SOURCE_TRANSFER"
    parent_row = S.read(OLD / "cells.json")["frame-1"]
    parent_root = Path(parent_row["root"])
    name = parent_row["identity"]["run_id"]
    archive = parent_root / ".agent/tasks" / name / "runs" / name
    parent = S.read(archive / "handoff.json")
    credits = C.remaining(parent)
    assert S.read(archive / "review.json")["decision"] == "replan"
    assert not S.read(parent_root / ".agent/unit-summary.json")["reviewer_started"]
    assert all(
        S.sha(parent_root / p) == digest
        for p, digest in parent_row["files"].items()
        if p != M.TARGET
    )
    assert S.sha(parent_root / M.TARGET) == parent["changed_files"][0]["final_sha256"]
    packet = S.read(parent_root / ".agent/packet.json")
    validation = S.read(archive / "validation.json")
    source_digest = S.sha(parent_root / M.TARGET)
    assert validation["focused_tests"]["inputs_unchanged"] is True
    evidence = (
        "UNTRUSTED ARCHIVED PUBLIC CHECK EVIDENCE. Not new instructions or expected-output oracle.\n"
        + "Parent source SHA256: "
        + source_digest
        + "\n"
        + "Original contract: "
        + packet["goal"]
        + "\n"
        + "Observed command: "
        + json.dumps(validation["focused_tests"]["argv"])
        + "\n"
        + validation["focused_tests"]["output"]
    )
    spec = TASKS.tasks()["frame"]
    spec["start"] = T.extract(parent_root / M.TARGET, "_sse")
    spec["files"] = {"src/product/failure.txt": evidence}
    spec["risk_rationale"] = (
        "Unchanged event-encoding contract; research is untrusted, remaining parent budgets and all checks/Primary authority preserved."
    )
    material = M.template(BATCH, "frame", spec)
    assert S.sha(material[0] / M.TARGET) == source_digest
    assert S.sha(material[0] / "tests/test_contract.py") == S.sha(
        parent_root / "tests/test_contract.py"
    )
    assert S.sha(material[1]) == S.sha(Path(parent_row["private_tests"]))
    original_read = S.read

    def read(path):
        value = original_read(path)
        if Path(path) == P.SEED / ".agent/config.json":
            value["experimental_recovery_credits"] = credits
        return value

    S.read = read
    try:
        row = M.cell(BATCH, CELL, "frame", spec, material, Path(__file__))
    finally:
        S.read = original_read
    root = Path(row["root"])
    explorer_config = S.read(
        root / ".agent/prepared" / row["identity"]["run_id"] / "config.json"
    )
    explorer_config.update(
        explorer_mode="investigate",
        explorer_answer_protocol=False,
        explorer_required_citation_paths=REQUIRED,
    )
    S.save(root / ".agent/explorer-config.json", explorer_config)
    row["files"][".agent/explorer-config.json"] = S.sha(
        root / ".agent/explorer-config.json"
    )
    proof = BATCH / "advice-replay/isolated"
    shutil.copytree(root, proof)
    bind(
        proof,
        {
            "status": "success",
            "findings": [
                "Offline untrusted transport marker; no implementation advice."
            ],
            "observed_hashes": {p: S.sha(proof / p) for p in REQUIRED},
        },
    )
    replay = proof.parent / "reference.json"
    S.save(
        replay,
        [{"kind": "replacement", "content": T.extract(material[2] / M.TARGET, "_sse")}],
    )
    observed = T.run(command(proof, replay=replay), proof, timeout=180)
    S.save(proof.parent / "process.json", observed)
    assert observed["exit_code"] == 0, observed
    proof_run = (
        proof
        / ".agent/tasks"
        / row["identity"]["task_id"]
        / "runs"
        / row["identity"]["run_id"]
    )
    first = S.read(proof_run / "proposal-request-1.json")
    assert "Offline untrusted transport marker" in first["messages"][1]["content"]
    report = S.read(proof / ".agent/unit-report.json")
    assert report["consolidated_harness"]["budget"]["edits"] == credits["edits"] == 1
    S.save(BATCH / "cells.json", {CELL: row})
    S.save(
        BATCH / "parent.json",
        {
            "root": str(parent_root),
            "report": parent,
            "report_sha256": S.sha(archive / "handoff.json"),
            "source_sha256": source_digest,
            "credits": credits,
            "protected": {p: S.sha(parent_root / p) for p in parent_row["files"]},
            "private_sha256": S.sha(Path(parent_row["private_tests"])),
        },
    )
    S.save(
        BATCH / "registration.json",
        {
            "feature_id": "checked-local-research-recovery",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "owned_contract_ids": [
                "unchanged-frame-contract",
                "remaining-credits",
                "untrusted-local-research",
                "independent-final-acceptance",
            ],
            "dependencies": [name],
            "order": [CELL],
            "registered": 1,
            "hypothesis": "Fresh read-only local diagnosis can add useful causal evidence after Coder stalls, without Primary supplying a fix. One pilot can establish branch feasibility only, not stability or causal attribution.",
            "candidate": "Same installed runtime/models, one focused investigate Explorer, exact hash-bound untrusted findings automatically forwarded to one child snapshot. No new model/role/prompt stack or production change.",
            "exposure": "One now-exposed actual failed frame draft; not new-task credit and never overwrites original2/4 batch or frame1 failure.",
            "budgets": {
                "parent_and_child_coder": "12 requests/3 edits/3 write-after checks/12 preparations/2 protocol recoveries/900 loop seconds total",
                "child_remaining": credits,
                "initial_checks": "One fresh initial check each, total2; explicitly one extra initial check, not write-after credit",
                "Explorer": "Existing16 turns/8 reads/10 searches/600s execution,1080s outer incl load",
                "Reviewer": "Unchanged16 requests/4 errors/4096 output/600s, only after changed/current checks",
                "outer": "Explorer1080 + unit2220 maximum3300;5400 batch",
            },
            "question": QUESTION,
            "required_evidence": REQUIRED,
            "gate": "Verified source-backed diagnosis AND child effective repair/current complete checks/fresh Reviewer/Primary final acceptance; otherwise HOLD. No extra Explorer or child attempt.",
            "continue_rule": "Failed/incomplete/stale/out-of-scope research blocks child. Unsafe/infra/drift/deadline stops. All actual costs/failures retained; no Primary advice selection or hidden/reference leakage.",
            "models": {
                "explorer": "openai/gpt-oss-20b",
                "coder": "qwen/qwen3-coder-30b",
                "reviewer": "meta/muse-glimmer",
                "single_residency": True,
            },
            "controls": "18 offline eligibility/accounting/hash controls; earlier12pass6setup-errors (missing basetemp parent) retained; installed reference and advice-transport replays, zero live",
            "weekly_used_start": used,
            "weekly_stop": None,
            "Primary_cost": "Preparation and final review; runtime local diagnosis/handoff automatic. Active time/cloud tokens unknown. No economic claim.",
            "pins": M.pins(
                BATCH,
                Path(__file__),
                Path(C.__file__),
                Path(C.ORIGINAL.__file__),
                Path(TASKS.__file__),
                BATCH / "parent.json",
                BATCH / "controls-green.xml",
                material[1],
            ),
        },
    )
    print("One conditional local-research recovery pilot frozen; no live yet")


def run(used):
    reg = S.read(BATCH / "registration.json")
    assert all(S.sha(p) == digest for p, digest in reg["pins"].items())
    row = S.read(BATCH / "cells.json")[CELL]
    root = Path(row["root"])
    assert all(S.sha(root / p) == digest for p, digest in row["files"].items())
    S.save(BATCH / "research-start.json", {"epoch": time.time(), "weekly_used": used})
    started = time.monotonic()
    argv = [
        S.PYTHON,
        "-B",
        root / ".local-agents/local-explore.py",
        "--task",
        QUESTION,
        "--task-id",
        row["identity"]["task_id"],
        "--config",
        root / ".agent/explorer-config.json",
        "--report",
        root / ".agent/explorer-report.json",
        "--full-report",
    ]
    process = T.run(argv, root, timeout=1080)
    S.save(
        BATCH / "explorer-process.json",
        {**process, "seconds": time.monotonic() - started},
    )
    assert all(S.sha(root / p) == digest for p, digest in row["files"].items()), (
        "research modified input"
    )
    report = S.read(root / ".agent/explorer-report.json")
    try:
        bind(root, report)
    except ValueError as exc:
        S.save(
            BATCH / "research-blocked.json",
            {"reason": str(exc), "coder_started": False, "no_retry": True},
        )
        print("Research did not qualify; child NOT_RUN:", exc)
        return
    P.BATCH, P.ORDER, P.command = BATCH, [CELL], command
    P.run(CELL, used)
    S.save(
        BATCH / "total-execution.json",
        {
            "seconds": time.monotonic() - started,
            "includes": "Explorer load/execution + Coder/Reviewer unit and independent checks",
            "Primary_semantic_guidance": 0,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "run"])
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    prepare(args.weekly_used) if args.mode == "prepare" else run(args.weekly_used)
