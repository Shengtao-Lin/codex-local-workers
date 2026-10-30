"""Two new local behavior changes from exact read-only sibling functions."""

import argparse
from pathlib import Path

import prepared_task_matrix as M

S, P, T = M.S, M.P, M.T
BATCH = P.I.BASE / "stream-slice-transfer-20261022-1"
ORDER = ["frame-1", "text-1", "text-2", "frame-2"]
UPSTREAM = Path("F:/ChatGPT/agent-runtime-kit/src/agent_runtime")


def tasks():
    source = UPSTREAM / "adapters/framework_streaming.py"
    text_start = T.extract(source, "_text")
    return {
        "frame": {
            "origin": UPSTREAM / "service/app.py",
            "symbol": "_sse",
            "header": '"""Isolated event frame encoder, copied from service/app.py."""\n',
            "contract": "Extend _sse(event: str, data: str) -> str for multiline data. Reject event containing CR or LF with ValueError; otherwise preserve event exactly, including empty/whitespace/Unicode values. Normalize CRLF and lone CR in data to LF, emit one 'data: ' field for every LF-delimited segment including empty and trailing segments, preceded by exactly 'event: {event}\\n' and followed by one blank-line terminator. Empty data still emits one empty data field. Preserve every other data character: no trimming, JSON encoding, escaping, or splitting on other Unicode/control separators. Legacy single-line CR/LF-free output stays byte-for-byte the same. Keep signature/imports, no external effects. Other functions, tests and configuration protected.",
            "start": T.extract(UPSTREAM / "service/app.py", "_sse"),
            "reference": """def _sse(event: str, data: str) -> str:
    if "\\r" in event or "\\n" in event:
        raise ValueError("event contains a line break")
    normalized = data.replace("\\r\\n", "\\n").replace("\\r", "\\n")
    return f"event: {event}\\n" + "".join(f"data: {part}\\n" for part in normalized.split("\\n")) + "\\n"
""",
            "public": """import pytest
from product.code import _sse

@pytest.mark.parametrize(("event", "data", "expected"), [
    ("chunk", "hello", "event: chunk\\ndata: hello\\n\\n"),
    ("", "", "event: \\ndata: \\n\\n"),
    ("chunk", "a\\nb\\n", "event: chunk\\ndata: a\\ndata: b\\ndata: \\n\\n"),
    ("chunk", "a\\r\\nb\\rc", "event: chunk\\ndata: a\\ndata: b\\ndata: c\\n\\n"),
])
def test_frame(event, data, expected):
    assert _sse(event, data) == expected

@pytest.mark.parametrize("event", ["chunk\\nother", "chunk\\rother"])
def test_event_line_break_rejected(event):
    with pytest.raises(ValueError):
        _sse(event, "content")
""",
            "private": """import pytest
from product.code import _sse

@pytest.mark.parametrize("event", ["", " ", "雪", "a:b", "tab\\tname"])
def test_payload_roundtrip_without_extra_fields(event):
    for payload in ["", "\\n", "\\r\\n", "a\\n\\nb\\n", "data: x\\nevent: injected", " \\t雪 ", "x\\v\\f\\x85\\u2028\\u2029z", "\\x00"]:
        output = _sse(event, payload)
        assert output.startswith("event: " + event + "\\n") and output.endswith("\\n\\n")
        fields = output.split("\\n")[1:-2]
        assert fields and all(field.startswith("data: ") for field in fields)
        restored = "\\n".join(field[6:] for field in fields)
        assert restored == payload.replace("\\r\\n", "\\n").replace("\\r", "\\n")

@pytest.mark.parametrize("event", ["\\n", "\\r", "ok\\r\\nevent: bad", "\\r\\n"])
def test_every_event_line_break_rejected(event):
    with pytest.raises(ValueError):
        _sse(event, "")
""",
            "cases": [
                {"args": ["chunk", "a\nb\n"], "kwargs": {}},
                {"args": ["bad\nevent", "x"], "kwargs": {}},
            ],
            "scenarios": [
                {
                    "id": "normal",
                    "text": "Legacy single-line and empty frames remain exact",
                },
                {
                    "id": "boundary",
                    "text": "Normalize CR/CRLF only, preserve trailing empty segments and non-LF separators",
                },
                {
                    "id": "error",
                    "text": "Event CR/LF is rejected before producing a frame",
                },
            ],
        },
        "text": {
            "origin": source,
            "symbol": "_text",
            "header": "from typing import cast\n",
            "contract": "Extend _text(value: object) -> str so a tuple of content blocks is accepted exactly like a list, preserving order and concatenating string blocks and dict blocks with type=='text' whose text is a string. Empty tuple yields ''. All existing string and list behavior, error types/messages and nonmutation remain unchanged. Any other outer type (including dict, bytes, set, generator or arbitrary iterable) remains ValueError with the existing Unsupported streamed content message. An invalid list/tuple member still raises the existing error: a dict declaring type text but missing/non-string text raises Invalid streamed text block, every other invalid block raises Unsupported streamed content. Do not stringify unknown values, recursively flatten, suppress invalid blocks or coerce the input. Preserve signature/imports and every caller-owned object; other functions/tests/configuration protected.",
            "start": text_start,
            "reference": text_start.replace(
                "not isinstance(value, list)", "not isinstance(value, (list, tuple))"
            ).replace(
                "cast(list[object], value)",
                "cast(list[object] | tuple[object, ...], value)",
            ),
            "public": """import pytest
from product.code import _text

@pytest.mark.parametrize(("value", "expected"), [((), ""), (("a", {"type": "text", "text": "雪"}, ""), "a雪"), (["a", {"type": "text", "text": "b"}], "ab"), ("keep", "keep")])
def test_text(value, expected):
    assert _text(value) == expected

@pytest.mark.parametrize("value", [({"type": "text", "text": 1},), ({"type": "text"},)])
def test_invalid_text(value):
    with pytest.raises(ValueError, match="^Invalid streamed text block$"):
        _text(value)

def test_invalid_member():
    with pytest.raises(ValueError, match="^Unsupported streamed content; provide an explicit stream mapper$"):
        _text(("ok", 3))
""",
            "private": """import copy
import pytest
from product.code import _text

@pytest.mark.parametrize("outer", [None, 1, False, {}, b"x", {"x"}, range(0)])
def test_nonsequence_stays_invalid(outer):
    with pytest.raises(ValueError, match="^Unsupported streamed content; provide an explicit stream mapper$"):
        _text(outer)

def test_iterator_not_consumed():
    iterator = iter(["x"])
    with pytest.raises(ValueError):
        _text(iterator)
    assert next(iterator) == "x"

@pytest.mark.parametrize("container", [list, tuple])
def test_exact_legacy_and_identity(container):
    block = {"type": "text", "text": " \\n雪", "extra": {"a": [1]}}
    before = copy.deepcopy(block)
    value = container(["prefix", block, ""])
    assert _text(value) == "prefix \\n雪"
    assert value[1] is block and block == before
    for bad in [None, {}, [], (), {"type": "image", "text": "hidden"}, {"type": "text", "text": False}]:
        expected = "Invalid streamed text block" if isinstance(bad, dict) and bad.get("type") == "text" else "Unsupported streamed content; provide an explicit stream mapper"
        with pytest.raises(ValueError) as caught:
            _text(container(["ok", bad]))
        assert str(caught.value) == expected
""",
            "cases": [
                {"args": [["a", {"type": "text", "text": "b"}]], "kwargs": {}},
                {"args": [[{"type": "text", "text": 1}]], "kwargs": {}},
            ],
            "scenarios": [
                {
                    "id": "normal",
                    "text": "Tuple content works like list; original strings/lists unchanged",
                },
                {
                    "id": "boundary",
                    "text": "Empty tuple, exact characters, order and original object preservation",
                },
                {
                    "id": "error",
                    "text": "Invalid blocks/outer types keep their prior precise errors without consumption/coercion",
                },
            ],
        },
    }


