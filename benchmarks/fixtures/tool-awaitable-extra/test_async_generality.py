"""Preserve existing async final objects without consuming them a second time."""

import asyncio
from pathlib import Path

import pytest
from pydantic import BaseModel

from agent_runtime.tools import registry as registry_module
from agent_runtime.tools.registry import ToolRegistry

CODE_ROOT = Path(__file__).resolve().parents[2] / "src"
REGISTRY_SOURCE = Path(registry_module.__file__).resolve()


class Input(BaseModel):
    value: int


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["future", "custom", "coroutine"])
async def test_async_final_object_preserved_without_consumption(kind):
    assert REGISTRY_SOURCE.is_relative_to(CODE_ROOT)
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
