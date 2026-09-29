"""Read-only, paired scorecard for real local-worker maintenance tasks.

No result is inferred from subscription-window percentages or worker call counts.
Only records with the same task, trial, source commit, acceptance revision, and
Primary model are compared. The tool never modifies a repository or result file.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any


class EvaluationError(ValueError):
    pass


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvaluationError(f"{label} must be a JSON object")
    return value


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]*", value
    ):
        raise EvaluationError(f"{label} must be a stable identifier")
    return value


def _hash(value: Any, label: str, length: int) -> str:
    if not isinstance(value, str) or not re.fullmatch(
        rf"[a-fA-F0-9]{{{length}}}", value
    ):
        raise EvaluationError(f"{label} must be a {length}-character hex hash")
    return value.lower()


def _nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise EvaluationError(f"{label} must be a nonnegative integer")
    return value


def _positive_int(value: Any, label: str) -> int:
    result = _nonnegative_int(value, label)
    if result == 0:
        raise EvaluationError(f"{label} must be positive")
    return result


def load_manifest(path: Path) -> dict[str, dict[str, str]]:
    raw = _object(json.loads(path.read_text(encoding="utf-8-sig")), "manifest")
    if raw.get("schema_version") != 1:
        raise EvaluationError("manifest schema_version must be 1")
    tasks = raw.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise EvaluationError("manifest.tasks must be a non-empty array")
    catalog: dict[str, dict[str, str]] = {}
    for index, value in enumerate(tasks, 1):
        item = _object(value, f"tasks[{index}]")
        task_id = _identifier(item.get("task_id"), f"tasks[{index}].task_id")
        if task_id in catalog:
            raise EvaluationError(f"duplicate task_id: {task_id}")
        risk = item.get("risk")
        if risk not in {"small", "medium", "high"}:
            raise EvaluationError(f"tasks[{index}].risk must be small, medium, or high")
        category = _identifier(item.get("category"), f"tasks[{index}].category")
        catalog[task_id] = {
            "risk": risk,
            "category": category,
            "start_commit": _hash(item.get("start_commit"), "start_commit", 40),
            "acceptance_sha256": _hash(
                item.get("acceptance_sha256"), "acceptance_sha256", 64
            ),
        }
    return catalog


def _record(
    value: Any, catalog: dict[str, dict[str, str]], line: int
) -> dict[str, Any]:
    item = _object(value, f"records line {line}")
    task_id = _identifier(item.get("task_id"), f"records line {line}.task_id")
    if task_id not in catalog:
        raise EvaluationError(f"records line {line}: unknown task_id {task_id}")
    arm = item.get("arm")
    if arm not in {"primary", "local"}:
        raise EvaluationError(f"records line {line}: arm must be primary or local")
    trial_id = _positive_int(item.get("trial_id"), "trial_id")
    task = catalog[task_id]
    if _hash(item.get("start_commit"), "start_commit", 40) != task["start_commit"]:
        raise EvaluationError(
            f"records line {line}: start_commit differs from manifest"
        )
    if (
        _hash(item.get("acceptance_sha256"), "acceptance_sha256", 64)
        != task["acceptance_sha256"]
    ):
        raise EvaluationError(
            f"records line {line}: acceptance_sha256 differs from manifest"
        )
    for field in ("qualified_pass", "first_gate_pass"):
        if type(item.get(field)) is not bool:
            raise EvaluationError(f"records line {line}: {field} must be boolean")
    wall_seconds = item.get("wall_seconds")
    if (
        type(wall_seconds) not in {int, float}
        or not math.isfinite(wall_seconds)
        or wall_seconds < 0
    ):
        raise EvaluationError(
            f"records line {line}: wall_seconds must be finite and nonnegative"
        )
    primary_model = _identifier(item.get("primary_model"), "primary_model")
    tokens = item.get("primary_tokens")
    token_source = item.get("token_source")
    if tokens is not None:
        tokens = _nonnegative_int(tokens, "primary_tokens")
        if not isinstance(token_source, str) or not token_source.strip():
            raise EvaluationError(
                f"records line {line}: measured tokens need token_source"
            )
    elif token_source is not None:
        raise EvaluationError(
            f"records line {line}: token_source needs measured tokens"
        )
    failure_categories = item.get("failure_categories", [])
    if not isinstance(failure_categories, list) or any(
        not isinstance(value, str) or not value.strip() for value in failure_categories
    ):
        raise EvaluationError(
            f"records line {line}: failure_categories must be strings"
        )
    return {
        "task_id": task_id,
        "trial_id": trial_id,
        "arm": arm,
        "risk": task["risk"],
        "category": task["category"],
        "qualified_pass": item["qualified_pass"],
        "first_gate_pass": item["first_gate_pass"],
        "wall_seconds": float(wall_seconds),
        "primary_model": primary_model,
        "primary_tokens": tokens,
        "token_source": token_source,
        "coder_calls": _nonnegative_int(item.get("coder_calls", 0), "coder_calls"),
        "explorer_calls": _nonnegative_int(
            item.get("explorer_calls", 0), "explorer_calls"
        ),
        "reviewer_calls": _nonnegative_int(
            item.get("reviewer_calls", 0), "reviewer_calls"
        ),
        "takeovers": _nonnegative_int(item.get("takeovers", 0), "takeovers"),
        "failure_categories": failure_categories,
    }


def load_records(
    path: Path, catalog: dict[str, dict[str, str]]
) -> dict[tuple[str, int, str], dict[str, Any]]:
    records: dict[tuple[str, int, str], dict[str, Any]] = {}
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(), 1
    ):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError as exc:
            raise EvaluationError(
                f"records line {line_number}: invalid JSON: {exc}"
            ) from exc
        item = _record(value, catalog, line_number)
        key = (item["task_id"], item["trial_id"], item["arm"])
        if key in records:
            raise EvaluationError(f"duplicate record: {key}")
        records[key] = item
    return records


def summarize(records: dict[tuple[str, int, str], dict[str, Any]]) -> dict[str, Any]:
    trial_keys = sorted({(task, trial) for task, trial, _arm in records})
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    unpaired: list[dict[str, Any]] = []
    for task_id, trial_id in trial_keys:
        primary = records.get((task_id, trial_id, "primary"))
        local = records.get((task_id, trial_id, "local"))
        if primary is None or local is None:
            unpaired.append(
                {
                    "task_id": task_id,
                    "trial_id": trial_id,
                    "missing_arm": "primary" if primary is None else "local",
                }
            )
            continue
        if primary["primary_model"] != local["primary_model"]:
            raise EvaluationError(
                f"{task_id} trial {trial_id}: paired arms used different Primary models"
            )
        pairs.append((primary, local))
    measured = [
        (primary, local)
        for primary, local in pairs
        if primary["primary_tokens"] is not None and local["primary_tokens"] is not None
    ]
    primary_tokens = sum(primary["primary_tokens"] for primary, _local in measured)
    local_tokens = sum(local["primary_tokens"] for _primary, local in measured)
    failures = Counter(
        category
        for _primary, local in pairs
        for category in local["failure_categories"]
    )
    return {
        "schema_version": 1,
        "paired_trials": len(pairs),
        "unpaired_trials": unpaired,
        "risk_counts": dict(
            sorted(Counter(local["risk"] for _primary, local in pairs).items())
        ),
        "quality_regressions": [
            {"task_id": primary["task_id"], "trial_id": primary["trial_id"]}
            for primary, local in pairs
            if primary["qualified_pass"] and not local["qualified_pass"]
        ],
        "primary_qualified": sum(
            primary["qualified_pass"] for primary, _local in pairs
        ),
        "local_qualified": sum(local["qualified_pass"] for _primary, local in pairs),
        "primary_first_gate": sum(
            primary["first_gate_pass"] for primary, _local in pairs
        ),
        "local_first_gate": sum(local["first_gate_pass"] for _primary, local in pairs),
        "median_wall_seconds": {
            "primary": statistics.median(
                primary["wall_seconds"] for primary, _local in pairs
            )
            if pairs
            else None,
            "local": statistics.median(
                local["wall_seconds"] for _primary, local in pairs
            )
            if pairs
            else None,
        },
        "token_evidence": {
            "measured_pairs": len(measured),
            "primary_tokens": primary_tokens if measured else None,
            "local_tokens": local_tokens if measured else None,
            "reduction_percent": round(
                100 * (primary_tokens - local_tokens) / primary_tokens, 2
            )
            if primary_tokens > 0
            else None,
            "status": (
                "measured_all"
                if measured and len(measured) == len(pairs)
                else "measured_subset"
                if measured
                else "unavailable"
            ),
        },
        "local_worker_calls": {
            field: sum(local[field] for _primary, local in pairs)
            for field in (
                "explorer_calls",
                "coder_calls",
                "reviewer_calls",
                "takeovers",
            )
        },
        "local_failure_categories": dict(sorted(failures.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only paired real-task scorecard")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--records", type=Path, required=True)
    args = parser.parse_args()
    try:
        catalog = load_manifest(args.manifest)
        records = load_records(args.records, catalog)
        report = summarize(records)
    except (OSError, ValueError) as exc:
        print(f"scorecard error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
