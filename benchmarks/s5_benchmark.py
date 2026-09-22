from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent
WORK = ROOT / "work"
RESULTS = ROOT / "results"


@dataclass(frozen=True)
class Case:
    task_id: str
    title: str
    requirement: str
    source: str
    public_tests: str
    hidden_tests: str


CASES = (
    Case(
        "task-01",
        "Normalize a username",
        "Implement normalize_username(value): require str, trim surrounding whitespace, casefold it, collapse internal whitespace runs to one underscore, and reject an empty normalized value with ValueError.",
        '''def normalize_username(value):
    """Return the canonical username used as an account key."""
    return value.strip().lower()
''',
        '''import pytest
from solution import normalize_username

def test_normalizes_common_input():
    assert normalize_username("  Ada  Lovelace ") == "ada_lovelace"

def test_rejects_empty():
    with pytest.raises(ValueError):
        normalize_username("   ")
''',
        '''import pytest
from solution import normalize_username

def test_unicode_casefold_and_whitespace():
    assert normalize_username(" STRA\u00dfE\tName ") == "strasse_name"

def test_rejects_non_string():
    with pytest.raises(TypeError):
        normalize_username(None)
''',
    ),
    Case(
        "task-02",
        "One-based pagination",
        "Implement page_items(items, page, page_size): page and page_size are positive non-bool integers, page numbering starts at 1, an out-of-range page returns [], and the input sequence is not mutated.",
        '''def page_items(items, page, page_size):
    start = page * page_size
    return list(items[start:start + page_size])
''',
        '''import pytest
from solution import page_items

def test_first_and_second_page():
    values = [1, 2, 3, 4, 5]
    assert page_items(values, 1, 2) == [1, 2]
    assert page_items(values, 2, 2) == [3, 4]

def test_rejects_zero_page():
    with pytest.raises(ValueError):
        page_items([1], 0, 2)
''',
        '''import pytest
from solution import page_items

@pytest.mark.parametrize("page,size", [(True, 2), (1, False), (1.5, 2)])
def test_rejects_non_integer_or_bool(page, size):
    with pytest.raises(TypeError):
        page_items([1, 2], page, size)

def test_last_partial_and_no_mutation():
    values = [1, 2, 3]
    assert page_items(values, 2, 2) == [3]
    assert values == [1, 2, 3]
    assert page_items(values, 3, 2) == []
''',
    ),
    Case(
        "task-03",
        "Recursive settings merge",
        "Implement merge_settings(defaults, overrides): recursively merge nested dictionaries, let non-dict overrides replace defaults, preserve untouched defaults, return independent containers, and never mutate either input.",
        '''def merge_settings(defaults, overrides):
    result = defaults.copy()
    result.update(overrides)
    return result
''',
        '''from solution import merge_settings

def test_nested_merge_preserves_siblings():
    defaults = {"db": {"host": "localhost", "port": 5432}}
    assert merge_settings(defaults, {"db": {"port": 5433}}) == {
        "db": {"host": "localhost", "port": 5433}
    }
''',
        '''from solution import merge_settings

def test_inputs_and_nested_output_are_independent():
    defaults = {"features": {"flags": ["a"]}}
    overrides = {"extra": {"enabled": True}}
    result = merge_settings(defaults, overrides)
    result["features"]["flags"].append("b")
    result["extra"]["enabled"] = False
    assert defaults == {"features": {"flags": ["a"]}}
    assert overrides == {"extra": {"enabled": True}}

def test_scalar_replaces_mapping():
    assert merge_settings({"a": {"b": 1}}, {"a": 9}) == {"a": 9}
''',
    ),
    Case(
        "task-04",
        "Parse a TCP port",
        "Implement parse_port(value): accept integers or whitespace-padded decimal strings, reject bool and all other types with TypeError, reject malformed strings with ValueError, and require the inclusive range 1..65535.",
        '''def parse_port(value):
    return int(value)
''',
        '''import pytest
from solution import parse_port

def test_accepts_integer_and_string():
    assert parse_port(443) == 443
    assert parse_port(" 8080 ") == 8080

def test_rejects_out_of_range():
    with pytest.raises(ValueError):
        parse_port(0)
''',
        '''import pytest
from solution import parse_port

@pytest.mark.parametrize("value", [True, 3.2, None])
def test_rejects_wrong_types(value):
    with pytest.raises(TypeError):
        parse_port(value)

@pytest.mark.parametrize("value", ["", "1.5", "abc", 65536])
def test_rejects_malformed_or_large(value):
    with pytest.raises(ValueError):
        parse_port(value)
''',
    ),
    Case(
        "task-05",
        "Stable case-insensitive deduplication",
        "Implement unique_names(values): require every item to be str, preserve the first spelling and input order, compare names with Unicode casefold, and do not mutate the input.",
        '''def unique_names(values):
    return list(set(values))
''',
        '''from solution import unique_names

def test_preserves_first_and_order():
    assert unique_names(["Ada", "bob", "ADA", "Cara", "Bob"]) == ["Ada", "bob", "Cara"]
''',
        '''import pytest
from solution import unique_names

def test_unicode_casefold_and_input_unchanged():
    values = ["Stra\u00dfe", "STRASSE", "X"]
    assert unique_names(values) == ["Stra\u00dfe", "X"]
    assert values == ["Stra\u00dfe", "STRASSE", "X"]

def test_rejects_non_string_member():
    with pytest.raises(TypeError):
        unique_names(["ok", 2])
''',
    ),
    Case(
        "task-06",
        "Capped exponential retry delay",
        "Implement retry_delay(base, attempt, cap): numeric base/cap must be positive, attempt must be a non-bool integer >= 0, return min(cap, base * 2**attempt), and never return above cap even for huge attempts.",
        '''def retry_delay(base, attempt, cap):
    return base * attempt
''',
        '''import pytest
from solution import retry_delay

def test_exponential_and_cap():
    assert retry_delay(0.5, 0, 10) == 0.5
    assert retry_delay(0.5, 3, 3) == 3

def test_rejects_negative_attempt():
    with pytest.raises(ValueError):
        retry_delay(1, -1, 5)
''',
        '''import math
import pytest
from solution import retry_delay

def test_huge_attempt_is_safely_capped():
    assert retry_delay(1, 100000, 60) == 60

@pytest.mark.parametrize("args,error", [((0, 1, 5), ValueError), ((1, True, 5), TypeError), ((1, 1.2, 5), TypeError), ((1, 1, math.inf), ValueError)])
def test_invalid_arguments(args, error):
    with pytest.raises(error):
        retry_delay(*args)
''',
    ),
    Case(
        "task-07",
        "TTL cache boundary",
        "Implement TTLCache(ttl, clock): ttl must be positive, set stores a value at the injected clock time, get returns it only while age < ttl, expiration at exactly ttl raises KeyError and removes the entry, and different keys remain independent.",
        '''import time

class TTLCache:
    def __init__(self, ttl, clock=time.monotonic):
        self.ttl = ttl
        self.clock = clock
        self.data = {}

    def set(self, key, value):
        self.data[key] = (value, self.clock())

    def get(self, key):
        value, created = self.data[key]
        if self.clock() - created <= self.ttl:
            return value
        raise KeyError(key)
''',
        '''import pytest
from solution import TTLCache

def test_fresh_then_expired():
    now = [10.0]
    cache = TTLCache(2, lambda: now[0])
    cache.set("a", 3)
    assert cache.get("a") == 3
    now[0] = 12.0
    with pytest.raises(KeyError):
        cache.get("a")
''',
        '''import pytest
from solution import TTLCache

def test_expiration_removes_only_target():
    now = [0.0]
    cache = TTLCache(5, lambda: now[0])
    cache.set("old", 1)
    now[0] = 3.0
    cache.set("new", 2)
    now[0] = 5.0
    with pytest.raises(KeyError):
        cache.get("old")
    assert "old" not in cache.data
    assert cache.get("new") == 2

def test_rejects_nonpositive_ttl():
    with pytest.raises(ValueError):
        TTLCache(0)
''',
    ),
    Case(
        "task-08",
        "Strict CSV records",
        "Implement parse_records(text): parse CSV with the first row as non-empty trimmed headers, skip completely blank rows, trim every field, return dictionaries, and raise ValueError when a data row has a different field count.",
        '''import csv
import io

def parse_records(text):
    rows = csv.reader(io.StringIO(text))
    headers = next(rows)
    return [dict(zip(headers, row)) for row in rows]
''',
        '''import pytest
from solution import parse_records

def test_trims_headers_and_fields():
    assert parse_records(" name , age \\n Ada , 36 \\n") == [{"name": "Ada", "age": "36"}]

def test_rejects_short_row():
    with pytest.raises(ValueError):
        parse_records("a,b\\n1\\n")
''',
        '''import pytest
from solution import parse_records

def test_skips_blank_rows_and_rejects_long_row():
    assert parse_records("a,b\\n\\n1,2\\n") == [{"a": "1", "b": "2"}]
    with pytest.raises(ValueError):
        parse_records("a,b\\n1,2,3\\n")

@pytest.mark.parametrize("text", ["", " ,b\\n", " ,b\\n1,2\\n"])
def test_requires_valid_header(text):
    with pytest.raises(ValueError):
        parse_records(text)
''',
    ),
    Case(
        "task-09",
        "Integer weighted allocation",
        "Implement allocate(total, weights): total is a nonnegative non-bool integer, weights is a non-empty sequence of finite nonnegative numbers with positive sum, return integer shares summing exactly to total, and assign leftover units by largest fractional remainder with stable index tie-breaking.",
        '''def allocate(total, weights):
    scale = total / sum(weights)
    return [round(weight * scale) for weight in weights]
''',
        '''import pytest
from solution import allocate

def test_exact_total_and_largest_remainder():
    assert allocate(10, [1, 1, 1]) == [4, 3, 3]
    assert sum(allocate(7, [1, 2])) == 7

def test_rejects_zero_weight_sum():
    with pytest.raises(ValueError):
        allocate(2, [0, 0])
''',
        '''import math
import pytest
from solution import allocate

def test_zero_total_and_stable_tie():
    assert allocate(0, [1, 2]) == [0, 0]
    assert allocate(2, [1, 1, 1, 1]) == [1, 1, 0, 0]

@pytest.mark.parametrize("total,weights,error", [(-1, [1], ValueError), (True, [1], TypeError), (1, [], ValueError), (1, [1, -1], ValueError), (1, [math.inf], ValueError)])
def test_invalid_inputs(total, weights, error):
    with pytest.raises(error):
        allocate(total, weights)
''',
    ),
    Case(
        "task-10",
        "Batch conversion with indexed errors",
        "Implement convert_all(values, converter): apply converter in order and return converted values; if converter raises ValueError or TypeError, raise ConversionError(index, value, cause) with public attributes and exception chaining; do not catch other exception types or process later values after failure.",
        '''class ConversionError(Exception):
    pass

def convert_all(values, converter):
    return [converter(value) for value in values]
''',
        '''import pytest
from solution import ConversionError, convert_all

def test_converts_in_order():
    assert convert_all(["1", "2"], int) == [1, 2]

def test_wraps_value_error_with_context():
    with pytest.raises(ConversionError) as caught:
        convert_all(["1", "bad"], int)
    assert caught.value.index == 1
    assert caught.value.value == "bad"
    assert isinstance(caught.value.cause, ValueError)
''',
        '''import pytest
from solution import ConversionError, convert_all

def test_success_calls_converter_once_per_item():
    seen = []
    def converter(value):
        seen.append(value)
        return value * 10
    assert convert_all([1, 2], converter) == [10, 20]
    assert seen == [1, 2]

def test_chains_and_stops_after_failure():
    seen = []
    def converter(value):
        seen.append(value)
        if value == 2:
            raise TypeError("no")
        return value
    with pytest.raises(ConversionError) as caught:
        convert_all([1, 2, 3], converter)
    assert seen == [1, 2]
    assert caught.value.__cause__ is caught.value.cause

def test_does_not_wrap_runtime_error():
    def converter(value):
        raise RuntimeError("boom")
    with pytest.raises(RuntimeError):
        convert_all([1], converter)
''',
    ),
)


