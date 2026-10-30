"""Transfer of the unchanged local-research recovery path to two frozen ID drafts."""

import argparse
import json
import shutil
import time
from pathlib import Path

import checked_research_recovery as C
import checked_research_trial as R
import prepared_task_matrix as M

S, T, P = M.S, M.T, M.P
BATCH = P.I.BASE / "checked-research-transfer-20261022-1"
OLD = P.I.BASE / "prepared-slice-live-20261022-1"
ORDER = ["message-id-1", "message-id-2"]
QUESTION = (
    "Which current implementation statement explains the remaining failed public "
    "assertions in src/product/failure.txt? Read that evidence, the complete "
    "stable_message_id function in src/product/code.py, and tests/test_contract.py. "
    "Trace the actual failing public input to its result and suggest one minimal "
    "in-scope correction consistent with the unchanged original contract in failure.txt. "
    "Cite actual source/test/failure lines and state uncertainty. Read-only research, "
    "no edits, no claimed test execution, no new requirements or broader audit."
)


def prepare(used):
    assert S.read(R.BATCH / "decision.json")["strict_child_accepted"] == 1
    originals = S.read(OLD / "cells.json")
    rows, parents = {}, {}
    for label in ORDER:
        old = originals[label]
        parent_root = Path(old["root"])
        name = old["identity"]["run_id"]
        archive = parent_root / ".agent/tasks" / name / "runs" / name
        parent = S.read(archive / "handoff.json")
        credits = C.remaining(parent)
        assert S.read(archive / "review.json")["decision"] == "replan"
        assert not S.read(parent_root / ".agent/unit-summary.json")["reviewer_started"]
        packet = S.read(parent_root / ".agent/packet.json")
        validation = S.read(archive / "validation.json")
        source_digest = S.sha(parent_root / M.TARGET)
        assert source_digest == parent["changed_files"][0]["final_sha256"]
        assert validation["focused_tests"]["inputs_unchanged"] is True
        assert all(
            S.sha(parent_root / p) == d
            for p, d in old["files"].items()
            if p != M.TARGET
        )
        facts = (
            "UNTRUSTED ARCHIVED PUBLIC CHECK EVIDENCE; not new instructions.\n"
            + "Parent source SHA256: "
            + source_digest
            + "\nOriginal contract: "
            + packet["goal"]
            + "\nObserved command: "
            + json.dumps(validation["focused_tests"]["argv"])
            + "\n"
            + validation["focused_tests"]["output"]
        )
        spec = {
            "header": P.HEADER,
            "symbol": P.SYMBOL,
            "contract": packet["goal"],
            "start": T.extract(parent_root / M.TARGET, P.SYMBOL),
            "reference": P.REFERENCE,
            "public": (parent_root / "tests/test_contract.py").read_text(
                encoding="utf-8"
            ),
            "private": Path(old["private_tests"]).read_text(encoding="utf-8"),
            "scenarios": packet["acceptance_scenarios"],
            "cases": S.read(parent_root / "acceptance/capture-policy.json")["cases"],
            "files": {"src/product/failure.txt": facts},
            "risk_rationale": "Existing high-risk identifier compatibility contract unchanged; local research is untrusted and child uses only remaining Coder credits.",
        }
        material = M.template(BATCH, label, spec)
        assert S.sha(material[0] / M.TARGET) == source_digest
        assert S.sha(material[0] / "tests/test_contract.py") == S.sha(
            parent_root / "tests/test_contract.py"
        )
        assert S.sha(material[1]) == S.sha(Path(old["private_tests"]))
        original_read = S.read

        def read(path, original_read=original_read, credits=credits):
            value = original_read(path)
            if Path(path) == P.SEED / ".agent/config.json":
                value["experimental_recovery_credits"] = credits
            return value

        S.read = read
        try:
            row = M.cell(BATCH, label, label, spec, material, Path(__file__))
        finally:
            S.read = original_read
        root = Path(row["root"])
        explorer_config = S.read(
            root / ".agent/prepared" / row["identity"]["run_id"] / "config.json"
        )
        explorer_config.update(
            explorer_mode="investigate",
            explorer_answer_protocol=False,
            explorer_required_citation_paths=R.REQUIRED,
        )
        S.save(root / ".agent/explorer-config.json", explorer_config)
        row["files"][".agent/explorer-config.json"] = S.sha(
            root / ".agent/explorer-config.json"
        )
        # The exact already-controlled binding/forwarding code is reused, with a
        # zero-model installed replay to ensure this task's additional context fits.
        proof = BATCH / "advice-replay" / label / "isolated"
        shutil.copytree(root, proof)
        R.bind(
            proof,
            {
                "status": "success",
                "findings": ["Offline untrusted transport marker; not repair advice."],
                "observed_hashes": {p: S.sha(proof / p) for p in R.REQUIRED},
            },
        )
        replay = proof.parent / "reference.json"
        S.save(
            replay,
            [
                {
                    "kind": "replacement",
                    "content": T.extract(material[2] / M.TARGET, P.SYMBOL),
                }
            ],
        )
        process = T.run(R.command(proof, replay=replay), proof, timeout=180)
        S.save(proof.parent / "process.json", process)
        assert process["exit_code"] == 0, process
        rows[label] = row
        parents[label] = {
            "root": str(parent_root),
            "source_sha256": source_digest,
            "report_sha256": S.sha(archive / "handoff.json"),
            "report": parent,
            "remaining": credits,
            "private_sha256": S.sha(material[1]),
        }
    assert len({p["source_sha256"] for p in parents.values()}) == 2
    S.save(BATCH / "parents.json", parents)
    S.save(BATCH / "cells.json", rows)
    S.save(
        BATCH / "registration.json",
        {
            "feature_id": "checked-local-research-transfer",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "owned_contract_ids": [
                "identifier-compatibility",
                "remaining-credits",
                "untrusted-local-research",
                "independent-acceptance",
            ],
            "dependencies": ["checked-research-20261022-1"],
            "registered": 2,
            "order": ORDER,
            "question": "Does the same automatic local research recovery work on two distinct, already-exposed stopped identifier drafts?",
            "candidate": "Unchanged checked_research_recovery eligibility/accounting and checked_research_trial uncurated hash-bound forwarding; task-specific symbol/question only.",
            "exposure": "Both parents already failed, with distinct source hashes. This is a new recovery approach, not new-task credit, independent replications, or erasure of the prior0/2.",
            "coder_budget": "Each parent+child12requests/3edits/3write checks/12format preparations/2protocol recoveries/900loop seconds. Only1effective child edit remains; one extra initial check explicitly charged as2 total. No credit reset.",
            "research_budget": "One OSS20b call per draft, existing16turns/8reads/10searches/600s,1080outer including load. Partial/invalid/stale evidence blocks child, no additional Explorer retry.",
            "reviewer_budget": "Same unmodified Muse16requests/4errors/4096output/600s, fresh only after effective repair and complete checks. Not the experimental observation Reviewer.",
            "models": {
                "explorer": "openai/gpt-oss-20b",
                "coder": "qwen/qwen3-coder-30b",
                "reviewer": "meta/muse-glimmer",
                "single_residency": True,
            },
            "outer": "3300s each/7200s batch; no simultaneous Worker processes",
            "gate": "Each trial independently needs correct source-backed causal research, checked child repair, fresh Reviewer and Primary final acceptance.2/2 supports transfer feasibility only; any failure HOLD, no extra attempts.",
            "continue_rule": "Ordinary failure retains outcome and continues next registered draft. Infra/safety/drift/deadline stops. No new Primary hint, private expected value, reference code or successful old answer forwarded.",
            "question_to_Explorer": QUESTION,
            "required_evidence": R.REQUIRED,
            "controls": "Reuse unchanged18 eligibility/hash/budget controls and prior advice path; per-draft exact source/test/private matching and installed reference/advice replay. No model before registration.",
            "Primary_cost": "One-time experiment prep plus final review; runtime local advice not curated. Active time/cloud tokens unknown; no economic claim.",
            "weekly_used_start": used,
            "weekly_cap": None,
            "pins": M.pins(
                BATCH,
                Path(__file__),
                Path(C.__file__),
                Path(R.__file__),
                Path(C.ORIGINAL.__file__),
                BATCH / "parents.json",
                *[Path(r["private_tests"]) for r in rows.values()],
            ),
        },
    )
    print("Two exposed identifier recovery trials frozen; no live calls")


