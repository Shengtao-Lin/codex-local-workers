"""Two larger behavior units from the frozen full sibling-project snapshot."""

import project_caller_trial as J

TARGET = "src/evaluation_harness/adapters/common.py"
RUNTIME_PREFIX = """
import copy
import pytest
from pydantic import ValidationError
from evaluation_harness.adapters.base import AdapterContext, AdapterError
from evaluation_harness.adapters.generic_otel import GenericOtelAdapter
from evaluation_harness.canonical.models import CanonicalSample, RuntimeMetadata
from tests.conftest import load_trace

def normalize(application, mode, metadata):
    trace = load_trace("generic_multi_turn.json")
    trace.raw["metadata"] = metadata
    return trace, GenericOtelAdapter().normalize(trace, context=AdapterContext(application=application, row_mode=mode))
"""
RUNTIME_PUBLIC = """
@pytest.mark.parametrize("mode", ["trace", "turn"])
def test_new_runtime_field_reaches_canonical_roundtrip(application, mode):
    metadata = {"agent_version": "new-v2", "trace_id": "untrusted-shadow", "span_ids": ["s1"], "unknown_runtime_key": "ignored"}
    before = copy.deepcopy(metadata)
    trace, samples = normalize(application, mode, metadata)
    assert len(samples) == (1 if mode == "trace" else 2)
    for sample in samples:
        restored = CanonicalSample.model_validate_json(sample.model_dump_json())
        assert restored.runtime.agent_version == "new-v2"
        assert restored.runtime.trace_id == trace.source_trace_id
        assert restored.runtime.span_ids == ["s1"]
    assert metadata == before

def test_runtime_defaults_preserved(application):
    trace, samples = normalize(application, "turn", {})
    assert samples[0].runtime == RuntimeMetadata(trace_id=trace.source_trace_id, span_ids=[])
"""
RUNTIME_PRIVATE = """
@pytest.mark.parametrize("mode", ["trace", "turn"])
def test_every_existing_schema_field_and_object_preservation(application, mode):
    metadata = {"framework":"f", "agent_id":"a", "agent_version":"a2", "model":"m", "model_version":"m2", "provider":"p", "latency_ms":0, "input_tokens":0, "output_tokens":3, "estimated_cost_usd":0.25, "status":"ok", "trace_id":"shadow", "span_ids":["s1","s2"], "not_a_runtime_field":True}
    original = copy.deepcopy(metadata)
    trace, samples = normalize(application, mode, metadata)
    expected = RuntimeMetadata(framework="f", agent_id="a", agent_version="a2", model="m", model_version="m2", provider="p", latency_ms=0, input_tokens=0, output_tokens=3, estimated_cost_usd=0.25, status="ok", trace_id=trace.source_trace_id, span_ids=["s1","s2"])
    assert set(expected.model_fields_set) == set(RuntimeMetadata.model_fields)
    for sample in samples:
        assert sample.runtime == expected
        assert sample.runtime.span_ids is not metadata["span_ids"]
    assert metadata == original
    assert samples[0].input_messages[0].role == "user"
    assert samples[-1].output_messages[0].role == "assistant"
    if mode == "turn":
        assert samples[1].history_messages and samples[1].turn_index == 1

def test_explicit_null_and_existing_validation(application):
    _, samples = normalize(application, "trace", {"agent_version":None, "model_version":None, "estimated_cost_usd":None})
    assert samples[0].runtime.model_version is None
    with pytest.raises(ValidationError):
        normalize(application, "trace", {"estimated_cost_usd":-1})
    with pytest.raises(ValidationError):
        normalize(application, "trace", {"model_version":{}})

def test_message_error_precedes_runtime_error(application):
    trace = load_trace("generic_multi_turn.json")
    trace.raw = {"messages":[{"role":"bad","content":"x"}], "metadata":{"estimated_cost_usd":-1}}
    with pytest.raises(AdapterError) as exc:
        GenericOtelAdapter().normalize(trace, context=AdapterContext(application=application,row_mode="trace"))
    assert exc.value.reason == "invalid_message_role"
"""
TOOLS_PREFIX = """
import copy
import pytest
from evaluation_harness.adapters.base import AdapterContext
from evaluation_harness.adapters.common import collect_tools
from evaluation_harness.adapters.generic_otel import GenericOtelAdapter
from evaluation_harness.canonical.models import CanonicalMessage, ToolCallPart, ToolResultPart
from tests.conftest import load_trace

def message(parts):
    return CanonicalMessage(message_id="m", role="assistant", content=parts)

def call(key, name="first", **arguments):
    return ToolCallPart(call_id=key, name=name, arguments=arguments)

def result(key, value):
    return ToolResultPart(call_id=key, result=value)
"""
TOOLS_PUBLIC = """
def test_result_before_request_and_orphan():
    messages = [message([result("orphan", 9), result("a", None), call("a", n=0)])]
    before = copy.deepcopy(messages)
    out = collect_tools(messages)
    assert len(out) == 1 and out[0].call_id == "a"
    assert out[0].status == "succeeded" and out[0].result is None
    assert messages == before

def test_duplicate_request_keeps_first_metadata_and_completed_result():
    out = collect_tools([message([call("b", n=1), result("b", False), call("a"), call("b", name="later", n=2)])])
    assert [item.call_id for item in out] == ["b", "a"]
    assert out[0].name == "first" and out[0].arguments == {"n":1}
    assert out[0].status == "succeeded" and out[0].result is False
    assert out[1].status == "requested"
"""
TOOLS_PRIVATE = """
@pytest.mark.parametrize("value", [None, False, 0, "", [], {}])
def test_latest_result_across_request_positions_and_nonmutation(value):
    messages = [message([result("b", "old"), result("ghost", 9), call("a", n=1)]),
                message([result("b", value), call("b", n=2), result("a", value), call("a", name="duplicate", n=7)])]
    before = copy.deepcopy(messages)
    out = collect_tools(messages)
    assert [item.call_id for item in out] == ["a", "b"]
    assert [item.arguments for item in out] == [{"n":1}, {"n":2}]
    assert all(item.status == "succeeded" and item.result == value for item in out)
    assert messages == before
    assert collect_tools([]) == []

@pytest.mark.parametrize("mode", ["trace", "turn"])
def test_real_adapter_keeps_row_partition_and_tool_order(application, mode):
    trace = load_trace("generic_multi_turn.json")
    trace.raw = {"messages":[
        {"role":"user","content":"q1"},
        {"role":"assistant","content":[{"type":"tool_result","call_id":"a","result":None},{"type":"tool_call","tool_call":{"id":"a","name":"first","arguments":{"x":0}}}]},
        {"role":"user","content":"q2"},
        {"role":"assistant","content":[{"type":"tool_call","tool_call":{"id":"b","name":"first","arguments":{}}},{"type":"tool_result","call_id":"b","result":0},{"type":"tool_call","tool_call":{"id":"b","name":"later","arguments":{"wrong":1}}}]},
    ]}
    before = copy.deepcopy(trace.raw)
    samples = GenericOtelAdapter().normalize(trace, context=AdapterContext(application=application,row_mode=mode))
    assert len(samples) == (1 if mode == "trace" else 2)
    if mode == "trace":
        assert [item.call_id for item in samples[0].tool_calls] == ["a","b"]
    else:
        assert [item.call_id for item in samples[0].tool_calls] == ["a"]
        assert [item.call_id for item in samples[1].tool_calls] == ["b"]
    assert samples[0].tool_calls[0].result is None and samples[0].tool_calls[0].status == "succeeded"
    assert samples[-1].tool_calls[-1].name == "first" and samples[-1].tool_calls[-1].result == 0
    assert trace.raw == before
"""

