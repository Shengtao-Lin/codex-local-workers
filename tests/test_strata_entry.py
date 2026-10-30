import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from strata_entry import validate
from strata_model_entry import request_body


def state():
    return {
        "instances": [
            {
                "id": "fixed",
                "model": "iq3_s",
                "status": "ready",
                "context": 131072,
                "parallel": 1,
            }
        ]
    }


def test_expected_instance():
    assert validate(state(), {"models": []}, "iq3_s", 32768, "fixed")["id"] == "fixed"


def test_thinking_budget_preserves_contract_and_total_limit():
    original = {
        "max_tokens": 12288,
        "messages": [{"role": "user", "content": "contract"}],
    }
    assert request_body(original, 4096) == {**original, "reasoning_budget_tokens": 4096}
    assert "reasoning_budget_tokens" not in original
    for invalid in (True, 0, 12288, 13000):
        with pytest.raises(ValueError):
            request_body(original, invalid)


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", "changed"),
        ("model", "other"),
        ("status", "loading"),
        ("parallel", 2),
        ("context", 8192),
        ("context", "131072"),
    ],
)
def test_rejects_unverified_configuration(field, value):
    data = state()
    data["instances"][0][field] = value
    with pytest.raises(ValueError):
        validate(data, {"models": []}, "iq3_s", 32768, "fixed")


def test_rejects_second_instance_or_lmstudio_resident():
    data = state()
    data["instances"].append(copy.deepcopy(data["instances"][0]))
    with pytest.raises(ValueError):
        validate(data, {"models": []}, "iq3_s", 32768, "fixed")
    with pytest.raises(ValueError):
        validate(
            state(),
            {"models": [{"loaded_instances": [{"id": "lm"}]}]},
            "iq3_s",
            32768,
            "fixed",
        )
