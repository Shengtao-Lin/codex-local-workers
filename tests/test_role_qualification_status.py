"""Evidence indexing must not manufacture model calls or Primary acceptance."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

BENCHMARKS = Path(__file__).resolve().parents[1] / "benchmarks"
sys.path.insert(0, str(BENCHMARKS))
SPEC = importlib.util.spec_from_file_location(
    "role_status", BENCHMARKS / "role_qualification_status.py"
)
STATUS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STATUS)


def test_status_is_not_model_or_acceptance_evidence(tmp_path):
    agent = tmp_path / ".agent"
    agent.mkdir()
    (agent / "coder.json").write_text(
        json.dumps({"status": "ready_for_review"}), encoding="utf-8"
    )
    result = STATUS.inspect(tmp_path)
    assert result["primary_decision"] is None
    assert result["model_started"] is False


def test_index_rejects_external_archive(tmp_path):
    agent = tmp_path / ".agent"
    agent.mkdir()
    (agent / "coder.json").write_text(
        json.dumps({"evidence_refs": {"run_archive": "../foreign"}}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="outside canonical"):
        STATUS.inspect(tmp_path)
