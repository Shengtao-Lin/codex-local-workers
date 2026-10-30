import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import harness_r4_medium as H
import reviewer_experiment_entry as BASE
import reviewer_medium_entry as A


def create(row, name, adapter):
    root = Path(row["root"])
    module = H.R.load(root / ".local-agents/reviewer-runtime.py", name)
    config = H.B.read(root / ".agent/experiment-config.json")
    runtime = adapter.install(module)(
        root,
        {**row["identity"], "review_id": name.replace("_", "-")},
        config,
        type(
            "NoModel", (), {"native_tools": copy.deepcopy(module.REVIEW_NATIVE_TOOLS)}
        )(),
    )
    return runtime, module


def test_all_twenty_preconditions_prompt_only_and_unchanged_gates():
    registry = H.B.read(H.BATCH / "registration.json")
    assert len(registry["cells"]) == 20
    assert sum(r["group"] == "original-sixteen" for r in registry["cells"]) == 16
    for row in registry["cells"]:
        assert not (Path(row["root"]) / ".agent/current-task.json").exists()
        runtime, module = create(row, "medium_control_" + row["id"], A)
        baseline, _ = create(row, "baseline_control_" + row["id"], BASE)
        assert runtime.system_prompt() == baseline.system_prompt().replace(
            "Reasoning strength: low.", "Reasoning strength: medium."
        )
        actual, expected = runtime.initial_payload(), baseline.initial_payload()
        actual["identity"]["review_id"] = expected["identity"]["review_id"]
        assert actual == expected
        assert runtime.client.native_tools == baseline.client.native_tools
        assert runtime.max_turns == baseline.max_turns == 16
        assert runtime.max_protocol_errors == baseline.max_protocol_errors == 4
        assert not runtime.read_lines and not baseline.read_lines
        with pytest.raises(module.ReviewError):
            runtime.validate_report(
                {
                    "assessment": "consistent",
                    "findings": [],
                    "contract_review": [],
                    "ordering_review": [],
                    "unverified_claims": [],
                }
            )
        H.R.assert_files(Path(row["root"]), row["files"])
        H.R.assert_files(Path(row["origin"]), row["origin_files"])


@pytest.mark.parametrize(
    "field,value",
    [
        ("reviewer_max_tokens", 8192),
        ("coder_model", "other-model"),
        ("max_model_turns", 99),
    ],
)
def test_real_archive_coder_config_cannot_be_changed(field, value):
    row = next(
        r
        for r in H.B.read(H.BATCH / "registration.json")["cells"]
        if r["group"] == "exposed-real"
    )
    root = Path(row["root"])
    module = H.R.load(
        root / ".local-agents/reviewer-runtime.py", "medium_config_negative_" + field
    )
    config = H.B.read(root / ".agent/experiment-config.json")
    config[field] = value
    with pytest.raises(ValueError, match="Trusted host configuration changed"):
        A.install(module)(
            root,
            {**row["identity"], "review_id": "negative-" + field.replace("_", "-")},
            config,
            type("NoModel", (), {"native_tools": None})(),
        )


@pytest.mark.parametrize(
    "reason",
    ["output_token_limit", "http_4xx", "http_5xx", "timeout", "input_too_large"],
)
def test_only_output_cap_permits_fixed_batch_continuation(reason):
    value = {
        "observed": "failed",
        "infra_failure": {"reason_code": reason},
        "failure_reason": "retained",
    }
    before = copy.deepcopy(value)
    result = H.boundary(H.BATCH / "cells/real-01/result.json", value)
    assert (result["infra_failure"] is None) == (reason == "output_token_limit")
    assert result["observed"] == "failed" and result["failure_reason"] == "retained"
    assert value == before
