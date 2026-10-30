"""Frozen 2x2 context/output repair comparison; isolated from production runtime."""

import argparse
import ast
import copy
import difflib
import json
import shutil
import subprocess
import textwrap
import time
from pathlib import Path

import convergence_coder_schema_trial as common
import harness_repair_comparison as previous

KIT = common.KIT
BASE = KIT / "benchmarks/work/system-convergence/harness-factorial-20261012-1"
OLD = previous.OLD
SOURCE = previous.SOURCE
SYMBOL = "MlflowTraceSource.get_many"
REQUEST = (
    "Repair the existing MlflowTraceSource.get_many implementation's Ruff E501 "
    "at line 84 column 101: the docstring is 159 characters; the limit is 100. "
    "The method already exists and its behavior tests pass. Preserve its behavior "
    "and signature. Only this method may change. All original behavior tests, "
    "Ruff formatting/lint, strict Pyright and duplicate-definition protection must pass."
)
ARMS = ("minimal-code", "minimal-json", "full-code", "full-json")
ORDER = ["minimal-code-1", "full-json-1", "minimal-json-1", "full-code-1",
         "full-code-2", "minimal-json-2", "full-json-2", "minimal-code-2",
         "full-json-3", "minimal-code-3", "full-code-3", "minimal-json-3"]
GUARD = '''"""Protect method uniqueness independently of dict-based legacy snapshots."""

import ast
from collections import Counter
from pathlib import Path


def test_no_duplicate_function_or_method_definitions() -> None:
    for path in Path("src").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for scope in ast.walk(tree):
            if isinstance(scope, (ast.Module, ast.ClassDef)):
                names = [
                    item.name
                    for item in scope.body
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                assert all(count == 1 for count in Counter(names).values()), str(path)
'''


def save(path, value):
    common.save(path, value)


def method_span(source, symbol=SYMBOL):
    owner, name = symbol.split(".")
    tree = ast.parse(source)
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == owner]
    if len(classes) != 1:
        raise ValueError("Expected exactly one target class")
    nodes = [n for n in classes[0].body
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    if len(nodes) != 1:
        raise ValueError("Expected exactly one target method")
    node = nodes[0]
    start = min([node.lineno, *[d.lineno for d in node.decorator_list]])
    lines = source.splitlines(keepends=True)
    return node, start - 1, node.end_lineno, "".join(lines[start - 1:node.end_lineno])


def code_body(response):
    text = response.strip("\r\n")
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0] not in {"```python", "```"} or lines[-1] != "```":
            raise ValueError("Expected one Python code block without surrounding prose")
        text = "\n".join(lines[1:-1])
    return textwrap.dedent(text).rstrip() + "\n"


def checked_method(code, original):
    normalized = code_body(code)
    tree = ast.parse(normalized)
    if len(tree.body) != 1 or not isinstance(tree.body[0], type(original)):
        raise ValueError("Response must contain exactly the target function, no extra definitions/statements")
    node = tree.body[0]
    if node.name != original.name or ast.dump(node.args) != ast.dump(original.args):
        raise ValueError("Target method name/parameters must remain unchanged")
    if ast.dump(node.returns) != ast.dump(original.returns):
        raise ValueError("Return annotation must remain unchanged")
    if [ast.dump(n) for n in node.decorator_list] != [ast.dump(n) for n in original.decorator_list]:
        raise ValueError("Decorators must remain unchanged")
    return textwrap.indent(normalized, " " * original.col_offset)


