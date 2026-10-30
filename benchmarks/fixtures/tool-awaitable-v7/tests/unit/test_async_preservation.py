"""Protect existing direct-async return semantics, independently of new factories."""

import asyncio
from pathlib import Path

import pytest
from agent_runtime.tools import registry as registry_module
from agent_runtime.tools.registry import ToolRegistry
from pydantic import BaseModel


class Input(BaseModel):
    value: int


@pytest.mark.asyncio
async def test_direct_async_final_value_is_not_awaited_a_second_time():
    root = Path(__file__).resolve().parents[2]
    assert Path(registry_module.__file__).resolve().is_relative_to(root / "src")
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
