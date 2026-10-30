"""Narrow transport candidate must retain the existing substantive gates."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import reviewer_direct_report as D
import test_reviewer_contract_first as C


def candidate(tmp_path, replies):
    runtime, module, client = C.make(tmp_path, replies)
    runtime.__class__ = D.install(module, type(runtime), enabled=True)
    return runtime, module, client


def test_default_is_same_class():
    class Base:
        pass
    assert D.install(SimpleNamespace(), Base) is Base
    with pytest.raises(ValueError):
        D.install(SimpleNamespace(), Base, enabled="yes")


def test_prediction_unchanged_source_first_required(tmp_path):
    runtime, _, client = candidate(tmp_path, [C.predict(), C.report()])
    one, two = C.facts(C.profile())
    with one, two:
        result = runtime.run()
    assert result["decision"] == "pass_to_primary"
    assert client.profiles[0]["choice"] == "auto"
    assert client.profiles[1]["choice"] == "required"
    assert "Reasoning strength: low." in client.messages[1][0]["content"]
    assert result["request_profiles"][1]["selection"] == "explicit-direct-report-v1"
    assert result["reviewer_model_calls"] == 2


def test_two_output_limits_still_stop(tmp_path):
    runtime, module, client = candidate(tmp_path, [C.predict(), "output_token_limit", "output_token_limit"])
    one, two = C.facts(C.profile())
    with one, two, pytest.raises(module.WORKER.ModelRequestError):
        runtime.run()
    assert client.calls == 3
    assert len(runtime.output_failures) == 2
    assert not (runtime.review_root / "completed.json").exists()


def test_owned_uncertainty_cannot_pass(tmp_path):
    contradiction = C.report()
    contradiction["arguments"]["uncertainties"] = [{"contract_id": "behavior-1", "text": "Unresolved owned behavior"}]
    runtime, module, client = candidate(tmp_path, [C.predict()] + [contradiction] * 4)
    one, two = C.facts(C.profile())
    with one, two, pytest.raises(module.ReviewError):
        runtime.run()
    assert runtime.protocol_errors == 4
    assert client.calls == 5
    assert not (runtime.review_root / "completed.json").exists()


def test_one_output_limit_and_shape_recovery_share_budget(tmp_path):
    invalid = {"action": "REPORT", "arguments": {}}
    runtime, _, client = candidate(tmp_path, [C.predict(), "output_token_limit", invalid, C.report()])
    one, two = C.facts(C.profile())
    with one, two:
        result = runtime.run()
    assert result["reviewer_model_calls"] == 4
    assert result["shared_error_budget_used"] == 2
    assert result["output_limit_failures"] == 1
    assert all(p["choice"] == "required" for p in client.profiles[1:])


def test_prediction_disagreement_still_escalates(tmp_path):
    runtime, _, _ = candidate(tmp_path, [C.predict(), C.report(), C.report("contract_conflict", "uncertain")])
    one, two = C.facts(C.profile("requested"))
    with one, two:
        result = runtime.run()
    assert result["decision"] == "escalate"
    assert runtime.protocol_errors == 1


@pytest.mark.parametrize("limit", ["requests", "deadline", "drift"])
def test_existing_global_stop_still_applies(tmp_path, limit):
    runtime, module, client = candidate(tmp_path, [C.predict(), C.report()])
    if limit == "requests":
        runtime.max_turns = 1
    else:
        original = client.complete
        def complete(messages):
            value = original(messages)
            if limit == "deadline":
                runtime.deadline = 0
            else:
                runtime._assert_inputs_current = lambda: (_ for _ in ()).throw(module.ReviewError("source drift"))
            return value
        client.complete = complete
    one, two = C.facts(C.profile())
    with one, two, pytest.raises(module.ReviewError):
        runtime.run()
    assert client.calls == 1