def selected(task_arg: str | None) -> tuple[Case, ...]:
    if not task_arg:
        return CASES
    wanted = {item.strip() for item in task_arg.split(",") if item.strip()}
    known = {case.task_id for case in CASES}
    unknown = wanted - known
    if unknown:
        raise SystemExit(f"unknown task(s): {', '.join(sorted(unknown))}")
    return tuple(case for case in CASES if case.task_id in wanted)


def atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def task_root(group: str, task_id: str) -> Path:
    return WORK / group / task_id


def packet_for(case: Case, group: str) -> dict:
    run_id = f"s5-{group.lower()}-{case.task_id}-a1"
    return {
        "schema_version": 2,
        "task_id": f"s5-{group.lower()}-{case.task_id}",
        "unit_id": case.task_id,
        "run_id": run_id,
        "attempt": 1,
        "plan_revision": 1,
        "packet_revision": 1,
        "goal": case.requirement,
        "scope": {
            "read": ["solution.py", "tests"],
            "modify": ["solution.py", "tests/test_public.py"],
            "create": [],
            "forbidden": [".agent", ".local-agents"],
        },
        "required_behavior": [{"id": "behavior-1", "text": case.requirement}],
        "acceptance_criteria": [
            {"id": "acceptance-public", "text": "All focused public tests pass."},
            {"id": "acceptance-boundaries", "text": "The implementation covers the stated validation and boundary behavior."},
        ],
        "acceptance_scenarios": [
            {"id": "scenario-normal", "text": "Representative valid input produces the specified result."},
            {"id": "scenario-boundary", "text": "Validation, exception, and boundary behavior matches the requirement."},
        ],
        "validation_profile": "python-focused",
        "focused_tests": ["tests/test_public.py"],
        "explorer_findings": [],
        "review_feedback": [],
        "limits": {
            "max_local_repairs": 2,
            "max_model_turns": 24,
            "max_protocol_errors": 4,
            "command_timeout_seconds": 180,
        },
    }


