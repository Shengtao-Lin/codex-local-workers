"""Bounded untrusted explanations; original edit protections remain authoritative."""

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import exception_reasoning_diagnostic as R


@pytest.mark.parametrize(
    "raw",
    [
        "{}",
        '{"cause":"x","cause":"y"}',
        json.dumps({"cause": "", "affected_symbol": "x", "required_change": "x"}),
        json.dumps(
            {"cause": "x" * 1501, "affected_symbol": "x", "required_change": "x"}
        ),
    ],
)
def test_bad_explanations_rejected(raw):
    with pytest.raises(ValueError):
        R.diagnosis(raw)


def test_explanation_is_untrusted_extra_data_not_a_contract_change():
    fixture = R.T.read(R.BATCH / "fixture.json")
    before = copy.deepcopy(fixture)
    direct = R.repair_messages(fixture)
    value = {
        "cause": "untrusted cause",
        "affected_symbol": "unknown",
        "required_change": "untrusted claim",
    }
    diagnosed = R.repair_messages(fixture, R.diagnosis(json.dumps(value)))
    assert direct[0] == diagnosed[0]
    a = R.D.INTERFACE.restore_literal(direct[1]["content"])
    b = R.D.INTERFACE.restore_literal(diagnosed[1]["content"])
    assert b.pop("untrusted_model_diagnosis") == value
    assert a == b and fixture == before


def test_pristine_cases_and_original_positive_negative_controls():
    assert (
        R.T.sha(R.BATCH / "snapshot.py")
        == R.T.read(R.BATCH / "fixture.json")["binding"]["sha256"]
    )
    for row in R.T.read(R.BATCH / "cells.json").values():
        root = Path(row["root"])
        assert all(R.T.sha(root / p) == sha for p, sha in row["files"].items())
        assert not (root / ".agent").exists()
    assert all(
        R.T.sha(p) == sha
        for p, sha in R.T.read(R.C.BATCH / "freeze.json")["pins"].items()
    )
