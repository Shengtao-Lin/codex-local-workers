"""Shared deterministic parsing used by the built-in adapters."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, cast

from evaluation_harness.adapters.base import AdapterContext, AdapterError
from evaluation_harness.canonical.fingerprint import make_sample_id
from evaluation_harness.canonical.models import (
    CanonicalMessage,
    CanonicalSample,
    CanonicalToolCall,
    ContentPart,
    RuntimeMetadata,
    TextPart,
    ToolCallPart,
    ToolResultPart,
)
from evaluation_harness.trace_sources.base import SourceTrace


def mapping_raw(trace: SourceTrace) -> dict[str, Any]:
    raw = trace.raw
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AdapterError("invalid_json", "trace payload is not valid JSON") from exc
    if not isinstance(raw, dict):
        raise AdapterError("unsupported_shape", "trace payload must be an object")
    return cast(dict[str, Any], raw)


def stable_message_id(source_trace_id: str, index: int, message: dict[str, Any]) -> str:
    supplied = message.get("id") or message.get("message_id")
    if supplied:
        return str(supplied)
    digest = hashlib.sha256(
        json.dumps(message, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()[:16]
    return f"msg_{source_trace_id}_{index}_{digest}"


def parse_message(source_trace_id: str, index: int, value: dict[str, Any]) -> CanonicalMessage:
    role = value.get("role")
    if role not in {"system", "user", "assistant", "tool"}:
        raise AdapterError("invalid_message_role", f"message {index} has an unsupported role")
    raw_content = value.get("content")
    if isinstance(raw_content, str):
        parts: list[ContentPart] = [TextPart(text=raw_content)]
    elif isinstance(raw_content, list):
        parts = []
        for part in raw_content:
            if not isinstance(part, dict):
                raise AdapterError("invalid_content", f"message {index} content is invalid")
            kind = part.get("type", "text")
            if kind == "text":
                parts.append(TextPart(text=str(part.get("text", ""))))
            elif kind == "tool_call":
                call = part.get("tool_call", part)
                parts.append(
                    ToolCallPart(
                        call_id=str(call.get("id") or call.get("call_id")),
                        name=str(call.get("name")),
                        arguments=dict(call.get("arguments") or {}),
                    )
                )
            elif kind == "tool_result":
                parts.append(
                    ToolResultPart(
                        call_id=str(part.get("tool_call_id") or part.get("call_id")),
                        result=part.get("result"),
                    )
                )
            else:
                raise AdapterError("invalid_content", f"unsupported content type {kind}")
    else:
        raise AdapterError("invalid_content", f"message {index} must have content")
    return CanonicalMessage(
        message_id=stable_message_id(source_trace_id, index, value),
        role=role,
        content=parts,
        name=value.get("name"),
        tool_call_id=value.get("tool_call_id"),
    )


def build_samples(
    trace: SourceTrace,
    *,
    context: AdapterContext,
    adapter_name: str,
    adapter_version: str,
    messages: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> list[CanonicalSample]:
    parsed = [
        parse_message(trace.source_trace_id, index, item) for index, item in enumerate(messages)
    ]
    if not any(message.role == "user" for message in parsed):
        raise AdapterError("missing_input", "trace has no user message")
    if not any(message.role == "assistant" for message in parsed):
        raise AdapterError("missing_output", "trace has no assistant message")
    runtime = RuntimeMetadata(
        framework=metadata.get("framework"),
        agent_id=metadata.get("agent_id"),
        agent_version=metadata.get("agent_version"),
        model=metadata.get("model"),
        provider=metadata.get("provider"),
        latency_ms=metadata.get("latency_ms"),
        input_tokens=metadata.get("input_tokens"),
        output_tokens=metadata.get("output_tokens"),
        status=metadata.get("status"),
        trace_id=trace.source_trace_id,
        span_ids=list(metadata.get("span_ids") or []),
    )
    tools = collect_tools(parsed)
    event_time = _datetime(metadata.get("event_time"), trace.observed_at)
    if context.row_mode == "trace":
        last_assistant = max(i for i, message in enumerate(parsed) if message.role == "assistant")
        first_input = next(i for i, message in enumerate(parsed) if message.role == "user")
        return [
            _sample(
                trace,
                context=context,
                adapter_name=adapter_name,
                adapter_version=adapter_version,
                event_time=event_time,
                input_messages=[parsed[first_input]],
                output_messages=[parsed[last_assistant]],
                history_messages=parsed[:first_input],
                tool_calls=tools,
                runtime=runtime,
                metadata=metadata,
                turn_index=None,
            )
        ]

    samples: list[CanonicalSample] = []
    turn = 0
    cursor = 0
    while cursor < len(parsed):
        try:
            user_index = next(i for i in range(cursor, len(parsed)) if parsed[i].role == "user")
            assistant_index = next(
                i for i in range(user_index + 1, len(parsed)) if parsed[i].role == "assistant"
            )
        except StopIteration:
            break
        turn_messages = parsed[user_index + 1 : assistant_index]
        samples.append(
            _sample(
                trace,
                context=context,
                adapter_name=adapter_name,
                adapter_version=adapter_version,
                event_time=event_time,
                input_messages=[parsed[user_index]],
                output_messages=[parsed[assistant_index]],
                history_messages=parsed[:user_index],
                tool_calls=collect_tools([*turn_messages, parsed[assistant_index]]),
                runtime=runtime,
                metadata=metadata,
                turn_index=turn,
            )
        )
        turn += 1
        cursor = assistant_index + 1
    if not samples:
        raise AdapterError(
            "ambiguous_turns", "reliable user/assistant turn boundaries were not found"
        )
    return samples


def collect_tools(messages: list[CanonicalMessage]) -> list[CanonicalToolCall]:
    calls: dict[str, CanonicalToolCall] = {}
    for message in messages:
        for part in message.content:
            if isinstance(part, ToolCallPart):
                calls[part.call_id] = CanonicalToolCall(
                    call_id=part.call_id,
                    name=part.name,
                    arguments=part.arguments,
                    status="requested",
                )
            elif isinstance(part, ToolResultPart):
                existing = calls.get(part.call_id)
                if existing:
                    calls[part.call_id] = existing.model_copy(
                        update={"result": part.result, "status": "succeeded"}
                    )
    return list(calls.values())


def _sample(
    trace: SourceTrace,
    *,
    context: AdapterContext,
    adapter_name: str,
    adapter_version: str,
    event_time: datetime,
    input_messages: list[CanonicalMessage],
    output_messages: list[CanonicalMessage],
    history_messages: list[CanonicalMessage],
    tool_calls: list[CanonicalToolCall],
    runtime: RuntimeMetadata,
    metadata: dict[str, Any],
    turn_index: int | None,
) -> CanonicalSample:
    app = context.application
    sample_id = make_sample_id(
        workspace_id=app.workspace_id,
        application_id=app.application_id,
        environment=app.environment,
        source_trace_id=trace.source_trace_id,
        source_revision=trace.source_revision,
        row_mode=context.row_mode,
        turn_index=turn_index,
        adapter_name=adapter_name,
        adapter_version=adapter_version,
    )
    allowed_metadata = {
        key: value
        for key, value in metadata.items()
        if key not in {"messages", "prompt", "output", "authorization"}
    }
    return CanonicalSample(
        sample_id=sample_id,
        workspace_id=app.workspace_id,
        application_id=app.application_id,
        environment=app.environment,
        source_trace_id=trace.source_trace_id,
        source_revision=trace.source_revision,
        session_id=metadata.get("session_id"),
        turn_index=turn_index,
        event_time=event_time,
        input_messages=input_messages,
        output_messages=output_messages,
        history_messages=history_messages,
        tool_calls=tool_calls,
        runtime=runtime,
        tags=dict(metadata.get("tags") or {}),
        source_metadata=allowed_metadata,
    )


def _datetime(value: Any, default: datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return default