def apply_proposal(module, root, output_format, response, observed_sha, guard=lambda: None):
    editor = module.SAFE_EDIT.SafeEditor(root, allowed_modify=[SOURCE], allowed_create=[],
                                        mutation_guard=guard)
    raw, current_sha = editor.read_bytes(SOURCE)
    if current_sha != observed_sha:
        raise ValueError("Source changed during inference")
    original_source = raw.decode("utf-8").replace("\r\n", "\n")
    node, _, _, block = method_span(original_source)
    if output_format == "code":
        replacement = checked_method(response, node)
        find = block
        expected_sha = observed_sha
    else:
        proposal = json.loads(response)
        if not isinstance(proposal, dict) or set(proposal) != set(previous.PATCH_SCHEMA["required"]):
            raise ValueError("Expected path, expected_sha256, find, replace")
        if any(not isinstance(value, str) for value in proposal.values()):
            raise ValueError("Patch fields must be strings")
        if proposal["path"].replace("\\", "/") != SOURCE:
            raise ValueError("Path is outside target scope")
        find = proposal["find"].replace("\r\n", "\n")
        replacement = proposal["replace"].replace("\r\n", "\n")
        if not find or block.count(find) != 1:
            raise ValueError("Find must uniquely match inside the target method")
        checked_method(block.replace(find, replacement), node)
        expected_sha = proposal["expected_sha256"]
    if find == replacement:
        raise ValueError("No-op replacement")
    method_span(original_source.replace(find, replacement, 1))
    return editor.replace(SOURCE, find, replacement, expected_sha256=expected_sha)


def messages_for(root, context_size, output_format, feedback=None, previous_response=None):
    source = (root / SOURCE).read_text(encoding="utf-8")
    packet = common.read(root / ".agent/packet.json")
    _, _, _, block = method_span(source)
    current = {
        "current_task": REQUEST,
        "hard_contract_to_preserve": packet["required_behavior"],
        "acceptance_scenarios": packet["acceptance_scenarios"],
        "path": SOURCE, "qualified_symbol": SYMBOL, "sha256": common.sha(root / SOURCE),
        "target_source": block,
        "dependencies": "self.get(id) is async and returns SourceTrace; preserve returned object identity.",
    }
    if context_size == "full":
        current["full_source"] = source
        current["readonly_context"] = {p: (root / p).read_text(encoding="utf-8")
                                       for p in packet["scope"]["readonly"]}
    output = (
        "Return only the complete corrected async get_many function as Python code, optionally in one Python fence. Do not output the class, neighboring functions, JSON, or prose."
        if output_format == "code" else
        "Return one JSON exact block replacement with path, expected_sha256, find, replace. Use the supplied current hash and an exact target-source block."
    )
    messages = [
        {"role": "system", "content": "Repair the supplied existing method. Preserve its contract and change only this method. " + output},
        {"role": "user", "content": json.dumps(current, ensure_ascii=False)},
    ]
    if previous_response is not None:
        messages.append({"role": "assistant", "content": previous_response})
    if feedback is not None:
        messages.append({"role": "user", "content": "LAST_ATTEMPT_RESULT\n" + json.dumps(feedback, ensure_ascii=False)})
    assert REQUEST in messages[1]["content"]
    return messages


def checkpoint():
    BASE.mkdir(parents=True, exist_ok=False)
    listed = subprocess.run(["git", "ls-files", "-c", "-o", "--exclude-standard"], cwd=KIT,
                            check=True, capture_output=True, text=True).stdout.splitlines()
    paths = {KIT / p for p in listed if (KIT / p).is_file()}
    paths.update(p for p in common.files(BASE.parent) if not p.is_relative_to(BASE))
    paths.add(KIT / ".local-agents/config.json")
    states = {}
    for name in ("agent-evaluation-harness", "agent-runtime-kit"):
        sibling = KIT.parent / name
        for folder in ("src", "tests", "docs", ".agent", ".local-agents"):
            paths.update(common.files(sibling / folder))
        paths.update(p for p in (sibling / "AGENTS.md", sibling / "pyproject.toml") if p.is_file())
        states[name] = {label: subprocess.run(["git", "-C", str(sibling), *args], check=True,
                                              capture_output=True, text=True).stdout
                        for label, args in {"head": ["rev-parse", "HEAD"], "status": ["status", "--short"]}.items()}
    save(BASE / "baseline.json", {str(p): common.sha(p) for p in sorted(paths)})
    save(BASE / "authorization.json", {
        "weekly_used_start": 13, "weekly_used_ceiling": 30,
        "feature_id": "repair-context-factorial", "feature_risk": "high", "unit_risk": "high",
        "integration_risk": "high", "owned_contract_ids": ["sequential-trace-batch"],
        "dependencies": [], "risk_rationale": "Preserve ordering/cancellation invariants and evaluate untrusted code editing.",
        "arms": ARMS, "fixed_order": ORDER, "repeats_per_arm": 3, "max_proposals_per_case": 3,
        "qualified_screen": "3/3 independently pass all checks, no protected-input changes. Select by first-attempt passes then fewer calls, then lower input tokens. Tie favors minimal-code.",
        "transfer_condition": "At least one 3/3 arm; then freeze two unseen small semantic/multifile tasks and test each twice. No tuning after live.",
        "fixed_factors": "Same source preimage, behavior contracts/tests, added duplicate guard, model/sampling/context limit, target method scope, host validation and budgets.",
        "varied_factors": "Input: method plus complete contract vs same plus full source/read-only context. Output: raw function vs strict JSON exact replacement.",
        "historical_correction": "Old full arm dropped first-request repair context; old 0/3 results retained but not a fair comparative causal estimate. Original packet goal was stale. Old path metric correction remains separate.",
        "reviewer": "Not evaluated by this Coder experiment; successful checks do not authorize product acceptance.",
        "single_model_residency": True, "model": "qwen/qwen3-coder-30b", "production_runtime_edits": False,
        "siblings": states, "brothers_readonly": True, "commit_push": False,
    })
    print("baseline pinned", len(paths), flush=True)


