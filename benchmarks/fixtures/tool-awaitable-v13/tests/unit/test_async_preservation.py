"""Protect existing direct-async return semantics, independently of new factories."""

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
async def test_direct_async_final_value_is_not_awaited_a_second_time():
    assert REGISTRY_SOURCE.is_relative_to(CODE_ROOT)
    future = asyncio.get_running_loop().create_future()
    future.set_result(42)
    calls = []

    async def handler(value):
        calls.append(value)
        return future

    registry = ToolRegistry()
    registry.register(
        name="direct",
        description="Existing async result",
        input_model=Input,
        handler=handler,
    )
    result = await registry.invoke("direct", {"value": 7}, tool_call_id="direct")
    assert calls == [7]
    assert result.output is future