RAW_PREFIX = """
import json
import pytest
from evaluation_harness.adapters.base import AdapterContext, AdapterError
from evaluation_harness.adapters.common import mapping_raw
from evaluation_harness.adapters.generic_otel import GenericOtelAdapter
from tests.conftest import load_trace

def source(value):
    trace = load_trace("generic_multi_turn.json")
    trace.raw = value
    return trace
"""
RAW_PUBLIC = """
@pytest.mark.parametrize("kind", [bytes, bytearray])
@pytest.mark.parametrize("mode", ["trace", "turn"])
def test_utf8_binary_reaches_real_adapter(application, kind, mode):
    payload = {"messages":[{"role":"user","content":"雪"},{"role":"assistant","content":"雨"}]}
    data = kind(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    trace = source(data)
    samples = GenericOtelAdapter().normalize(trace, context=AdapterContext(application=application,row_mode=mode))
    assert samples[0].input_messages[0].content[0].text == "雪"
    assert samples[0].output_messages[0].content[0].text == "雨"
    assert trace.raw is data

def test_dict_identity_and_error_category():
    value = {"messages":[]}
    assert mapping_raw(source(value)) is value
    with pytest.raises(AdapterError) as exc:
        mapping_raw(source(b"not-json"))
    assert exc.value.reason == "invalid_json"
"""
RAW_PRIVATE = """
@pytest.mark.parametrize("value", [b"\\xff", bytearray(b"\\xff"), '{"x":1}'.encode("utf-16"), b"\\xef\\xbb\\xbf{}"])
def test_only_strict_utf8_and_existing_text_json_rules(value):
    with pytest.raises(AdapterError) as exc:
        mapping_raw(source(value))
    assert exc.value.reason == "invalid_json"

@pytest.mark.parametrize("value", [b"[]", bytearray(b"null"), b'"text"', memoryview(b"{}"), None, []])
def test_nonobject_or_unsupported_kind_keeps_shape_reason(value):
    with pytest.raises(AdapterError) as exc:
        mapping_raw(source(value))
    assert exc.value.reason == "unsupported_shape"

def test_string_semantics_and_binary_buffer_unchanged():
    assert mapping_raw(source(' {"x":0,"a":[false,null,"雪"]} ')) == {"x":0,"a":[False,None,"雪"]}
    data = bytearray(b'{"x":0}')
    before = bytes(data)
    trace = source(data)
    assert mapping_raw(trace) == {"x":0}
    assert trace.raw is data and bytes(data) == before
"""