def setup():
    packet = common.read(previous.OLD_RUN / "packet.json")
    config = common.read(OLD / ".agent/config.json")
    assert common.sha(OLD / SOURCE) == "53a07351d7b381c318868446de5ef702e8bfb0070bddb81e1518eaa464874738"
    registration = {}
    for name in ORDER:
        root = BASE / name / "isolated"
        root.mkdir(parents=True, exist_ok=False)
        for directory in (".local-agents", "src", "tests"):
            shutil.copytree(OLD / directory, root / directory,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copyfile(OLD / "pyproject.toml", root / "pyproject.toml")
        (root / "tests/test_definition_uniqueness.py").write_text(GUARD, encoding="utf-8")
        fresh = copy.deepcopy(packet)
        fresh["run_id"] = "factorial-" + name
        fresh["goal"] = REQUEST
        fresh["focused_tests"].append("tests/test_definition_uniqueness.py")
        fresh["scope"]["readonly"].append("tests/test_definition_uniqueness.py")
        # Contract semantics retained; clarify the established feature is not a new task.
        for item in fresh["required_behavior"]:
            item["text"] = "Preserve the already implemented feature: " + item["text"]
        save(root / ".agent/packet.json", fresh)
        save(root / ".agent/config.json", config)
        registration[name] = {p.relative_to(root).as_posix(): common.sha(p) for p in common.files(root)}
    save(BASE / "freeze.json", {"cases": registration, "driver_sha256": common.sha(Path(__file__)),
                                "guard_sha256": common.sha(BASE / ORDER[0] / "isolated/tests/test_definition_uniqueness.py")})
    print("12 cases prepared and frozen", flush=True)


def checks(case, name):
    results = previous.checks(case, name)
    import xml.etree.ElementTree as ET
    tree = ET.parse(case / f"{name}.xml").getroot()
    tests = tree.findall(".//testcase")
    valid_tests = len(tests) == 11 and not any(tree.findall(".//" + tag) for tag in ("failure", "error", "skipped"))
    return results, valid_tests


def run(name):
    assert name in ORDER
    case = BASE / name
    root = case / "isolated"
    freeze = common.read(BASE / "freeze.json")
    assert common.sha(Path(__file__)) == freeze["driver_sha256"]
    for relative, digest in freeze["cases"][name].items():
        assert common.sha(root / relative) == digest, relative
    assert not (case / "started.json").exists()
    save(case / "started.json", {"case": name, "time": time.time()})
    baseline, tests_valid = checks(case, "baseline")
    assert tests_valid and [r["exit"] for r in baseline] == [0, 0, 1, 0]
    context_size, output_format, _ = name.split("-")
    module = previous.runtime_module(root)
    config = common.read(root / ".agent/config.json")
    client = module.LMStudioClient(
        config["lmstudio_base_url"], config["coder_model"], config["model_request_timeout_seconds"],
        max_tokens=config["coder_max_tokens"], temperature=config["coder_temperature"],
        top_p=config["coder_top_p"], top_k=config["coder_top_k"], min_p=config["coder_min_p"],
        repeat_penalty=config["coder_repeat_penalty"], context_length=config["coder_context_length"],
        context_safety_margin=config["model_context_safety_margin"],
        structured_output=output_format == "json", action_schema=previous.PATCH_SCHEMA,
    )
    attempts = []
    prior = None
    feedback = {"check_id": "ruff-check", "output": baseline[2]["stdout"]}
    initial = (root / SOURCE).read_text(encoding="utf-8")
    started = time.monotonic()
    with module.MODEL_RESIDENCY.role_model_lease(client, config):
        client.preflight()
        lock = module.RepoWriteLock(root, "factorial-" + name)
        lock.acquire()
        try:
            for number in range(1, 4):
                messages = messages_for(root, context_size, output_format, feedback, prior)
                observed = common.sha(root / SOURCE)
                save(case / f"request-{number}.json", {"messages": messages, "schema": previous.PATCH_SCHEMA if output_format == "json" else None,
                                                       "current_source_sha256": observed, "task_persisted": True})
                response = client.complete(messages)
                save(case / f"response-{number}.json", {"content": response, "stats": client.last_request_stats})
                row = {"attempt": number, "applied": False, "passed": False}
                try:
                    row["edit"] = apply_proposal(module, root, output_format, response, observed, lock.assert_owned)
                    row["applied"] = True
                    results, tests_valid = checks(case, f"attempt-{number}")
                    row["passed"] = tests_valid and all(r["exit"] == 0 for r in results)
                    feedback = {"checks": [{"argv": r["argv"], "exit": r["exit"], "output": r["stdout"][:6000]} for r in results]}
                except (ValueError, SyntaxError, module.SafeEditError) as exc:
                    row["error"] = str(exc)
                    feedback = {"edit_rejected": str(exc)}
                save(case / f"attempt-{number}.json", row)
                attempts.append(row)
                if row["passed"]:
                    break
                prior = response
        finally:
            lock.release()
    final, valid_tests = checks(case, "independent-final")
    changed_protected = [p for p, h in freeze["cases"][name].items()
                         if p != SOURCE and common.sha(root / p) != h]
    after = (root / SOURCE).read_text(encoding="utf-8")
    passed = valid_tests and all(r["exit"] == 0 for r in final) and not changed_protected and initial != after
    result = {"case": name, "passed": passed, "first_attempt_passed": attempts[0]["passed"],
              "calls": len(attempts), "attempts": attempts, "check_exits": [r["exit"] for r in final],
              "protected_changes": changed_protected, "source_sha256": common.sha(root / SOURCE),
              "diff": "".join(difflib.unified_diff(initial.splitlines(True), after.splitlines(True))),
              "seconds": time.monotonic() - started, "reviewer_calls": 0, "product_acceptance": False}
    save(case / "result.json", result)
    print(name, "PASS" if passed else "FAIL", "calls", len(attempts), flush=True)


def audit():
    results = {name: common.read(BASE / name / "result.json") for name in ORDER}
    changed = [p for p, h in common.read(BASE / "baseline.json").items()
               if not Path(p).is_file() or common.sha(Path(p)) != h]
    summary = {arm: {"passed": sum(results[f"{arm}-{i}"]["passed"] for i in range(1, 4)),
                     "first_passed": sum(results[f"{arm}-{i}"]["first_attempt_passed"] for i in range(1, 4)),
                     "calls": sum(results[f"{arm}-{i}"]["calls"] for i in range(1, 4))}
               for arm in ARMS}
    save(BASE / "screen-decision.json", {"arms": summary, "prior_files_changed": changed,
                                        "qualified_arms": [a for a in ARMS if summary[a]["passed"] == 3],
                                        "product_release": False})
    print(json.dumps(summary, indent=2), "prior changed", len(changed), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["checkpoint", "setup", "run", "audit"])
    parser.add_argument("--case", choices=ORDER)
    args = parser.parse_args()
    if args.action == "run":
        run(args.case)
    else:
        globals()[args.action]()
