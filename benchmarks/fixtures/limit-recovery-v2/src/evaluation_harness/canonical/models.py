"""Framework-neutral canonical sample schema v1.0."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_METADATA_KEYS = 64
MAX_METADATA_BYTES = 16_384


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TextPart(StrictModel):
    type: Literal["text"] = "text"
    text: str = Field(min_length=1, max_length=32_000)


class JsonPart(StrictModel):
    type: Literal["json"] = "json"
    value: Any


class ToolCallPart(StrictModel):
    type: Literal["tool_call"] = "tool_call"
    call_id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResultPart(StrictModel):
    type: Literal["tool_result"] = "tool_result"
    call_id: str
    result: Any = None


ContentPart = Annotated[
    TextPart | JsonPart | ToolCallPart | ToolResultPart, Field(discriminator="type")
]


def _empty_messages() -> list[CanonicalMessage]:
    return []


class CanonicalMessage(StrictModel):
    message_id: str
    role: Literal["system", "user", "assistant", "tool"]
    content: list[ContentPart] = Field(min_length=1, max_length=64)
    name: str | None = None
    tool_call_id: str | None = None


class CanonicalToolCall(StrictModel):
    call_id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: Any = None
    status: Literal["requested", "succeeded", "failed", "unknown"] = "unknown"
    error: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_ms: float | None = Field(default=None, ge=0)


class RetrievedItem(StrictModel):
    reference_id: str
    rank: int | None = Field(default=None, ge=0)
    score: float | None = None
    source_uri: str | None = None
    title: str | None = None
    content: str | None = Field(default=None, max_length=32_000)


class AgentStep(StrictModel):
    index: int = Field(ge=0)
    kind: str
    name: str | None = None
    status: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class RuntimeMetadata(StrictModel):
    framework: str | None = None
    agent_id: str | None = None
    agent_version: str | None = None
    model: str | None = None
    model_version: str | None = None
    provider: str | None = None
    latency_ms: float | None = Field(default=None, ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0)
    status: str | None = None
    trace_id: str | None = None
    span_ids: list[str] = Field(default_factory=list)


class Expectations(StrictModel):
    reference_output: str | None = None
    reference_facts: list[str] = Field(default_factory=list)
    expected_tools: list[str] = Field(default_factory=list)
    expected_behavior: str | None = None
    rubric: dict[str, Any] = Field(default_factory=dict)


class HumanLabel(StrictModel):
    label: str
    value: str | float | bool
    source: str
    revision: str | None = None


def _empty_tool_calls() -> list[CanonicalToolCall]:
    return []


def _empty_retrieval_context() -> list[RetrievedItem]:
    return []


def _empty_agent_steps() -> list[AgentStep]:
    return []


def _empty_labels() -> list[HumanLabel]:
    return []


class CanonicalSample(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    sample_id: str
    workspace_id: str = "default"
    application_id: str
    environment: str
    source_trace_id: str
    source_revision: str | None = None
    session_id: str | None = None
    turn_index: int | None = Field(default=None, ge=0)
    event_time: datetime
    input_messages: list[CanonicalMessage]
    output_messages: list[CanonicalMessage]
    history_messages: list[CanonicalMessage] = Field(default_factory=_empty_messages)
    tool_calls: list[CanonicalToolCall] = Field(default_factory=_empty_tool_calls)
    retrieval_context: list[RetrievedItem] = Field(default_factory=_empty_retrieval_context)
    agent_steps: list[AgentStep] = Field(default_factory=_empty_agent_steps)
    runtime: RuntimeMetadata = Field(default_factory=RuntimeMetadata)
    expectations: Expectations | None = None
    labels: list[HumanLabel] = Field(default_factory=_empty_labels)
    tags: dict[str, str] = Field(default_factory=dict)
    source_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("source_metadata")
    @classmethod
    def bounded_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(value) > MAX_METADATA_KEYS:
            raise ValueError(f"source_metadata cannot exceed {MAX_METADATA_KEYS} keys")
        try:
            encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
        except (TypeError, ValueError) as exc:
            raise ValueError("source_metadata must be JSON-compatible") from exc
        if len(encoded) > MAX_METADATA_BYTES:
            raise ValueError(f"source_metadata cannot exceed {MAX_METADATA_BYTES} bytes")
        return value
