"""Protected observable contracts for a frozen real ToolRegistry."""

import asyncio
import threading
import time
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import BaseModel

import agent_runtime
from agent_runtime.errors import ToolExecutionError, ToolTimeoutError
from agent_runtime.hooks import HookEvent, HookManager
from agent_runtime.models import RuntimeContext, ToolResult
from agent_runtime.tools import ToolRegistry


class Input(BaseModel):
    value: int


class Recorder:
    name = "recorder"

    def __init__(self, events):
        self.events = events

    async def handle(self, event: HookEvent) -> None:
        self.events.append(event.phase)
        if event.phase == "after_tool":
            assert event.tool_result is not None
            assert event.tool_result.output == {"answer": 7}


def test_import_is_frozen_copy():
    assert (
        Path(agent_runtime.__file__)
        .resolve()
        .is_relative_to(Path(__file__).resolve().parents[2] / "src")
    )


@pytest.mark.asyncio
async def test_factory_resolved_before_hook_and_json_roundtrip():
    events = []
    caller_thread = threading.get_ident()

    def factory(value):
        assert threading.get_ident() != caller_thread
        events.append("factory")

        async def answer():
            events.append("await")
            await asyncio.sleep(0)
            events.append("resolved")
            return {"answer": value}

        return answer()

    registry = ToolRegistry(hooks=HookManager([Recorder(events)]))
    registry.register(name="factory", description="Factory", input_model=Input, handler=factory)
    context = RuntimeContext(run_id=uuid4(), thread_id=uuid4())
    result = await registry.invoke("factory", {"value": 7}, tool_call_id="call", context=context)
    assert events == ["before_tool", "factory", "await", "resolved", "after_tool"]
    assert ToolResult.model_validate_json(result.model_dump_json()).output == {"answer": 7}


@pytest.mark.asyncio
async def test_sync_factory_returning_future_is_awaited_once():
    future = asyncio.get_running_loop().create_future()
    future.set_result(9)
    calls = []

    def factory(value):
        calls.append(value)
        return future

    registry = ToolRegistry()
    registry.register(name="future", description="Future", input_model=Input, handler=factory)
    result = await registry.invoke("future", {"value": 9}, tool_call_id="future-call")
    assert result.output == 9
    assert calls == [9]


@pytest.mark.asyncio
async def test_awaitable_failure_keeps_original_cause_and_no_after_hook():
    original = ValueError("deferred error")
    events = []

    def factory(value):
        events.append("factory")

        async def fail():
            raise original

        return fail()

    registry = ToolRegistry(hooks=HookManager([Recorder(events)]))
    registry.register(name="fail", description="Fail", input_model=Input, handler=factory)
    with pytest.raises(ToolExecutionError) as caught:
        await registry.invoke(
            "fail",
            {"value": 1},
            tool_call_id="fail-call",
            context=RuntimeContext(run_id=uuid4(), thread_id=uuid4()),
        )
    assert caught.value.__cause__ is original
    assert events == ["before_tool", "factory"]


@pytest.mark.asyncio
async def test_cancelled_awaitable_propagates_without_success_hook():
    events = []
    original = asyncio.CancelledError("cancelled")

    def factory(value):
        events.append("factory")

        async def cancel():
            raise original

        return cancel()

    registry = ToolRegistry(hooks=HookManager([Recorder(events)]))
    registry.register(name="cancel", description="Cancel", input_model=Input, handler=factory)
    with pytest.raises(asyncio.CancelledError):
        await registry.invoke(
            "cancel",
            {"value": 1},
            tool_call_id="cancel-call",
            context=RuntimeContext(run_id=uuid4(), thread_id=uuid4()),
        )
    assert events == ["before_tool", "factory"]


@pytest.mark.asyncio
async def test_factory_and_await_share_one_deadline():
    events = []

    def factory(value):
        events.append("factory")
        time.sleep(0.08)

        async def answer():
            try:
                events.append("await")
                await asyncio.sleep(0.08)
                return {"answer": value}
            finally:
                events.append("finalized")

        return answer()

    registry = ToolRegistry(hooks=HookManager([Recorder(events)]))
    registry.register(
        name="slow",
        description="Slow",
        input_model=Input,
        handler=factory,
        timeout_seconds=0.12,
    )
    with pytest.raises(ToolTimeoutError):
        await registry.invoke(
            "slow",
            {"value": 7},
            tool_call_id="slow-call",
            context=RuntimeContext(run_id=uuid4(), thread_id=uuid4()),
        )
    assert events == ["before_tool", "factory", "await", "finalized"]


@pytest.mark.asyncio
async def test_custom_awaitable_supported():
    calls = []

    class Answer:
        def __await__(self):
            calls.append("await")
            return asyncio.sleep(0, result=12).__await__()

    registry = ToolRegistry()
    registry.register(
        name="custom",
        description="Custom",
        input_model=Input,
        handler=lambda value: Answer(),
    )
    result = await registry.invoke("custom", {"value": 12}, tool_call_id="custom-call")
    assert result.output == 12
    assert calls == ["await"]
