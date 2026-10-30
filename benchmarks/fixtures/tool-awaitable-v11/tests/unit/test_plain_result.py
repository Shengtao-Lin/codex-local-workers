"""Existing plain synchronous JSON output must not be mistaken for an awaitable."""

import inspect
import json

import pytest
from agent_runtime.tools.registry import ToolRegistry
from pydantic import BaseModel


class Input(BaseModel):
    value: int


@pytest.mark.asyncio
async def test_sync_json_mapping_with_disabled_await_is_a_plain_result():
    class PlainMapping(dict):
        __await__ = None

    final = PlainMapping(value=7)
    assert not inspect.isawaitable(final)
    assert json.loads(json.dumps(final)) == {"value": 7}
    calls = []

    def handler(value):
        calls.append(value)
        return final

    registry = ToolRegistry()
    registry.register(
        name="plain", description="Plain mapping", input_model=Input, handler=handler
    )
    result = await registry.invoke("plain", {"value": 7}, tool_call_id="plain")
    assert result.output is final
    assert calls == [7]
