"""JSON-callable real slices; no observation wrapper or new capture protocol."""

from pathlib import Path

import evidence_loop_trial as E

UP = Path("F:/ChatGPT/agent-evaluation-harness/src/evaluation_harness")
SPECS = {
    "sequence": E.SPECS["sequence"],
    "mapping": {
        "origin": "models_clients/openai_compatible.py",
        "symbol": "_mapping",
        "header": "from __future__ import annotations\nfrom collections.abc import Mapping\nfrom typing import cast\n",
        "contract": "Keep mapping's existing Mapping type check, identity preservation, empty-map acceptance and non-mapping error. Require every top-level key to be a string, raising TypeError('Provider <label> keys must be strings') otherwise. Accept str subclasses and arbitrary Mapping implementations. Nested values/keys are not validated or modified. Preserve signature and all other code.",
        "reference": """def mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"Provider {label} must be an object")
    if any(not isinstance(key, str) for key in value):
        raise TypeError(f"Provider {label} keys must be strings")
    return cast(Mapping[str, object], value)
""",
        "public": """import pytest
from product.code import mapping

def test_bad_key_and_identity():
    with pytest.raises(TypeError, match="Provider event keys must be strings"):
        mapping({1: "v"}, "event")
    value = {"x": False}
    assert mapping(value, "event") is value
    empty = {}
    assert mapping(empty, "event") is empty

def test_nonmapping():
    with pytest.raises(TypeError, match="Provider event must be an object"):
        mapping([], "event")
""",
        "private": """from types import MappingProxyType
import pytest
from product.code import mapping

def test_mapping_types_and_nested_values():
    value = MappingProxyType({"x": {1: object()}})
    assert mapping(value, "delta") is value
    class Key(str):
        pass
    data = {Key("x"): None}
    assert mapping(data, "delta") is data

@pytest.mark.parametrize("key", [False, None, (1,)])
def test_other_nonstring_keys(key):
    with pytest.raises(TypeError, match="Provider delta keys must be strings"):
        mapping({key: 0}, "delta")
""",
    },
    "parse": {
        "origin": str(UP / "adapters/common.py"),
        "symbol": "parse_message",
        "header": "from __future__ import annotations\nfrom typing import Any\nfrom product.dependencies import AdapterError, CanonicalMessage, ContentPart, TextPart, ToolCallPart, ToolResultPart, stable_message_id\n",
        "dependency_source": str(UP / "canonical/models.py"),
        "contract": "For list content in parse_message, a text part (explicit type=text or omitted type) must have a nonempty string text. Missing, empty or non-string text raises real AdapterError(reason='invalid_content'); do not stringify it or leak Pydantic ValidationError for these cases. Preserve valid string-content and list-text parsing, exact whitespace text, all other part types/values, roles, IDs, name/tool_call_id, input immutability, error-role precedence and signature. Do not change imported dependencies or helper.",
        "reference": None,
        "public": """import pytest
from product.code import parse_message
from product.dependencies import AdapterError

@pytest.mark.parametrize("text", [None, False, 0, ""])
def test_reject_nontext(text):
    with pytest.raises(AdapterError) as exc:
        parse_message("t", 0, {"role": "assistant", "content": [{"type": "text", "text": text}]})
    assert exc.value.reason == "invalid_content"

def test_valid():
    out = parse_message("t", 0, {"id": "m", "role": "assistant", "content": [{"text": "雪"}]})
    assert out.message_id == "m" and out.content[0].text == "雪"
""",
        "private": """import copy
import pytest
from product.code import parse_message
from product.dependencies import AdapterError, stable_message_id

def test_missing_and_nonmutation():
    data = {"role": "assistant", "content": [{"type": "text"}]}
    before = copy.deepcopy(data)
    with pytest.raises(AdapterError) as exc:
        parse_message("t", 0, data)
    assert exc.value.reason == "invalid_content" and data == before

def test_whitespace_and_falsy_tool_result():
    data = {"id": 0, "role": "assistant", "content": [{"text": " "}, {"type": "tool_result", "call_id": "c", "result": False}]}
    before = copy.deepcopy(data)
    out = parse_message("t", 0, data)
    assert out.message_id == stable_message_id("t", 0, data) and out.content[0].text == " "
    assert out.content[1].result is False and data == before

def test_bad_role_precedes_bad_content():
    with pytest.raises(AdapterError) as exc:
        parse_message("t", 0, {"role": "bad", "content": [{"text": None}]})
    assert exc.value.reason == "invalid_message_role"
""",
        "cases": [
            {
                "args": [
                    "t",
                    0,
                    {"id": "m", "role": "assistant", "content": [{"text": "雪"}]},
                ],
                "kwargs": {},
            }
        ],
    },
}
