"""Faithfully factor the frozen A delta into high-risk A1 and atomic A2 audits.

The intermediate is a derived source snapshot, NOT a historical execution.
Canonical archives are explicitly synthetic; no Coder-performance credit.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from v13_diagnostic_compat import WORK, write

A1_SYMBOLS = {
    "resolve_inherited_packet",
    "_begin_edit",
    "_is_repair_edit",
    "_record_edit",
}
A1_TESTS = [
    "test_v13_baseline_does_not_spend_two_post_implementation_repairs",
    "test_v13_inherited_run_cannot_claim_fresh_baseline_budget",
    "test_inherited_rework_packet_preserves_parent_contract",
    "test_failed_replace_does_not_consume_repair_budget",
    "test_safe_replace_rejects_noop_without_spending_repair",
    "test_successful_repair_edit_is_marked_for_turn_reserve",
]


def intermediate_source(before: str, candidate: str) -> str:
    """Keep A1 functions atomic; acknowledgement invalidation belongs to A2."""
    old_lines = before.splitlines(keepends=True)
    new_lines = candidate.splitlines(keepends=True)
    old_nodes = {
        node.name: node
        for node in ast.walk(ast.parse(before))
        if isinstance(node, ast.FunctionDef) and node.name in A1_SYMBOLS
    }
    new_nodes = {
        node.name: node
        for node in ast.walk(ast.parse(candidate))
        if isinstance(node, ast.FunctionDef) and node.name in A1_SYMBOLS
    }
    if set(new_nodes) != A1_SYMBOLS or set(old_nodes) != A1_SYMBOLS - {
        "_is_repair_edit"
    }:
        raise ValueError("frozen A1 symbol set drift")
    for name, old in sorted(
        old_nodes.items(), key=lambda pair: pair[1].lineno, reverse=True
    ):
        new = new_nodes[name]
        replacement = new_lines[new.lineno - 1 : new.end_lineno]
        if name == "_record_edit":
            replacement = [
                line
                for line in replacement
                if line.strip() != "self.last_contract_check = None"
            ]
        if name == "_begin_edit":
            helper = new_nodes["_is_repair_edit"]
            replacement = (
                replacement + ["\n"] + new_lines[helper.lineno - 1 : helper.end_lineno]
            )
        old_lines[old.lineno - 1 : old.end_lineno] = replacement
    result = "".join(old_lines)
    ast.parse(result)
    return result


def checked_snapshot(label: str) -> Path:
    if not label or any(
        c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in label
    ):
        raise ValueError("invalid snapshot label")
    root = WORK / label
    manifest = json.loads((root / "freeze.json").read_text(encoding="utf-8"))
    for relative, digest in manifest["files"].items():
        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != digest:
            raise ValueError("frozen snapshot drift: " + relative)
    return root


def prepare(
    unit: str, candidate: Path, trial: str
) -> tuple[Path, dict, tuple[dict, dict]]:
    before = checked_snapshot(
        "roleq-native-wire-baseline-1"
        if unit == "d7"
        else "roleq-final-channel-baseline-1"
        if unit == "d6"
        else "roleq-prefetch-guard-baseline-1"
        if unit == "d5"
        else "roleq-edit-recovery-baseline-1"
        if unit == "d4"
        else "roleq-timeout-baseline-1"
        if unit == "d3"
        else "roleq-six-runtime-1"
        if unit == "d2"
        else "v13diag-before-1"
        if unit == "d1"
        else "v13-a-before-1"
    )
    root = WORK / f"v13-scoped-{unit}-{trial}"
    root.mkdir(exist_ok=False)
    shutil.copytree(candidate / ".local-agents", root / ".local-agents")
    shutil.copytree(candidate / ".local-agents", root / "src")
    old_worker = (before / ".local-agents/worker-runtime.py").read_text(
        encoding="utf-8"
    )
    new_worker = (candidate / ".local-agents/worker-runtime.py").read_text(
        encoding="utf-8"
    )
    intermediate = (
        old_worker
        if unit in {"d1", "d2", "d3", "d4", "d5", "d6", "d7"}
        else intermediate_source(old_worker, new_worker)
    )
    initial_worker = (
        old_worker
        if unit in {"a1", "d1", "d2", "d3", "d4", "d5", "d6", "d7"}
        else intermediate
    )
    final_worker = intermediate if unit == "a1" else new_worker
    (root / "src/worker-runtime.py").write_text(initial_worker, encoding="utf-8")
    (root / "src/local-unit.py").write_bytes(
        (before / ".local-agents/local-unit.py").read_bytes()
    )
    writable = ["src/worker-runtime.py"] + (
        []
        if unit in {"a1", "d1", "d2", "d3", "d4", "d5", "d7"}
        else ["src/local-unit.py"]
    )
    if unit == "r1":
        writable = ["src/reviewer-runtime.py"]
        (root / "src/worker-runtime.py").write_text(new_worker, encoding="utf-8")
        (root / "src/local-unit.py").write_bytes(
            (candidate / ".local-agents/local-unit.py").read_bytes()
        )
        (root / "src/reviewer-runtime.py").write_bytes(
            (
                checked_snapshot("v13d") / ".local-agents/reviewer-runtime.py"
            ).read_bytes()
        )
    focused = (
        [
            f"src/tests/test_worker_runtime.py::WorkerRuntimeTests::{name}"
            for name in A1_TESTS
        ]
        if unit == "a1"
        else ["src/tests/test_reviewer_runtime.py"]
        if unit == "r1"
        else ["src/tests/test_worker_runtime.py", "src/tests/test_local_unit.py"]
    )
    if unit in {"d1", "d2", "d3", "d4", "d5"}:
        focused = ["src/tests/test_worker_runtime.py"]
    if unit == "d7":
        focused = [
            "src/tests/test_worker_runtime.py::WorkerRuntimeTests::" + name
            for name in (
                "test_lmstudio_client_normalizes_one_native_tool_call",
                "test_native_schema_cost_blocks_oversized_request_before_http",
                "test_native_parallel_response_still_fails_closed",
                "test_lmstudio_client_can_disable_structured_output_for_compatibility",
            )
        ]
    if unit == "d6":
        writable = ["src/explorer-runtime.py"]
        (root / writable[0]).write_bytes(
            (before / ".local-agents/explorer-runtime.py").read_bytes()
        )
        focused = ["src/tests/test_explorer_runtime.py"]
        if trial in {"2", "3"}:
            focused = [
                "src/tests/test_explorer_runtime.py::ExplorerRuntimeTests::" + name
                for name in (
                    "test_reasoning_candidates_never_become_executable_actions",
                    "test_repeated_reasoning_only_fails_closed_without_raw_excerpt",
                    "test_final_native_call_remains_authoritative_with_reasoning_present",
                    "test_legacy_cached_reports_cannot_bypass_final_channel_authority",
                    "test_empty_response_repair_keeps_roles_alternating_after_merge",
                    "test_output_length_failure_is_infrastructure_not_worker_quality",
                )
            ]
    contracts = (
        [
            {
                "id": "repair-budget-accounting",
                "text": "Fresh pre-edit failed diagnostics do not consume the initial implementation's repair allowance; subsequent failed validation starts one bounded repair cycle per effective edit series. No-op/mismatch and multi-edit accounting remain sound. Inherited rework is not fresh; parent hash provenance is recorded, never reused as current validation. Inspect _begin_edit, _is_repair_edit, _record_edit and resolve_inherited_packet. A2 diagnostic/submission separation is a later dependency and is not claimed by A1.",
            }
        ]
        if unit == "a1"
        else [
            {
                "id": "diagnostic-not-acceptance",
                "text": "Check may execute with truthful false/null ordering claims, stored as claims not runtime proof. Final and legacy FINISH_SUCCESS require complete current acknowledgements. Edits invalidate prior acknowledgement and validation; a green fresh unedited baseline never enters final terminal state. Inspect _contract_check, _assert_submission_contract, execute(FINISH_SUCCESS), _record_edit and validate(effective_phase).",
            },
            {
                "id": "fresh-validation-handoff",
                "text": "Independent verify_handoff rejects missing/false/unknown diagnostic acknowledgements and preserves schema-v1/v2 compatibility, actual nonzero JUnit, identity, input freshness, path attribution and scope gates. This boundary and Coder submission must remain one atomic A2 unit. Passing tests alone do not establish semantic compliance.",
            },
        ]
    )
    if unit == "r1":
        contracts = [
            {
                "id": "review-evidence-navigation",
                "text": "On a duplicate source read when required test evidence is missing, show at most 40 current lines from an existing packet-scoped focused test using the normal read guard. Never bypass forbidden/reparse scope, recursively prefetch a test, mark truncated unseen lines as read, infer verified contracts or approve a report. Keep all report validation, execution acknowledgement and deadline/turn gates unchanged. Read read_file and the new forbidden/truncation regression tests.",
            }
        ]
    if unit == "d1":
        contracts = [
            {
                "id": "failed-test-diagnostics-not-acceptance",
                "text": "Default configured-check behavior unchanged. Only trusted-profile boolean run_on_test_failure=true permits the configured command after a real failed focused test run with current inputs and nonzero available JUnit. Missing/zero/all-skipped JUnit or drift must skip diagnostics; drift after one diagnostic stops later diagnostics. No autoformat/revalidation on failed tests. Static success never erases failed tests, consumes repair budget or permits submission. No additional shell authority or packet-controlled command. Read validate around diagnostic_checks_allowed and test_failed_tests_only_run_explicit_diagnostics_with_current_nonzero_junit, plus existing green-check/autoformat tests.",
            }
        ]
    if unit == "d2":
        contracts = [
            {
                "id": "bounded-pytest-binding-evidence",
                "text": "Preserve at most four displayed argument bindings from the leading pytest JUnit traceback header, name <=32 and representation <=120 chars, stop on non-binding/blank, no evaluation or inferred expected behavior. Keep per-test examples within shared failure groups at most three, pass bindings into compact repair test evidence. Missing header leaves legacy failures unchanged. No permission, edit scope, repair accounting, acceptance, validation or terminal gate changes. Inspect _junit_failures, _failed_test_repair_focus, _compact_repair_payload and JUnitDisplayedBindingTests/test_grouped_failure_examples_keep_bindings_in_compact_evidence.",
            }
        ]
    if unit == "d3":
        contracts = [
            {
                "id": "unchanged-timeout-validation-gate",
                "text": "Before incrementing validation_count, archiving a new attempt or executing commands, refuse VALIDATE only when previous validation failed, focused_tests explicitly timed_out True, inputs_unchanged True, and input_facts match current _validation_facts. An actual changed input, ordinary failure, or inputs that drifted during prior validation must not trigger this refusal. Surface the observed focused timeout and retry constraint without inferring semantic failure or acceptance. No scope, command authority, repair accounting, final acknowledgement, JUnit or handoff acceptance weakening. Inspect validate, _validation_observation, and the three new timeout tests including a real bounded pytest timeout.",
            }
        ]
    if unit == "d4":
        contracts = [
            {
                "id": "scoped-whitespace-preparation",
                "text": "Only explicit boolean autoformat_on_diff_whitespace=true, permitted existing autoformat setting and a trusted Ruff format --check profile may trigger one scoped formatting attempt for exclusively introduced trailing whitespace in changed authorized Python files. Default behavior, scope, read/hash guards and contract checks remain unchanged. Preserve the original rejected validation attempt; if formatting changes bytes, run fresh complete validation before any success. Re-run diff-quality and semantic tests; formatting never substitutes for either. Significant string whitespace remains protected by the formatter and remaining issues still fail. Unexpected protected-input mutation raises PolicyViolation. Inspect _record_edit, _diff_whitespace_autoformat_eligible, _try_autoformat, validate and the three new diff_whitespace/real_formatter tests. This synthetic archive grants zero Coder credit.",
            }
        ]
    if unit == "d5":
        contracts = [
            {
                "id": "guarded-source-discovery",
                "text": "Coder SEARCH and automatic repair-context source/test/symbol reads must obey the same _assert_read_allowed scope/forbidden/excluded/reparse checks as explicit reads. Prune prohibited or reparse directories before traversal; check each file. Preserve broad repository read root '.', literal/regex search behavior and allowed evidence. Bound symbol scanning to 1000 eligible files and five matches; retain file-size limits. No new observed-line authority, edits, contract changes, JUnit or final/handoff acceptance. Inspect _iter_read_files, search and _compact_repair_payload plus the four new guarded/prefetch/reparse counterexample tests. This is trusted-repository application enforcement, not OS isolation or a TOCTOU security guarantee.",
            }
        ]
    if unit == "d6":
        contracts = [
            {
                "id": "final-channel-action-authority",
                "text": "Explorer LMStudioClient must never extract or execute actions from message.reasoning, including valid JSON and channel-marker candidates. Only existing formal content or one explicit native tool call may authorize dispatch. Reasoning-only responses use the existing one-shot empty-response repair, then fail closed; output-token-limit handling stays immediate. Do not log/replay raw reasoning snippets; metadata counts are allowed. Partition cache keys by the new final-action protocol and capability mode, so legacy reports cannot bypass the fix, without deleting history; valid current-cache reuse stays available. Preserve normal final content/native tools and read-only scope, budgets, citation and qualification gates. Inspect LMStudioClient.complete, ExplorerRuntime.__init__, and the four new reasoning/final_native/legacy_cached tests. This correction is not proof that a particular historical semantic failure came from the reasoning channel, and this archive gives no Coder credit.",
            }
        ]
    if unit == "d7":
        contracts = [
            {
                "id": "single-native-call-budget",
                "text": "Native-tool requests explicitly disable parallel_tool_calls and budget the serialized tool definitions as well as messages before HTTP. Preserve configured output reserve and safety margin. The server may ignore the flag: multiple returned calls still fail closed, without any dispatch. Text/JSON mode must not gain a tools/parallel flag or extra schema cost. Do not modify actual action scope, evidence authority, test/validation/handoff gates, model parameters, or claim tokenizer-exact estimation. Inspect LMStudioClient.complete and four focused tests. Synthetic archive: zero Coder capability credit.",
            }
        ]
    packet = {
        "schema_version": 2,
        "task_id": f"v13-scoped-{unit}-{trial}",
        "feature_id": "v13-diagnostic-state",
        "unit_id": unit,
        "run_id": f"v13-scoped-{unit}-{trial}-synthetic",
        "plan_revision": 1,
        "packet_revision": 1,
        "goal": f"Independent high-risk {unit} component audit, not Coder performance or full feature acceptance.",
        "risk": {
            "feature": "high",
            "unit": "medium" if unit == "r1" else "high",
            "integration": "high",
            "reasons": [
                "State/write/submission boundary; splitting preserves all atomic invariants"
            ],
        },
        "dependencies": [],
        "owned_contract_ids": [item["id"] for item in contracts],
        "scope": {
            "read": ["src"],
            "modify": writable,
            "create": [],
            "readonly": ["src/tests"],
            "forbidden": [".agent", ".local-agents", ".git"],
        },
        "edit_targets": [
            {
                "path": path,
                "anchor": "def complete"
                if unit in {"d6", "d7"}
                else "read_file"
                if unit == "r1"
                else "_junit_failures"
                if unit == "d2"
                else "def validate"
                if unit in {"d3", "d4", "d5"}
                else "_begin_edit"
                if path.endswith("worker-runtime.py")
                else "verify_handoff",
            }
            for path in writable
        ],
        "focused_tests": focused,
        "validation_profile": "audit-strict",
        "contract_check_required": True,
        "required_behavior": contracts,
        "required_order": [],
        "forbidden_orderings": [],
        "acceptance_criteria": [
            {
                "id": "protected",
                "text": "Focused protected tests and both registered Ruff checks execute and pass; source scope and hashes unchanged.",
            }
        ],
        "acceptance_scenarios": [
            {
                "id": "normal",
                "text": "The unit's normal, failure, boundary and compatibility counterexamples are preserved by actual execution.",
            }
        ],
    }
    targets = (
        {
            "src/reviewer-runtime.py": (
                candidate / ".local-agents/reviewer-runtime.py"
            ).read_text(encoding="utf-8")
        }
        if unit == "r1"
        else {"src/worker-runtime.py": final_worker}
    )
    if unit == "a2":
        targets["src/local-unit.py"] = (
            candidate / ".local-agents/local-unit.py"
        ).read_text(encoding="utf-8")
    if unit == "d6":
        targets = {
            "src/explorer-runtime.py": (
                candidate / ".local-agents/explorer-runtime.py"
            ).read_text(encoding="utf-8")
        }
    navigation = []
    for relative, source in targets.items():
        symbols = (
            {"complete"}
            if unit == "d7"
            else {"complete", "parse_action", "finish_success"}
            if unit == "d6"
            else A1_SYMBOLS
            if unit == "a1"
            else {"read_file", "required_reads_complete", "validate_report"}
            if unit == "r1"
            else {"validate", "_validation_facts", "_autoformat_eligible"}
            if unit == "d1"
            else {
                "_record_edit",
                "_diff_whitespace_autoformat_eligible",
                "_try_autoformat",
                "validate",
            }
            if unit == "d4"
            else {
                "_assert_read_allowed",
                "_iter_read_files",
                "search",
                "_compact_repair_payload",
            }
            if unit == "d5"
            else {
                "_contract_check",
                "_assert_submission_contract",
                "execute",
                "_record_edit",
                "validate",
                "verify_handoff",
            }
        )
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.FunctionDef) and node.name in symbols:
                navigation.append(
                    f"{relative}:{node.lineno}-{node.end_lineno} {node.name}"
                )
    packet["review_feedback"] = [
        {
            "verify_in_review": False,
            "text": "Navigation only, not proof or a verdict: "
            + "; ".join(navigation)
            + ". Review the cumulative component diff and relevant tests; when evidence is sufficient return REPORT rather than rereading unchanged ranges. Report any concrete defect or uncertainty. A1 and A2 retain high risk; neither pass accepts the whole feature.",
        }
    ]
    if unit == "d1":
        lines = final_worker.splitlines()
        start = next(
            index
            for index, line in enumerate(lines, 1)
            if "focused_gate_passed = status" in line
        )
        packet["review_feedback"].append(
            {
                "verify_in_review": False,
                "text": f"Citation navigation only, not a verdict: read src/worker-runtime.py:{start}-{start + 17}. That is a legal 18-line source_ref range for the changed diagnostic gate. Do not cite the entire validate function: each contract_review.source_ref must span at most 20 actually read lines. Read additional separate ranges for autoformat and final status preservation and explain any concrete concern. The owned obligation ID is failed-test-diagnostics-not-acceptance. Test navigation: test_failed_tests_only_run_explicit_diagnostics_with_current_nonzero_junit. No pass or verified claim is supplied by this hint.",
            }
        )
    if unit == "d6" and trial in {"2", "3"}:
        packet["review_feedback"].append(
            {
                "verify_in_review": False,
                "text": "Prior independent audit exhausted turns finding tests and submitted an overlong source_ref. No verdict is inherited. Navigation: src/explorer-runtime.py lines 502-510 cover draft-channel handling, 699-706 cover cache separation, and 477-501 cover retained final/native behavior (split citations into <=20-line ranges). Read each focused test at its named symbol. The current whole-kit regression independently passed 604 tests and 58 subtests, but this is not a supplied semantic verdict. Preserve the complete contract; cite a narrow actually read line/quote, not the entire complete function. Do not infer pass from this note.",
            }
        )
    config = json.loads(
        (candidate / ".local-agents/config.json").read_text(encoding="utf-8")
    )
    config["python"] = sys.executable
    config["validation_profiles"] = {
        "audit-strict": {
            "python": sys.executable,
            "compile": True,
            "pytest_argv": ["-B", "-m", "pytest"],
            "commands": [
                {
                    "id": "ruff-check",
                    "argv": [
                        "{python}",
                        "-m",
                        "ruff",
                        "check",
                        "--config",
                        "ruff.toml",
                        "src",
                    ],
                },
                {
                    "id": "ruff-format",
                    "argv": [
                        "{python}",
                        "-m",
                        "ruff",
                        "format",
                        "--check",
                        "--config",
                        "ruff.toml",
                        "src",
                    ],
                },
            ],
        }
    }
    shutil.copyfile(candidate / ".local-agents/ruff.toml", root / "ruff.toml")
    (root / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\npythonpath = ["."]\n', encoding="utf-8"
    )
    write(root / ".agent/packet.json", packet)
    write(root / ".agent/config.json", config)
    write(
        root / "experiment.json",
        {
            "unit": unit,
            "candidate": candidate.name,
            "baseline": before.name,
            "synthetic_archive": True,
            "derived_intermediate_not_historical_execution": True,
            "intermediate_sha256": hashlib.sha256(intermediate.encode()).hexdigest(),
            "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "source_initial_sha256": {
                p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in writable
            },
            "source_final_sha256": {
                p: hashlib.sha256(s.encode()).hexdigest() for p, s in targets.items()
            },
            "coder_credit": False,
            "capability_score": None,
        },
    )
    return root, packet, (config, targets)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "unit", choices=("a1", "a2", "r1", "d1", "d2", "d3", "d4", "d5", "d6", "d7")
    )
    parser.add_argument("--candidate", default="v13d")
    parser.add_argument("--trial", default="1")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    if not args.trial or any(
        c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in args.trial
    ):
        raise ValueError("invalid trial")
    candidate = checked_snapshot(args.candidate)
    root, packet, (config, targets) = prepare(args.unit, candidate, args.trial)
    spec = importlib.util.spec_from_file_location(
        "scoped_audit_worker", root / ".local-agents/worker-runtime.py"
    )
    worker = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = worker
    spec.loader.exec_module(worker)
    runtime = worker.WorkerRuntime(root, packet, config, None)
    runtime.write_lock.acquire()
    started = time.monotonic()
    try:
        runtime._prepare_run_archive()
        for relative, final in targets.items():
            observed = runtime.read_file({"path": relative})
            runtime.safe_replace(
                {
                    "path": relative,
                    "expected_sha256": observed["sha256"],
                    "find": (root / relative).read_text(encoding="utf-8"),
                    "replace": final,
                }
            )
        result = runtime.validate(
            {"phase": "final", "contract_check": runtime.contract_check_template()}
        )
        if result["status"] != "passed":
            write(root / "preflight-failure.json", result)
            raise ValueError("Component preflight failed; no model launched")
        if {item["id"] for item in runtime.validation.configured_checks} != {
            "ruff-check",
            "ruff-format",
        }:
            raise ValueError("Required static checks not executed")
        _, report = runtime.execute(
            {
                "action": "FINISH_SUCCESS",
                "arguments": {
                    "summary": [
                        "Primary-authored synthetic component archive, NOT a Coder success."
                    ]
                },
            }
        )
        report["synthetic_benchmark_archive"] = True
        runtime._complete_run(report)
    finally:
        runtime.close()
    request = {
        "schema_version": 1,
        "task_id": packet["task_id"],
        "unit_id": args.unit,
        "run_id": packet["run_id"],
        "review_id": "independent-component-1",
    }
    write(root / ".agent/review-request.json", request)
    if args.prepare_only:
        print(root)
        return 0
    completed = subprocess.run(
        [
            sys.executable,
            str(root / ".local-agents/local-review.py"),
            "--request",
            str(root / ".agent/review-request.json"),
            "--config",
            str(root / ".agent/config.json"),
            "--report",
            str(root / ".agent/reviewer.json"),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    write(
        root / "process-result.json",
        {
            "exit_code": completed.returncode,
            "seconds": time.monotonic() - started,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        },
    )
    print(json.dumps({"root": str(root), "exit_code": completed.returncode}))
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
