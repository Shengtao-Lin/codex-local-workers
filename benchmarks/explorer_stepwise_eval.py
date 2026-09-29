"""Probe one independently scored Explorer investigation per frozen test function.

This is an experimental protocol, not a replacement for the frozen baseline.
The test names provide coverage targets, never expected outcomes or answers.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
import time
import uuid
from pathlib import Path

import stability_e2e as STABILITY


def test_functions(source: str) -> list[tuple[str, int]]:
    tree = ast.parse(source)
    return [
        (node.name, node.lineno)
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    ]


def question(case: STABILITY.Case, test_path: str, name: str, line: int) -> str:
    source_paths = list(
        dict.fromkeys(
            [case.target, *(mutation.target for mutation in case.extra_mutations)]
        )
    )
    reads = " and ".join(f"READ_FILE {path}" for path in [*source_paths, test_path])
    return (
        f"{reads}. Answer only this: for {test_path} function {name} "
        f"(starts at line {line}), what does current source predict for EACH "
        "distinct input or assertion, and what does that assertion expect? "
        "Do not substitute assertions from another test function. Resolve any "
        "helper or fixture values used by this function. "
        "Follow the actual call path through conversions, validation and exception "
        "handling, including early returns and default field values; for "
        "parameterized tests, account for each parameter separately. "
        "When a size guard applies, compute or derive the size of the transformed "
        "value actually compared, not the size of an earlier input. "
        "State agreement or conflict and any genuine uncertainty. Do not treat a "
        "test expectation as proof of source behavior or claim test execution. "
        "A source/test mismatch is a successful investigation: report it with "
        "FINISH_SUCCESS, not FINISH_FAILED. "
        "Cite observed source and test lines as full paths followed by line N in "
        "findings or call_flow, include the test path in relevant_tests, and "
        "FINISH_SUCCESS when the investigation has evidence."
    )


def run(cases: list[str], rounds: int, output_dir: Path) -> Path:
    source_config = json.loads(
        (STABILITY.KIT / ".local-agents/config.json").read_text(encoding="utf-8-sig")
    )
    by_name = {case.name: case for case in STABILITY.CASES}
    unknown = set(cases) - set(by_name)
    if unknown:
        raise ValueError(f"unknown cases: {sorted(unknown)}")
    batch = STABILITY.WORK / f"explorer-stepwise-{uuid.uuid4().hex[:12]}"
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = output_dir / f"{batch.name}.json"
    results: list[dict] = []
    for round_number in range(1, rounds + 1):
        for case_name in cases:
            case = by_name[case_name]
            workspace = batch / f"round-{round_number}" / case_name
            config_path, _ = STABILITY.prepare(case, workspace, source_config)
            test_path = f"tests/test_{case.name.replace('-', '_')}.py"
            test_file = workspace / test_path
            for name, line in test_functions(test_file.read_text(encoding="utf-8")):
                report_path = workspace / ".agent" / f"explorer-{name}.json"
                started = time.perf_counter()
                completed = STABILITY.run_command(
                    workspace,
                    [
                        sys.executable,
                        str(workspace / ".local-agents/local-explore.py"),
                        "--task",
                        question(case, test_path, name, line),
                        "--task-id",
                        f"stepwise-{case_name}-{uuid.uuid4().hex[:8]}",
                        "--config",
                        str(config_path),
                        "--report",
                        str(report_path),
                    ],
                    650,
                )
                compact = (
                    json.loads(report_path.read_text(encoding="utf-8"))
                    if report_path.is_file()
                    else {}
                )
                full = STABILITY.full_explorer_report(workspace, compact)
                diagnostic_log = compact.get("diagnostic_log")
                events = (
                    STABILITY.read_events(workspace / diagnostic_log)
                    if isinstance(diagnostic_log, str)
                    else []
                )
                context = STABILITY.context_summary(events)
                cache_hit = bool(compact.get("cache", {}).get("hit"))
                diagnostic = compact.get("diagnostic_report")
                full_path = (
                    str((workspace / diagnostic).resolve())
                    if isinstance(diagnostic, str)
                    and (workspace / diagnostic)
                    .resolve()
                    .is_relative_to(workspace.resolve())
                    and (workspace / diagnostic).is_file()
                    else None
                )
                result = {
                    "round": round_number,
                    "case": case_name,
                    "test_function": name,
                    "test_line": line,
                    "workspace": str(workspace),
                    "report": str(report_path),
                    "full_report": full_path,
                    "exit_code": completed.returncode,
                    "status": compact.get("status"),
                    "failure_reason": compact.get("failure_reason"),
                    "line_evidence_valid": STABILITY.explorer_has_line_evidence(
                        full, case, test_path
                    ),
                    "cache_hit": cache_hit,
                    "model_exercised": bool(context["requests"]) and not cache_hit,
                    "context": context,
                    "semantic_review_required": True,
                    "wall_seconds": round(time.perf_counter() - started, 2),
                }
                results.append(result)
                STABILITY.write_json(summary, {"batch": str(batch), "results": results})
                print(json.dumps(result, ensure_ascii=False), flush=True)
    print(summary, flush=True)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default="metadata-limit,mapping-message-sequence")
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--output-dir", type=Path, default=STABILITY.WORK)
    args = parser.parse_args()
    if not 1 <= args.rounds <= 3:
        parser.error("rounds must be between 1 and 3")
    run(args.cases.split(","), args.rounds, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