def prepare(group: str, cases: Iterable[Case], replace: bool) -> None:
    for case in cases:
        destination = task_root(group, case.task_id)
        if destination.exists():
            if not replace:
                raise SystemExit(f"refusing to replace existing task: {destination}")
            shutil.rmtree(destination)
        (destination / "tests").mkdir(parents=True)
        (destination / ".agent").mkdir()
        (destination / "solution.py").write_text(case.source, encoding="utf-8")
        (destination / "tests" / "test_public.py").write_text(case.public_tests, encoding="utf-8")
        (destination / "TASK.md").write_text(f"# {case.title}\n\n{case.requirement}\n", encoding="utf-8")
        atomic_json(destination / ".agent" / "implementation-packet.json", packet_for(case, group))
        atomic_json(destination / ".benchmark-meta.json", {
            "task_id": case.task_id,
            "group": group,
            "prepared_at_unix": time.time(),
            "codex_usage": "unavailable",
        })
        print(f"prepared {group}/{case.task_id}")


def run_pytest(cwd: Path, test_path: Path) -> dict:
    started = time.perf_counter()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(cwd)
    completed = subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", str(test_path)],
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
        check=False,
    )
    return {
        "passed": completed.returncode == 0,
        "exit_code": completed.returncode,
        "duration_seconds": round(time.perf_counter() - started, 3),
        "output": completed.stdout[-12000:],
    }


