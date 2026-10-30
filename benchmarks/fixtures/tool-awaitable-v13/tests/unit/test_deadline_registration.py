"""Observable timeout registrations must not multiply for a sync factory."""

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
async def test_sync_factory_uses_one_registered_execution_deadline(monkeypatch):
    expected = Path(
        os.environ.get(
            "LW_DEADLINE_CODE_ROOT", str(Path(__file__).resolve().parents[2])
        )
    ).resolve()
    assert Path(registry_module.__file__).resolve().is_relative_to(expected)
    loop = asyncio.get_running_loop()
    call_at = loop.call_at
    deadlines = []
    calls = []

    def observe(when, callback, *args, context=None):
        # CPython wait_for uses its public Timeout context for nonzero deadlines.
        # Ignore unrelated timers; observe actual timer registration, not source AST.
        owner = getattr(callback, "__self__", None)
        if isinstance(owner, asyncio.Timeout):
            deadlines.append(owner)
        return call_at(when, callback, *args, context=context)

    monkeypatch.setattr(loop, "call_at", observe)

    def handler(value):
        calls.append(value)

        async def finish():
            return {"value": value}

        return finish()

    registry = ToolRegistry()
    registry.register(
        name="one-deadline",
        description="One deadline",
        input_model=Input,
        handler=handler,
        timeout_seconds=2.0,
    )
    result = await registry.invoke("one-deadline", {"value": 7}, tool_call_id="one")
    assert result.output == {"value": 7}
    assert calls == [7]
    assert len(deadlines) == 1, (
        "factory completion registered a separate execution timeout"
    )
