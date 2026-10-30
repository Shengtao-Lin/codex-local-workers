"""Existing plain-sync caller context must survive the off-thread invocation."""

import contextvars
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
@pytest.mark.parametrize("marker_value", ["request-alpha", "request-beta"])
async def test_plain_sync_preserves_callers_context(marker_value):
    assert REGISTRY_SOURCE.is_relative_to(CODE_ROOT)
    marker = contextvars.ContextVar("request_marker", default="missing")
    token = marker.set(marker_value)

    def handler(value):
        observed = marker.get()
        marker.set("handler-local-change")
        return (observed, value)

    registry = ToolRegistry()
    registry.register(
        name="context",
        description="Existing sync context",
        input_model=Input,
        handler=handler,
    )
    try:
        result = await registry.invoke("context", {"value": 7}, tool_call_id="context")
        assert result.output == (marker_value, 7)
        assert marker.get() == marker_value
    finally:
        marker.reset(token)