def evaluate_case(group: str, case: Case, phase: str) -> dict:
    cwd = task_root(group, case.task_id)
    if not cwd.is_dir():
        raise SystemExit(f"task is not prepared: {cwd}")
    public = run_pytest(cwd, cwd / "tests" / "test_public.py")
    # Keep the transient test below the task root. On managed Windows hosts,
    # putting it in the user temp directory can make pytest choose C:\ as the
    # common root and traverse protected profile directories during collection.
    with tempfile.TemporaryDirectory(prefix=f".s5-{case.task_id}-", dir=cwd) as temp_dir:
        hidden_path = Path(temp_dir) / "test_hidden.py"
        hidden_path.write_text(case.hidden_tests, encoding="utf-8")
        hidden = run_pytest(cwd, hidden_path)
    result = {
        "schema_version": 1,
        "task_id": case.task_id,
        "group": group,
        "phase": phase,
        "qualified_pass": public["passed"] and hidden["passed"],
        "public": public,
        "hidden": hidden,
        "measured_at_unix": time.time(),
        "codex_usage": "unavailable",
    }
    atomic_json(RESULTS / group / f"{case.task_id}-{phase}.json", result)
    print(f"{group}/{case.task_id}: public={'PASS' if public['passed'] else 'FAIL'} hidden={'PASS' if hidden['passed'] else 'FAIL'}")
    return result


