"""Primary-only original context propagation control, outside worker read scope."""

import contextvars
import os
from pathlib import Path

import pytest
from pydantic import BaseModel

from agent_runtime.tools import registry as registry_module
from agent_runtime.tools.registry import ToolRegistry

EXPECTED_ROOT = Path(os.environ["LW_COMPAT_CODE_ROOT"]).resolve()
REGISTRY_SOURCE = Path(registry_module.__file__).resolve()


class Input(BaseModel):
    value: int


@pytest.mark.asyncio
async def test_plain_sync_preserves_callers_context_variable():
    assert REGISTRY_SOURCE.is_relative_to(EXPECTED_ROOT)
    marker = contextvars.ContextVar("request_marker", default="missing")
    token = marker.set("caller-request")

    def handler(value):
        return (marker.get(), value)

    registry = ToolRegistry()
    registry.register(
        name="context",
        description="Existing sync context",
        input_model=Input,
        handler=handler,
    )
    try:
        result = await registry.invoke("context", {"value": 7}, tool_call_id="context")
        assert result.output == ("caller-request", 7)
        assert marker.get() == "caller-request"
    finally:
        marker.reset(token)
