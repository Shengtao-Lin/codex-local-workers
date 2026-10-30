import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import bounded_evidence_support as S
import bounded_evidence_tasks as T
import literal_check_feedback as L
import mapping_recovery_trial as M


@pytest.mark.parametrize("enabled", [False, True])
def test_actual_cli_only_adds_bound_failure_source_and_still_rechecks(
    tmp_path, enabled
):
    old = S.read(M.BATCH / "cells.json")["for-1"]
    root = tmp_path / "isolated"
    for name, digest in old["files"].items():
        source = Path(old["root"]) / name
        assert S.sha(source) == digest
        dest = root / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
    reference = T.extract(
        M.E.BATCH / "reference-checks/mapping/src/product/code.py", "mapping"
    )
    replay = root.parent / "replay.json"
    S.save(replay, [{"replacement": reference}])
    argv = M.command(root, "unit", replay)
    if enabled:
        argv.append("--failure-source")
    result = T.run(argv, root, timeout=180)
    assert result["exit_code"] == 0, result
    report = S.read(root / ".agent/unit-report.json")
    actual = report["consolidated_harness"]["actual"]
    assert actual["edits"] == actual["post_edit_checks"] == 1
    identity = S.read(root / ".agent/packet.json")
    archive = root / ".agent/tasks" / identity["task_id"] / "runs" / identity["run_id"]
    message = S.read(archive / "proposal-request-1.json")["messages"][1]["content"]
    facts = L.restore(message.split("\n", 1)[1])
    assert ("failed_test_sources" in facts) is enabled
    if enabled:
        evidence = facts["failed_test_sources"][0]
        assert evidence["sha256"] == S.sha(root / evidence["path"])
        assert "def __bool__(self):" in evidence["source"]
        assert "return False" in evidence["source"]
        assert actual["host_failure_reads"] == 1
        assert "<BEGIN failed_test_sources[0].source>" in message
    assert facts["validation_failure"]["status"] == "failed"
    assert not S.read(root / ".agent/unit-summary.json")["reviewer_started"]