def summary() -> None:
    records = []
    if RESULTS.exists():
        for path in sorted(RESULTS.glob("*/*-evaluate.json")):
            records.append(json.loads(path.read_text(encoding="utf-8")))
    grouped: dict[str, list[dict]] = {}
    for record in records:
        grouped.setdefault(record["group"], []).append(record)
    payload = {"groups": {}, "codex_usage": "unavailable"}
    for group, items in sorted(grouped.items()):
        passed = sum(bool(item["qualified_pass"]) for item in items)
        task_metrics = []
        for item in items:
            state_path = task_root(group, item["task_id"]) / ".agent" / "tasks" / f"s5-{group.lower()}-{item['task_id']}" / "state.json"
            state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
            reviews = state.get("reviews", [])
            runtime_seconds = 0.0
            for attempt in state.get("execution_history", []):
                archive = task_root(group, item["task_id"]) / attempt["archive"]
                baseline_path = archive / "baseline.json"
                completed_path = archive / "completed.json"
                if baseline_path.exists() and completed_path.exists():
                    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
                    completed = json.loads(completed_path.read_text(encoding="utf-8"))
                    started_at = datetime.fromisoformat(baseline["captured_at"])
                    ended_at = datetime.fromisoformat(completed["completed_at"])
                    runtime_seconds += (ended_at - started_at).total_seconds()
            task_metrics.append({
                "task_id": item["task_id"],
                "qualified_pass": item["qualified_pass"],
                "coder_calls": state.get("usage", {}).get("coder_calls", 0),
                "explorer_calls": state.get("usage", {}).get("explorer_calls", 0),
                "first_review_pass": bool(reviews and reviews[0].get("decision") == "accept"),
                "rework_reviews": sum(review.get("decision") == "rework" for review in reviews),
                "takeovers": sum(review.get("decision") == "takeover" for review in reviews),
                "worker_failed_runs": sum(attempt.get("result") == "failed" for attempt in state.get("execution_history", [])),
                "archived_runtime_seconds": round(runtime_seconds, 3),
            })
        payload["groups"][group] = {
            "evaluated": len(items),
            "qualified_passed": passed,
            "qualified_pass_rate": passed / len(items) if items else None,
            "public_passed": sum(bool(item["public"]["passed"]) for item in items),
            "hidden_passed": sum(bool(item["hidden"]["passed"]) for item in items),
            "test_duration_seconds": round(sum(item["public"]["duration_seconds"] + item["hidden"]["duration_seconds"] for item in items), 3),
            "coder_calls": sum(item["coder_calls"] for item in task_metrics),
            "explorer_calls": sum(item["explorer_calls"] for item in task_metrics),
            "first_review_passed": sum(item["first_review_pass"] for item in task_metrics),
            "rework_reviews": sum(item["rework_reviews"] for item in task_metrics),
            "takeovers": sum(item["takeovers"] for item in task_metrics),
            "worker_failed_runs": sum(item["worker_failed_runs"] for item in task_metrics),
            "archived_runtime_seconds": round(sum(item["archived_runtime_seconds"] for item in task_metrics), 3),
            "tasks": task_metrics,
        }
    atomic_json(RESULTS / "summary.json", payload)
    print(json.dumps(payload, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="S5 local-worker A/B benchmark")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("prepare", "baseline", "evaluate"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--group", choices=("A", "B", "P"), required=True)
        sub.add_argument("--tasks")
        if command == "prepare":
            sub.add_argument("--replace", action="store_true")
    subparsers.add_parser("summary")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.group, selected(args.tasks), args.replace)
    elif args.command in {"baseline", "evaluate"}:
        for case in selected(args.tasks):
            evaluate_case(args.group, case, args.command)
    else:
        summary()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
