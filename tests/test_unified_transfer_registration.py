"""Zero-model controls for the independent fixed transfer batch."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import unified_transfer_trial as N


def test_registration_and_fixed_budget():
    r = N.T.read(N.BATCH / "registration.json")
    assert r["registered_units"] == len(r["order"]) == 12
    assert r["weekly_used_ceiling"] == 15
    assert r["budget"]["coder_requests"] == 6
    assert r["budget"]["validations"] == r["budget"]["model_edits"] == 3
    assert r["budget"]["formatter_commands"] == 1
    assert N.T.read(N.U.BATCH / "decision.json")["conditional_migration_allowed"]
    assert N.T.read(N.BATCH / "entry-controls-v2.json")["model_calls"] == 0


def test_reference_and_negative_controls():
    results = N.T.read(N.BATCH / "fixture-controls.json")
    for topic in N.TOPICS:
        assert results[topic + "-reference"] == [0] * 5
        assert results[topic + "-baseline"][0] != 0
        assert results[topic + "-mutant"][:2] == [0, 1]


def test_fixed_models_and_truthful_candidate_flags():
    for name, row in N.T.read(N.BATCH / "cells.json").items():
        root = Path(row["root"])
        config = N.T.read(root / ".agent/config.json")
        assert config["coder_model"] == "qwen/qwen3-coder-30b"
        assert config["reviewer_model"] == "meta/muse-glimmer"
        assert config["coordinator_enabled"] is False
        assert config["coder_structured_output"] is True
        assert config.get("host_proposal_enabled", False) is ("-candidate-" in name)
        if "-candidate-" in name:
            assert config["experimental_unified_preparation"] is True
            assert config["experimental_static_span_repair"] is True
            assert config["experimental_prevalidation_format"] is True
            assert config["experimental_output_channel"] == "schema"
        else:
            assert Path(row["coder_runtime_dir"]).name == ".baseline-agents"


def test_all_inputs_unchanged_before_live_and_original_pin_chain():
    for row in N.T.read(N.BATCH / "cells.json").values():
        root = Path(row["root"])
        assert all(N.T.sha(root / p) == sha for p, sha in row["files"].items())
        assert not (root.parent / "started.json").exists()
    assert all(
        N.T.sha(p) == sha
        for p, sha in N.T.read(N.U.BATCH / "freeze.json")["pins"].items()
    )
