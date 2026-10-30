"""Primary-owned public caller checks; never a Coder-writable implementation test."""

import asyncio
import json
import os
import threading
from collections.abc import Awaitable
from pathlib import Path
from uuid import uuid4

import pytest
from agent_runtime.adapters import NativeAgentInvoker
from agent_runtime.models import (
    InvocationInput,
    Message,
    RuntimeContext,
    TextContent,
    ToolCall,
    ToolCallContent,
    ToolResultContent,
)
from agent_runtime.models_clients import DeterministicModelClient, ModelResult
from agent_runtime.tools import registry as registry_module
from agent_runtime.tools.registry import ToolRegistry
from pydantic import BaseModel


class Input(BaseModel):
    value: int


@pytest.fixture
def verified_source_root() -> Path:
    root = Path(os.environ["LW_NATIVE_CODE_ROOT"]).resolve()
    assert Path(registry_module.__file__).resolve().is_relative_to(root / "src")
    return root


@pytest.mark.asyncio
@pytest.mark.parametrize("stream", [False, True])
async def test_factory_value_roundtrips_through_public_native_caller(
    verified_source_root: Path,
    stream: bool,
) -> None:
    del verified_source_root
    caller_thread = threading.get_ident()
    caller_loop = asyncio.get_running_loop()
    invoked = []
    completed = []
    final = {"value": 7}

    def factory(value: int) -> Awaitable[dict[str, int]]:
        invoked.append((value, threading.get_ident()))

        async def completion() -> dict[str, int]:
            completed.append((threading.get_ident(), asyncio.get_running_loop()))
            return final

        return completion()

    call = ToolCall(id="factory-1", name="factory", arguments={"value": 7})
    model = DeterministicModelClient(
        [
            ModelResult(
                message=Message(
                    role="assistant", content=[ToolCallContent(tool_call=call)]
                ),
                tool_calls=[call],
            ),
            ModelResult(
                message=Message(role="assistant", content=[TextContent(text="done")])
            ),
        ]
    )
    tools = ToolRegistry()
    tools.register(
        name="factory",
        description="Synthetic factory",
        input_model=Input,
        handler=factory,
    )
    invoker = NativeAgentInvoker(
        agent_id="factory", version="1", model_client=model, tools=tools
    )
    request = InvocationInput(
        context=RuntimeContext(run_id=uuid4(), thread_id=uuid4()),
        messages=[Message(role="user", content=[TextContent(text="run")])],
    )
    if stream:
        events = [event async for event in invoker.stream(request)]
        assert [event.type for event in events] == [
            "tool_result",
            "text_delta",
            "completed",
        ]
        output = events[-1].output
    else:
        output = await invoker.invoke(request)
    assert len(invoked) == 1
    assert invoked[0][0] == 7 and invoked[0][1] != caller_thread
    assert completed == [(caller_thread, caller_loop)]
    assert output.tool_results[0].output is final
    assert len(model.calls) == 2
    message = model.calls[1][-1]
    assert message.role == "tool"
    content = message.content[0]
    assert isinstance(content, ToolResultContent)
    assert content.result is final
    assert json.loads(message.model_dump_json())["content"][0]["result"] == final