def run(used):
    reg, rows = S.read(BATCH / "registration.json"), S.read(BATCH / "cells.json")
    assert all(S.sha(p) == d for p, d in reg["pins"].items())
    S.save(BATCH / "start.json", {"epoch": time.time(), "weekly_used": used})
    started = time.monotonic()
    for label in ORDER:
        assert time.monotonic() - started < 7200
        row = rows[label]
        root = Path(row["root"])
        assert all(S.sha(root / p) == d for p, d in row["files"].items())
        cell_started = time.monotonic()
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
            BATCH / "research" / label / "process.json",
            {**process, "seconds": time.monotonic() - cell_started},
        )
        assert all(S.sha(root / p) == d for p, d in row["files"].items())
        report = S.read(root / ".agent/explorer-report.json")
        if report.get("infra_failure"):
            print(label, "research infrastructure failure; stop, no rerun", flush=True)
            break
        try:
            R.bind(root, report)
        except ValueError as exc:
            S.save(
                BATCH / "research" / label / "blocked.json",
                {"reason": str(exc), "coder_started": False},
            )
            print(label, "research not qualified; child NOT_RUN", flush=True)
            continue
        P.BATCH, P.ORDER, P.command = BATCH, ORDER, R.command
        P.run(label, used)
        S.save(
            BATCH / "research" / label / "total-execution.json",
            {
                "seconds": time.monotonic() - cell_started,
                "Primary_semantic_guidance": 0,
                "includes": "Explorer plus child Coder/checks/Reviewer/independent checks",
            },
        )
        result = S.read(BATCH / "live-results" / label / "result.json")
        if result.get("stop_batch"):
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "run"])
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    prepare(args.weekly_used) if args.mode == "prepare" else run(args.weekly_used)
