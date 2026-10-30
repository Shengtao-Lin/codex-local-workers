import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import bounded_evidence_support as S
import bounded_evidence_tasks as T
import literal_check_feedback as L
import mapping_recovery_trial as M
import reasoning_wire_candidate as W


@pytest.mark.parametrize(
    "guidance", [[], ["Untrusted local research note; not a new requirement."]]
)
def test_advisory_guidance_reaches_actual_request_without_changing_contract(
    tmp_path, guidance
):
    old = S.read(M.BATCH / "cells.json")["for-1"]
    root = tmp_path / "isolated"
    for name, digest in old["files"].items():
        source = Path(old["root"]) / name
        assert S.sha(source) == digest
        dest = root / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
    W.patch_client(root / ".local-agents/worker-runtime.py", allowed_root=tmp_path)
    packet = S.read(root / ".agent/packet.json")
    hard = packet["required_behavior"]
    packet["implementation_guidance"] = guidance
    (root / ".agent/packet.json").write_text(json.dumps(packet), encoding="utf-8")
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
    argv = M.command(root, "unit", replay) + [
        "--failure-source",
        "--repair-start",
        "--reviewer-forward-reasoning",
    ]
    result = T.run(argv, root, timeout=180)
    assert result["exit_code"] == 0, result
    archive = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
    message = S.read(archive / "proposal-request-1.json")["messages"][1]["content"]
    facts = L.restore(message.split("\n", 1)[1])
    assert facts["required_behavior"] == hard
    if guidance:
        assert facts["implementation_guidance"] == guidance
        assert "not a hard requirement" in facts["implementation_guidance_authority"]
    else:
        assert "implementation_guidance" not in facts
    summary = S.read(root / ".agent/unit-summary.json")
    assert summary["reviewer_input_authenticated"] and not summary["reviewer_started"]
