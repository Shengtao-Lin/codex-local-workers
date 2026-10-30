"""Primary regression for legal awaitables without a __await__ attribute."""

import asyncio
import inspect
import types
from pathlib import Path

import pytest
from pydantic import BaseModel

from agent_runtime.tools import registry as registry_module
from agent_runtime.tools.registry import ToolRegistry


class Input(BaseModel):
    value: int


@pytest.fixture
def verified_source_root():
    root = Path(__file__).resolve().parents[2]
    assert Path(registry_module.__file__).resolve().is_relative_to(root / "src")
    return root


@pytest.mark.asyncio
async def test_sync_factory_resolves_generator_based_coroutine_once(verified_source_root):
    del verified_source_root
    calls = []
    completions = []
    final = {"value": 7}

    @types.coroutine
    def completion():
        yield from asyncio.sleep(0).__await__()
        completions.append("completed")
        return final

    def handler(value):
        calls.append(value)
        returned = completion()
        assert inspect.isawaitable(returned)
        assert not hasattr(returned, "__await__")
        return returned

    registry = ToolRegistry()
    registry.register(
        name="generator",
        description="Generator coroutine",
        input_model=Input,
        handler=handler,
    )
    result = await registry.invoke("generator", {"value": 7}, tool_call_id="generator")
    assert result.output is final
    assert calls == [7]
    assert completions == ["completed"]
