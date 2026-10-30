"""Offline audit of existing inherited-rework and experiment evidence boundaries."""

import json
import shutil
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import explorer_trace_trial as E
import literal_check_feedback as L
import mapping_recovery_trial as M

BATCH = (
    S.KIT / "benchmarks/work/harness-convergence/inherited-feedback-audit-20261020-1"
)


def run(batch=BATCH, expected_visible=False):
    BATCH = Path(batch)
    old = S.read(M.BATCH / "cells.json")["for-1"]
    source_root = Path(old["root"])
    parent = old["identity"]
    parent_run = (
        source_root / ".agent/tasks" / parent["task_id"] / "runs" / parent["run_id"]
    )
    note = S.read(E.BATCH / "isolated/.agent/explorer.json")["findings"]
    rows = []
    for case in ("override", "unchanged-control", "versioned-control"):
        root = BATCH / case / "isolated"
        root.mkdir(parents=True, exist_ok=False)
        for name, digest in old["files"].items():
            source = source_root / name
            if S.sha(source) != digest:
                raise ValueError("Frozen parent changed")
            dest = root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
        dest_run = root / ".agent/tasks" / parent["task_id"] / "runs" / parent["run_id"]
        shutil.copytree(parent_run, dest_run)
        before_parent = {
            p.relative_to(dest_run).as_posix(): S.sha(p)
            for p in dest_run.rglob("*")
            if p.is_file()
        }
        child = {
            "schema_version": 2,
            "task_id": parent["task_id"],
            "unit_id": parent["unit_id"],
            "run_id": parent["run_id"] + "-child",
            "packet_revision": 2,
            "parent_run_id": parent["run_id"],
            "preserve_contract": True,
            "review_feedback": [
                {
                    "source": "local_explorer_untrusted",
                    "text": "\n".join(note),
                    "verify_in_review": False,
                }
            ],
        }
        if case == "override":
            child["implementation_guidance"] = note
        S.save(root / ".agent/child-packet.json", child)
        if case == "versioned-control":
            policy_path = root / "acceptance/capture-policy.json"
            config_path = root / ".agent/config.json"
            S.save(
                root.parent / "initial-controls.json",
                {
                    "config": S.read(config_path),
                    "policy": S.read(policy_path),
                    "config_sha256": S.sha(config_path),
                    "policy_sha256": S.sha(policy_path),
                },
            )
            policy = S.read(policy_path)
            policy["identity"] = {k: child[k] for k in ("task_id", "unit_id", "run_id")}
            policy_path.write_text(json.dumps(policy, indent=2), encoding="utf-8")
            config = S.read(config_path)
            config["experimental_capture_policy_sha256"] = S.sha(policy_path)
            config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        argv = M.command(root, "preflight")
        argv[argv.index("--packet") + 1] = str(root / ".agent/child-packet.json")
        result = T.run(argv, root, timeout=180)
        S.save(root.parent / "preflight.json", result)
        row = {"case": case, "preflight_exit": result["exit_code"], "model_calls": 0}
        if case == "override":
            assert (
                result["exit_code"]
                and "cannot override preserved fields" in result["stderr"]
            )
        elif case == "unchanged-control":
            assert (
                result["exit_code"] and "Capture identity differs" in result["stderr"]
            )
        else:
            assert result["exit_code"] == 0, result
            replay = root.parent / "replay.json"
            S.save(
                replay,
                [
                    {
                        "replacement": T.extract(
                            M.E.BATCH / "reference-checks/mapping/src/product/code.py",
                            "mapping",
                        )
                    }
                ],
            )
            argv = M.command(root, "unit", replay)
            argv[argv.index("--packet") + 1] = str(root / ".agent/child-packet.json")
            result = T.run(argv, root, timeout=180)
            S.save(root.parent / "unit-replay.json", result)
            assert result["exit_code"] == 0, result
            archive = (
                root / ".agent/tasks" / child["task_id"] / "runs" / child["run_id"]
            )
            packet = S.read(archive / "packet.json")
            original = S.read(dest_run / "packet.json")
            fields = [
                "goal",
                "risk",
                "scope",
                "required_behavior",
                "owned_contract_ids",
                "focused_tests",
                "validation_profile",
            ]
            assert all(packet[k] == original[k] for k in fields)
            message = S.read(archive / "proposal-request-1.json")["messages"][1][
                "content"
            ]
            facts = L.restore(message.split("\n", 1)[1])
            row.update(
                hard_contract_preserved=True,
                canonical_reviewer_input_authenticated=True,
                parent_input_state=packet["_inheritance"]["parent_input_state"],
                feedback_present_in_packet=bool(packet["review_feedback"]),
                feedback_present_in_model_input="review_feedback" in facts,
                traceback_present_in_packet=bool(
                    packet["_inheritance"]["rework_traceback"]
                ),
                traceback_present_in_model_input="inherited_execution" in facts,
            )
            assert row["feedback_present_in_model_input"] is expected_visible
            assert row["traceback_present_in_model_input"] is expected_visible
        assert all(S.sha(dest_run / p) == digest for p, digest in before_parent.items())
        row["parent_archive_unchanged"] = True
        rows.append(row)
    S.save(
        BATCH / "decision.json",
        {
            "status": "OFFLINE_BOUNDARIES_CONFIRMED",
            "rows": rows,
            "model_calls": 0,
            "production_modified": False,
            "finding": "Reuse review_feedback, not forbidden implementation_guidance override. Per-run capture identities need explicitly versioned controls; old validation cannot be reused. All parent archives preserved; actual no-network child checks/handoff authenticated.",
            "feedback_visible": expected_visible,
            "scope": "Experiment adapter/recovery readiness only, not a model quality result or permission to overwrite production control inputs.",
        },
    )
    print(rows)


if __name__ == "__main__":
    run()
