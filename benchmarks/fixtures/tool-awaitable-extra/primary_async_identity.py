"""Primary-only generality probe; not supplied to the implementation workers."""

import asyncio
import os
from pathlib import Path

import pytest
from pydantic import BaseModel

from agent_runtime.tools import registry as registry_module
from agent_runtime.tools.registry import ToolRegistry


class Input(BaseModel):
    value: int


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["future", "custom", "coroutine"])
async def test_direct_async_preserves_every_final_awaitable_kind(kind):
    expected = Path(os.environ["LW_COMPAT_CODE_ROOT"]).resolve()
    assert Path(registry_module.__file__).resolve().is_relative_to(expected)
    consumed = []
    calls = []

    async def inner():
        consumed.append("awaited")
        return 42

    class Custom:
        def __await__(self):
            return inner().__await__()

    if kind == "future":
        final = asyncio.get_running_loop().create_future()
        final.set_result(42)
    elif kind == "custom":
        final = Custom()
    else:
        final = inner()

    async def handler(value):
        calls.append(value)
        return final

    registry = ToolRegistry()
    registry.register(
        name="direct",
        description="Existing behavior",
        input_model=Input,
        handler=handler,
    )
    try:
        result = await registry.invoke("direct", {"value": 7}, tool_call_id="direct")
        assert result.output is final
        assert calls == [7]
        assert consumed == []
    finally:
        if kind == "coroutine":
            final.close()
