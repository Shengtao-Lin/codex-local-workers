from evaluation_harness.adapters.agent_runtime_kit import AgentRuntimeKitAdapter
from evaluation_harness.adapters.base import AdapterContext
from evaluation_harness.adapters.generic_otel import GenericOtelAdapter
from tests.conftest import load_trace


def test_generic_turn_mode_embeds_history(application) -> None:
    context = AdapterContext(application=application, row_mode="turn")
    samples = GenericOtelAdapter().normalize(load_trace("generic_multi_turn.json"), context=context)
    assert len(samples) == 2
    assert samples[0].turn_index == 0
    assert samples[1].turn_index == 1
    assert [message.role for message in samples[1].history_messages] == [
        "system",
        "user",
        "assistant",
    ]
    assert samples[0].sample_id != samples[1].sample_id


def test_generic_trace_mode_is_one_row(application) -> None:
    context = AdapterContext(application=application, row_mode="trace")
    samples = GenericOtelAdapter().normalize(load_trace("generic_multi_turn.json"), context=context)
    assert len(samples) == 1
    assert samples[0].turn_index is None


def test_runtime_kit_public_attributes_are_supported(application) -> None:
    configured = application.model_copy(
        update={"adapter_name": "agent-runtime-kit", "adapter_version": "1.0.0"}
    )
    context = AdapterContext(application=configured, row_mode="trace")
    adapter = AgentRuntimeKitAdapter()
    trace = load_trace("runtime_kit.json")
    assert adapter.can_handle(trace)
    result = adapter.normalize(trace, context=context)
    assert result[0].runtime.framework == "native"
    assert result[0].session_id == "thread-1"
