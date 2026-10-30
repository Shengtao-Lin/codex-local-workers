"""Approval and global-stop guards, with no model or subprocess invocation."""

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import bounded_evidence_run as R


def test_missing_approval_never_starts(monkeypatch, tmp_path):
    monkeypatch.setattr(
        R.subprocess, "Popen", lambda *_a, **_k: pytest.fail("must not launch")
    )
    with pytest.raises(ValueError, match="human live approval"):
        R.run_cell("T1-A1", tmp_path / "missing.json", 9, time.time())


@pytest.mark.parametrize(("used", "age"), [(15, 0), (100, 0), (9, 121), (9, -10)])
def test_usage_stop(monkeypatch, tmp_path, used, age):
    registration = tmp_path / "registration.json"
    R.S.save(registration, {"fixture": True})
    monkeypatch.setattr(R, "REGISTRATION", registration)
    approval = tmp_path / "synthetic-approval.json"
    R.S.save(
        approval,
        {"registration_sha256": R.S.sha(registration), "human_approved_live": True},
    )
    with pytest.raises(ValueError, match="Fresh actual"):
        R.authorize(approval, used, time.time() - age)


def test_approval_binds_registration(monkeypatch, tmp_path):
    registration = tmp_path / "registration.json"
    R.S.save(registration, {"fixture": True})
    monkeypatch.setattr(R, "REGISTRATION", registration)
    approval = tmp_path / "synthetic-approval.json"
    R.S.save(approval, {"registration_sha256": "wrong", "human_approved_live": True})
    with pytest.raises(ValueError, match="exact registration"):
        R.authorize(approval, 9, time.time())


def test_unit_timeout_only_targets_started_tree(monkeypatch, tmp_path):
    monkeypatch.setattr(R.S, "BATCH", tmp_path)
    registration = tmp_path / "registration.json"
    R.S.save(registration, {"order": ["T1-A1"], "pins": {}})
    monkeypatch.setattr(R, "REGISTRATION", registration)
    approval = tmp_path / "synthetic-approval.json"
    R.S.save(
        approval,
        {"registration_sha256": R.S.sha(registration), "human_approved_live": True},
    )
    root = tmp_path / "isolated"
    (root / "src/product").mkdir(parents=True)
    (root / "src/product/code.py").write_text("# control", encoding="utf-8")
    R.S.save(root / ".agent/packet.json", {"task_id": "control", "run_id": "control"})
    R.S.save(
        tmp_path / "cells-v4.json",
        {
            "T1-A1": {
                "root": str(root),
                "files": {},
                "capture_policy_sha256": "control",
                "private_tests": "unused",
            }
        },
    )
    killed = []

    class Child:
        pid = 123456789
        returncode = -1
        waits = 0

        def wait(self, timeout):
            self.waits += 1
            if self.waits == 1:
                raise R.subprocess.TimeoutExpired("synthetic", timeout)

    monkeypatch.setattr(R.subprocess, "Popen", lambda *_a, **_k: Child())
    monkeypatch.setattr(R.subprocess, "run", lambda argv, **_kw: killed.append(argv))
    if R.os.name != "nt":
        monkeypatch.setattr(R.os, "killpg", lambda pid, _signal: killed.append(pid))
    result = R.run_cell("T1-A1", approval, 9, time.time())
    assert result["interrupted"] and result["stop_batch"]
    assert result["independent_checks"] == []
    assert len(killed) == 1 and "123456789" in str(killed)
    with pytest.raises(ValueError, match="already started"):
        R.run_cell("T1-A1", approval, 9, time.time())
