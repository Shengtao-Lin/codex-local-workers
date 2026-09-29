"""Extract attributable token evidence from one Codex CLI `exec --json` run.

The JSONL may contain prompts, code, and tool results; keep the input private.
This reads it without modification and prints only aggregate counts and a hash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


class UsageError(ValueError):
    pass


def _count(value: Any, name: str) -> int:
    if type(value) is not int or value < 0:
        raise UsageError(f"{name} must be a nonnegative integer")
    return value


def extract(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    turns = []
    failed = False
    for line_number, line in enumerate(raw.decode("utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError as exc:
            raise UsageError(f"line {line_number}: invalid JSON") from exc
        if not isinstance(event, dict):
            raise UsageError(f"line {line_number}: event must be an object")
        if event.get("type") in {"turn.failed", "error"}:
            failed = True
        if event.get("type") == "turn.completed":
            turns.append(event)
    if failed:
        raise UsageError("stream contains a failed turn or error")
    if len(turns) != 1:
        raise UsageError(f"expected exactly one completed turn, found {len(turns)}")
    usage = turns[0].get("usage")
    if not isinstance(usage, dict):
        raise UsageError("completed turn has no usage object")
    input_tokens = _count(usage.get("input_tokens"), "input_tokens")
    output_tokens = _count(usage.get("output_tokens"), "output_tokens")
    cached = _count(usage.get("cached_input_tokens", 0), "cached_input_tokens")
    reasoning = _count(
        usage.get("reasoning_output_tokens", 0), "reasoning_output_tokens"
    )
    if cached > input_tokens or reasoning > output_tokens:
        raise UsageError("token subcounts exceed their parent count")
    digest = hashlib.sha256(raw).hexdigest()
    return {
        "primary_tokens": input_tokens + output_tokens,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cached_input_tokens": cached,
        "reasoning_output_tokens": reasoning,
        "token_source": f"codex-exec-jsonl-sha256:{digest}",
    }


def aggregate(paths: list[Path]) -> dict[str, Any]:
    if not paths:
        raise UsageError("at least one JSONL stream is required")
    samples = [extract(path) for path in paths]
    sources = [sample["token_source"] for sample in samples]
    if len(set(sources)) != len(sources):
        raise UsageError("duplicate JSONL stream supplied")
    source_digest = hashlib.sha256("\n".join(sorted(sources)).encode()).hexdigest()
    return {
        "primary_tokens": sum(sample["primary_tokens"] for sample in samples),
        "input_tokens": sum(sample["input_tokens"] for sample in samples),
        "output_tokens": sum(sample["output_tokens"] for sample in samples),
        "cached_input_tokens": sum(sample["cached_input_tokens"] for sample in samples),
        "reasoning_output_tokens": sum(
            sample["reasoning_output_tokens"] for sample in samples
        ),
        "streams": len(samples),
        "token_source": f"codex-exec-jsonl-set-sha256:{source_digest}",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract one task's measured usage from Codex exec streams"
    )
    parser.add_argument("jsonl", type=Path, nargs="+")
    args = parser.parse_args()
    try:
        result = aggregate(args.jsonl)
    except (OSError, UnicodeError, UsageError) as exc:
        print(f"usage error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