def tasks():
    original = J.function_source(J.TASKS.SNAPSHOT / TARGET, "build_samples")
    start = original.index("    runtime = RuntimeMetadata(")
    end = original.index("    tools = collect_tools(parsed)")
    runtime_reference = (
        original[:start]
        + """    runtime_values = {
        name: metadata[name]
        for name in RuntimeMetadata.model_fields
        if name in metadata and name not in {"trace_id", "span_ids"}
    }
    runtime_values["trace_id"] = trace.source_trace_id
    runtime_values["span_ids"] = list(metadata.get("span_ids") or [])
    runtime = RuntimeMetadata(**runtime_values)
"""
        + original[end:]
    )
    tools_reference = """def collect_tools(messages: list[CanonicalMessage]) -> list[CanonicalToolCall]:
    calls: dict[str, CanonicalToolCall] = {}
    results: dict[str, Any] = {}
    for message in messages:
        for part in message.content:
            if isinstance(part, ToolCallPart) and part.call_id not in calls:
                calls[part.call_id] = CanonicalToolCall(call_id=part.call_id, name=part.name, arguments=part.arguments, status="requested")
            elif isinstance(part, ToolResultPart):
                results[part.call_id] = part.result
    return [item.model_copy(update={"result":results[key],"status":"succeeded"}) if key in results else item for key,item in calls.items()]
"""
    raw_original = J.function_source(J.TASKS.SNAPSHOT / TARGET, "mapping_raw")
    raw_reference = raw_original.replace(
        "    raw = trace.raw\n",
        """    raw = trace.raw
    if isinstance(raw, (bytes, bytearray)):
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AdapterError("invalid_json", "trace payload must be valid UTF-8") from exc
""",
        1,
    )
    specs = {
        "runtime": {
            "symbol": "build_samples",
            "contract": "Forward every field currently declared by the protected canonical RuntimeMetadata schema when that field is provided in metadata; use that model's existing defaults and validation for absent/provided values, no coercion/sanitization shortcuts. Exceptions: trace_id always comes from trace.source_trace_id, never metadata; span_ids retains list(metadata.get('span_ids') or []) semantics and must not alias the metadata list. Unknown metadata keys are not runtime fields. Preserve parsing/error precedence, exact trace/turn row boundaries, IDs, event time, history, tool partition, all other sample fields and input immutability. No changes to callers, model, imports, signature or other functions. Locate schema details in approved source; no algorithm is prescribed.",
            "reference": runtime_reference,
            "public": J.TASKS.join_test_sources(RUNTIME_PREFIX, RUNTIME_PUBLIC),
            "private": J.TASKS.join_test_sources(RUNTIME_PREFIX, RUNTIME_PRIVATE),
            "cases": [],
        },
        "tools": {
            "symbol": "collect_tools",
            "contract": "Aggregate ToolCallPart/ToolResultPart events across the supplied ordered messages. Output one CanonicalToolCall per requested call_id in FIRST request occurrence order; keep the FIRST request's name/arguments. The chronologically last result for a requested ID wins whether before or after its request, including None/False/zero/empty values; status becomes succeeded. Duplicate requests never erase a result or replace first metadata/order. Requested IDs with no result keep requested/default result; result-only orphan IDs produce no output. Preserve exact values and input objects without mutation, and existing GenericOtelAdapter trace/turn tool partitioning. Do not filter by message role, sort IDs, change caller/model/imports/signature or any other function. Use actual model/caller evidence as needed, no new role or external execution.",
            "reference": tools_reference,
            "public": J.TASKS.join_test_sources(
                TOOLS_PREFIX.replace("import pytest\n", "")
                .replace(
                    "from evaluation_harness.adapters.base import AdapterContext\n", ""
                )
                .replace(
                    "from evaluation_harness.adapters.generic_otel import GenericOtelAdapter\n",
                    "",
                )
                .replace("from tests.conftest import load_trace\n", ""),
                TOOLS_PUBLIC,
            ),
            "private": J.TASKS.join_test_sources(
                TOOLS_PREFIX, "from tests.conftest import application\n", TOOLS_PRIVATE
            ),
            "family": "collect-tools-json-observation-v1",
            "cases": [
                {
                    "parts": [
                        {"type": "tool_result", "call_id": "a", "result": None},
                        {
                            "type": "tool_call",
                            "call_id": "a",
                            "name": "run",
                            "arguments": {"x": 0},
                        },
                    ]
                }
            ],
        },
        "raw": {
            "symbol": "mapping_raw",
            "contract": "Extend mapping_raw to accept bytes and bytearray containing strict UTF-8 text, then apply exactly the existing str JSON parsing/object requirement. Preserve dict object identity and all existing str behavior. Malformed UTF-8, malformed JSON or text BOM rejected by the existing str JSON rules must raise real AdapterError(reason='invalid_json'); JSON scalars/arrays/null and every other unsupported raw kind (including memoryview) retain unsupported_shape. Do not accept UTF-16/32 or auto-detect encodings. Preserve parsed values/Unicode/falsy data, SourceTrace and binary buffer unchanged, no input mutation. GenericOtelAdapter must normalize valid binary trace/turn inputs with existing IDs/parts/history. No caller/helper/import/signature/other function changes.",
            "reference": raw_reference,
            "public": J.TASKS.join_test_sources(RAW_PREFIX, RAW_PUBLIC),
            "private": J.TASKS.join_test_sources(RAW_PREFIX, RAW_PRIVATE),
            "family": "mapping-raw-utf8-v1",
            "cases": [
                {"text": '{"x":0,"label":"雪"}', "kind": "bytes"},
                {"text": "[]", "kind": "bytearray"},
            ],
        },
    }
    for spec in specs.values():
        spec.update(target=TARGET, module="evaluation_harness.adapters.common")
    # build_samples fixture is design-only: current installed capture families
    # cannot call its typed arguments. Do not manufacture meaningless probes.
    return {key: specs[key] for key in ("tools", "raw")}