def prepare(used):
    assert (
        S.read(P.I.BASE / "flat-diagnostics-20261022-1/decision.json")["status"]
        == "PASS_DIAGNOSTIC_CALLBACK_PARITY"
    )
    specs = tasks()
    materials, origins = {}, {}
    for topic, spec in specs.items():
        spec["risk_rationale"] = (
            "Public serialization/content compatibility; exact line boundaries, error propagation and unchanged inputs are atomic high-risk invariants. Isolated experiment does not qualify production use."
        )
        origin = spec["origin"]
        digest = S.sha(origin)
        T.write(BATCH / "origins" / f"{topic}.py", origin.read_text(encoding="utf-8"))
        assert S.sha(origin) == digest
        origins[topic] = {
            "path": str(origin),
            "sha256": digest,
            "symbol": spec["symbol"],
        }
        materials[topic] = M.template(BATCH, topic, spec)
    rows = {
        cell: M.cell(
            BATCH,
            cell,
            cell.split("-")[0],
            specs[cell.split("-")[0]],
            materials[cell.split("-")[0]],
            Path(__file__),
        )
        for cell in ORDER
    }
    S.save(BATCH / "cells.json", rows)
    S.save(
        BATCH / "registration.json",
        {
            "feature_id": "new-stream-behavior-transfer",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "order": ORDER,
            "registered": 4,
            "weekly_stop": None,
            "weekly_used_start": used,
            "batch_seconds": 5400,
            "candidate": "Installed bounded-v1 flat-v1 with restored existing static diagnostic callback; frozen editor, checks, fresh Muse and Primary final review.",
            "origins": origins,
            "exposure": "Two newly specified behavior extensions on exact copied sibling functions; first attempts new task exposure, second repeats. Not upstream confirmed bugs or deployment tests; Primary has authored detailed contracts/public/private tests.",
            "gate": "4/4 independent complete-chain accepts and each task2/2, zero assistance/safety drift; otherwise transfer HOLD while retaining every failure.",
            "continue_rule": "Ordinary failure HOLD, finish fixed diagnostic order. Infra/safety/protected drift/fixed deadline stops. No extra attempts, Primary fix hints or reference/private-test leakage.",
            "budget": S.read(P.BATCH / "registration.json")["budget"],
            "roles": S.read(P.BATCH / "registration.json")["roles"],
            "capture_limitation": "JSON capture observations for text cover legacy lists/errors, not tuples. Tuple behavior is executed by protected pytest and independent private tests, not claimed as a captured JSON tuple observation.",
            "Primary": "Task/contract and test preparation plus full final source review. No live implementation advice, dependency localization or code takeover. Exact cloud and active time unknown; no economic saving claim.",
            "pins": M.pins(BATCH, Path(__file__), *(m[1] for m in materials.values())),
        },
    )
    print("Four frozen new-slice cells; offline controls passed, no live yet")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "run"])
    parser.add_argument("--cell", choices=ORDER)
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.weekly_used)
    else:
        P.BATCH, P.ORDER = BATCH, ORDER
        P.run(args.cell, args.weekly_used)
