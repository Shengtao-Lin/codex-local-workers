"""Primary-only plain synchronous result compatibility, not a supplied solution."""

import inspect
import json
import os
from pathlib import Path

import pytest
from agent_runtime.tools import registry as registry_module
from agent_runtime.tools.registry import ToolRegistry
from pydantic import BaseModel


class Input(BaseModel):
    value: int


@pytest.mark.asyncio
async def test_sync_json_mapping_with_disabled_await_preserves_plain_result():
    expected = Path(os.environ["LW_COMPAT_CODE_ROOT"]).resolve()
    assert Path(registry_module.__file__).resolve().is_relative_to(expected)

    class PlainMapping(dict):
        __await__ = None

    final = PlainMapping(value=7)
    assert json.loads(json.dumps(final)) == {"value": 7}
    assert not inspect.isawaitable(final)
    calls = []

    def handler(value):
        calls.append(value)
        return final

    registry = ToolRegistry()
    registry.register(
        name="plain",
        description="Existing sync mapping",
        input_model=Input,
        handler=handler,
    )
    result = await registry.invoke("plain", {"value": 7}, tool_call_id="plain")
    assert result.output is final
    assert calls == [7]
