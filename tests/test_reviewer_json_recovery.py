import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import reviewer_json_recovery as J
import test_reviewer_contract_first as C


def make(tmp_path, replies):
    original, module, client = C.make(tmp_path, [])
    client.native_tools = copy.deepcopy(module.REVIEW_NATIVE_TOOLS)
    runtime = J.wrap(type(original), module)(
        tmp_path, original.request, original.config, client
    )
    runtime.forward_effort = True
    client.reasoning_effort = None
    client.structured_output = False
    client.action_schema = None
    client.schema_name = "original"
    pending = iter(replies)
    client.formats = []

    def complete(messages):
        client.calls += 1
        client.messages.append(copy.deepcopy(messages))
        client.formats.append("json" if client.native_tools is None else "native")
        value = next(pending)
        if isinstance(value, str):
            raise module.WORKER.ModelRequestError(value, value, {})
        return json.dumps(value)

    client.complete = complete
    return runtime, module, client


def test_two_truncations_can_recover_format_but_keep_original_report_gates(tmp_path):
    runtime, _, client = make(
        tmp_path, [C.predict(), "output_token_limit", "output_token_limit", C.report()]
    )
    one, two = C.facts(C.profile())
    with one, two:
        report = runtime.run()
    assert report["decision"] == "pass_to_primary"
    assert client.formats == ["native", "native", "native", "json"]
    assert (
        report["reviewer_model_calls"] == 4 and report["shared_error_budget_used"] == 2
    )
    assert runtime.json_recovery_used
    assert client.action_schema is None and client.schema_name == "original"
    assert client.structured_output is False and client.reasoning_effort is None


def test_successful_native_judgment_never_resampled(tmp_path):
    runtime, _, client = make(tmp_path, [C.predict(), C.report()])
    one, two = C.facts(C.profile())
    with one, two:
        assert runtime.run()["decision"] == "pass_to_primary"
    assert client.calls == 2 and not runtime.json_recovery_used


def test_semantic_contradiction_not_bypassed_by_json_format(tmp_path):
    runtime, module, client = make(
        tmp_path, [C.predict(), "output_token_limit", "output_token_limit", C.report()]
    )
    one, two = C.facts(C.profile("requested"))
    with one, two, pytest.raises(module.ReviewError):
        runtime.run()
    assert client.calls == 4 and not (runtime.review_root / "completed.json").exists()


def test_json_truncation_does_not_start_more_attempts(tmp_path):
    runtime, module, client = make(tmp_path, [C.predict(), *["output_token_limit"] * 3])
    one, two = C.facts(C.profile())
    with one, two, pytest.raises(module.WORKER.ModelRequestError):
        runtime.run()
    assert client.calls == 4 and len(runtime.output_failures) == 3


def test_prediction_failures_cannot_jump_to_source_report(tmp_path):
    runtime, module, client = make(tmp_path, ["output_token_limit"] * 2)
    one, two = C.facts(C.profile())
    with one, two, pytest.raises(module.WORKER.ModelRequestError):
        runtime.run()
    assert client.calls == 2 and not runtime.json_recovery_used


@pytest.mark.parametrize("limit", ["requests", "errors", "deadline", "source"])
def test_changed_format_never_bypasses_global_stop(tmp_path, limit):
    runtime, module, client = make(
        tmp_path, [C.predict(), "output_token_limit", "output_token_limit", C.report()]
    )
    if limit == "requests":
        runtime.max_turns = 3
    elif limit == "errors":
        runtime.max_protocol_errors = 2
    else:
        original = client.complete

        def complete(messages):
            if client.calls == 2:
                if limit == "deadline":
                    runtime.deadline = 0
                else:

                    def drift():
                        raise module.ReviewError("source drift")

                    runtime._assert_inputs_current = drift
            return original(messages)

        client.complete = complete
    one, two = C.facts(C.profile())
    with one, two, pytest.raises(module.ReviewError):
        runtime.run()
    assert client.calls == 3 and not runtime.json_recovery_used
    assert not (runtime.review_root / "completed.json").exists()
