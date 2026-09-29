"""Frozen, read-only Explorer model A/B on identical injected source snapshots."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import stability_e2e as STABILITY


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:48]


def run(
    cases: list[str],
    models: list[str],
    rounds: int,
    output_dir: Path,
    context_length: int,
    reasoning_effort: str | None,
    max_output_tokens: int | None,
    enumerate_tests: bool = False,
    temperature: float | None = None,
    include_baseline_failure: bool = False,
) -> Path:
    source_config = json.loads(
        (STABILITY.KIT / ".local-agents" / "config.json").read_text(
            encoding="utf-8-sig"
        )
    )
    by_name = {case.name: case for case in STABILITY.CASES}
    unknown = set(cases) - set(by_name)
    if unknown:
        raise ValueError(f"unknown cases: {sorted(unknown)}")
    batch = STABILITY.WORK / f"candidate-explorer-{uuid.uuid4().hex[:12]}"
    results: list[dict] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / (
        "candidate-"
        + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + uuid.uuid4().hex[:6]
        + ".json"
    )
    for round_number in range(1, rounds + 1):
        for case_name in cases:
            case = by_name[case_name]
            test_path = f"tests/test_{case.name.replace('-', '_')}.py"
            ordered_models = models if round_number % 2 else list(reversed(models))
            for model in ordered_models:
                model_slug = slug(model)
                workspace = batch / f"round-{round_number}" / case.name / model_slug
                STABILITY.prepare(case, workspace, source_config)
                task = STABILITY.explorer_task(case, test_path)
                if include_baseline_failure:
                    command = (
                        [sys.executable, "-m", "ruff", "check", "src", "tests"]
                        if case.baseline_static_rule
                        else [
                            sys.executable,
                            "-m",
                            "pytest",
                            test_path,
                            "-q",
                            "--tb=short",
                        ]
                    )
                    baseline = STABILITY.run_command(workspace, command, 90)
                    if baseline.returncode == 0:
                        raise ValueError(f"expected baseline failure: {case.name}")
                    observation = (baseline.stdout + baseline.stderr)[-6000:]
                    STABILITY.write_json(
                        workspace / ".agent" / "baseline-observation.json",
                        {
                            "argv": command,
                            "exit_code": baseline.returncode,
                            "output": observation,
                        },
                    )
                    task += (
                        " Trusted baseline check failed on this unchanged fixture. "
                        "This is observed execution evidence, not source proof; read and cite "
                        "the source and tests to explain it, and still predict every focused "
                        "assertion, including cases absent from the failure output. "
                        f"Baseline output:\n{observation}"
                    )
                if enumerate_tests:
                    tree = ast.parse(
                        (workspace / test_path).read_text(encoding="utf-8")
                    )
                    tests = [
                        f"{node.name} (line {node.lineno})"
                        for node in tree.body
                        if isinstance(node, ast.FunctionDef)
                        and node.name.startswith("test_")
                    ]
                    task += (
                        " Coverage checklist, not evidence or results: "
                        + "; ".join(tests)
                        + ". In findings, account for every listed test's source-predicted "
                        "outcome and expected assertion, including any distinct inputs "
                        "inside a parametrized or multi-assertion test."
                    )
                config = {
                    **source_config,
                    "explorer_model": model,
                    "explorer_context_length": context_length,
                    "explorer_required_citation_paths": [
                        case.target,
                        *(mutation.target for mutation in case.extra_mutations),
                        test_path,
                    ],
                }
                if reasoning_effort is not None:
                    config["explorer_reasoning_effort"] = reasoning_effort
                if max_output_tokens is not None:
                    config["explorer_max_tokens"] = max_output_tokens
                    config["explorer_required_tool_max_tokens"] = max_output_tokens
                if temperature is not None:
                    config["explorer_temperature"] = temperature
                config_path = workspace / ".agent" / f"config-{model_slug}.json"
                STABILITY.write_json(config_path, config)
                report_path = workspace / ".agent" / f"explorer-{model_slug}.json"
                task_id = f"candidate-{case.name}-{model_slug}-{uuid.uuid4().hex[:8]}"
                started = time.perf_counter()
                completed = STABILITY.run_command(
                    workspace,
                    [
                        sys.executable,
                        str(workspace / ".local-agents" / "local-explore.py"),
                        "--task",
                        task,
                        "--task-id",
                        task_id,
                        "--config",
                        str(config_path),
                        "--report",
                        str(report_path),
                    ],
                    650,
                )
                report = (
                    json.loads(report_path.read_text(encoding="utf-8"))
                    if report_path.is_file()
                    else {}
                )
                full_path = None
                diagnostic_report = report.get("diagnostic_report")
                if isinstance(diagnostic_report, str):
                    candidate = (workspace / diagnostic_report).resolve()
                    if (
                        candidate.is_relative_to(workspace.resolve())
                        and candidate.is_file()
                    ):
                        full_path = str(candidate)
                diagnostic = report.get("diagnostic_log")
                events = (
                    STABILITY.read_events(workspace / diagnostic)
                    if isinstance(diagnostic, str)
                    else []
                )
                context = STABILITY.context_summary(events)
                cache_hit = bool(report.get("cache", {}).get("hit"))
                evidence_valid = STABILITY.explorer_has_line_evidence(
                    STABILITY.full_explorer_report(workspace, report), case, test_path
                )
                result = {
                    "round": round_number,
                    "case": case.name,
                    "model": model,
                    "context_length": context_length,
                    "reasoning_effort": config.get("explorer_reasoning_effort"),
                    "max_output_tokens": config.get("explorer_max_tokens", 2048),
                    "enumerate_tests": enumerate_tests,
                    "include_baseline_failure": include_baseline_failure,
                    "temperature": config.get("explorer_temperature", 0.1),
                    "workspace": str(workspace),
                    "report": str(report_path),
                    "full_report": full_path,
                    "compact_findings_truncated": report.get("findings_truncated"),
                    "exit_code": completed.returncode,
                    "status": report.get("status"),
                    "failure_reason": report.get("failure_reason"),
                    "infra_failure": report.get("infra_failure"),
                    "line_evidence_valid": evidence_valid,
                    "cache_hit": cache_hit,
                    "model_exercised": bool(context["requests"]) and not cache_hit,
                    # A source line can be real while the conclusion drawn from it
                    # is false. Semantic qualification is a separate manual review.
                    "mechanical_success": report.get("status") == "success"
                    and evidence_valid
                    and bool(context["requests"])
                    and not cache_hit,
                    "semantic_review_required": True,
                    "wall_seconds": round(time.perf_counter() - started, 2),
                    "context": context,
                }
                results.append(result)
                STABILITY.write_json(
                    path,
                    {"batch": str(batch), "results": results},
                )
                print(json.dumps(result, ensure_ascii=False), flush=True)
    print(path, flush=True)
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases", default="selection-order,internal-trace,sample-identity"
    )
    parser.add_argument("--models", default="openai/gpt-oss-20b,prism-ml/bonsai-27b")
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--context-length", type=int, default=32768)
    parser.add_argument("--reasoning-effort", choices=("low", "medium", "high"))
    parser.add_argument("--max-output-tokens", type=int)
    parser.add_argument("--enumerate-tests", action="store_true")
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--include-baseline-failure", action="store_true")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=STABILITY.KIT / "benchmarks" / "results" / "explorer-candidates",
    )
    args = parser.parse_args()
    if not 1 <= args.rounds <= 3:
        parser.error("rounds must be between 1 and 3")
    if args.context_length < 4096:
        parser.error("context length must be at least 4096")
    if args.max_output_tokens is not None and args.max_output_tokens < 512:
        parser.error("max output tokens must be at least 512")
    if args.temperature is not None and not 0 <= args.temperature <= 2:
        parser.error("temperature must be between 0 and 2")
    run(
        args.cases.split(","),
        args.models.split(","),
        args.rounds,
        args.output_dir,
        args.context_length,
        args.reasoning_effort,
        args.max_output_tokens,
        args.enumerate_tests,
        args.temperature,
        args.include_baseline_failure,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
