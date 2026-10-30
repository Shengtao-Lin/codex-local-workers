"""Unseen semantic and multi-file task transfer of the selected minimal JSON editor."""

import argparse
import ast
import copy
import difflib
import hashlib
import json
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import repair_context_factorial as screen

common = screen.common
KIT = common.KIT
BASE = screen.BASE / "transfer"
FIXTURE = KIT / "benchmarks/fixtures/repair-transfer-v1"
SIBLING = KIT.parent / "agent-evaluation-harness"
PREFIX = "src/evaluation_harness/"
SCORERS = PREFIX + "scorers/deterministic.py"
DEDUP = PREFIX + "evaluations/dedup.py"
FILES = ["__init__.py", "canonical/__init__.py", "canonical/models.py", "contracts.py",
         "errors.py", "scorers/__init__.py", "scorers/base.py", "scorers/deterministic.py",
         "scorers/registry.py", "scorers/judge.py", "evaluations/__init__.py", "evaluations/dedup.py"]
TASKS = {
    "presence": {
        "goal": "Change OutputPresentScorer.score so it passes iff at least one TextPart with non-whitespace text appears in any assistant-role message in sample.output_messages. Ignore non-text parts and non-assistant messages. Empty/all-blank/non-text-only output fails. Preserve the sample without mutation, async signature, succeeded status, 1.0/pass versus 0.0/fail results, and appropriate rationale. Other scorers, imports, class metadata and methods are unchanged. This is an isolated feature trial, not deployment.",
        "targets": {SCORERS: ["OutputPresentScorer.score"]},
        "tests": "test_output_presence.py", "expected_tests": 9,
        "dependencies": "CanonicalSample.output_messages is a list of CanonicalMessage(role, content). content is a list of TextPart(text), JsonPart, ToolCallPart or ToolResultPart. TextPart and ScoreResult are already imported. A TextPart may contain whitespace. Role can be system/user/assistant/tool.",
    },
    "keyword-reuse": {
        "goal": "Apply identical reference-fact normalization across ExpectedKeywordScorer.score and score_reuse_key for scorer_id expected-keywords: trim leading/trailing whitespace and discard resulting empty facts; preserve remaining order, duplicates and casing. Scoring uses those facts for matching and denominator, existing Unicode casefold matching, and existing result/rationale semantics. No remaining facts means skipped. Reuse identity must equal the existing schema_version=1 legacy hash for the same sample with only expectations.reference_facts replaced by that normalized list. Normalize only expected-keywords, only when expectations exists; absent expectations remains distinct from present empty facts. Other scorer identities stay byte-compatible. Preserve all other sample/scorer/config fields and identity invalidation, sample_id exclusion, non-cacheable and judge rejection, original signatures, imports and metadata. Do not mutate sample/expectations/reference_facts or scorer/config. Both scoring and key generation must work together on exact input forms; this is one unit spanning two source files, not separate fixes. Isolated trial only.",
        "targets": {SCORERS: ["ExpectedKeywordScorer.score"], DEDUP: ["score_reuse_key"]},
        "tests": "test_keyword_reuse.py", "expected_tests": 15,
        "dependencies": "CanonicalSample.expectations is Expectations(reference_facts: list[str]) or None. sample.model_dump(mode='json', exclude={'sample_id'}) returns a fresh dict with expectations None or a dict containing reference_facts. Scorer exposes scorer_id/version/scorer_type/contract; contract includes cacheable/scorer_type. ScoreResult is a Pydantic model. All names used by the current functions are already imported. JSON serialization/hash settings must be preserved.",
    },
}


def symbol_span(source, symbol):
    tree = ast.parse(source)
    parts = symbol.split(".")
    body = tree.body
    if len(parts) == 2:
        owners = [n for n in body if isinstance(n, ast.ClassDef) and n.name == parts[0]]
        if len(owners) != 1:
            raise ValueError("Target owner must be unique")
        body = owners[0].body
    nodes = [n for n in body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == parts[-1]]
    if len(nodes) != 1:
        raise ValueError("Target symbol must be unique")
    node = nodes[0]
    start = min([node.lineno, *[n.lineno for n in node.decorator_list]]) - 1
    return node, start, node.end_lineno, "".join(source.splitlines(True)[start:node.end_lineno])


def apply(module, root, targets, response, observed, guard=lambda: None):
    proposal = json.loads(response)
    if not isinstance(proposal, dict) or set(proposal) != set(screen.previous.PATCH_SCHEMA["required"]):
        raise ValueError("Expected path, expected_sha256, find, replace")
    if any(not isinstance(value, str) for value in proposal.values()):
        raise ValueError("All patch fields must be strings")
    path = proposal["path"].replace("\\", "/")
    if path not in targets:
        raise ValueError("File outside writable target scope")
    if common.sha(root / path) != observed[path]:
        raise ValueError("Current source changed during inference")
    source = (root / path).read_text(encoding="utf-8")
    find, replacement = proposal["find"].replace("\r\n", "\n"), proposal["replace"].replace("\r\n", "\n")
    if not find or find == replacement:
        raise ValueError("Empty or no-op replacement")
    matched = [(symbol, symbol_span(source, symbol)) for symbol in targets[path]
               if symbol_span(source, symbol)[3].count(find) == 1]
    if len(matched) != 1:
        raise ValueError("Find must match exactly one authorized target function")
    symbol, (node, _, _, block) = matched[0]
    screen.checked_method(block.replace(find, replacement, 1), node)
    symbol_span(source.replace(find, replacement, 1), symbol)
    editor = module.SAFE_EDIT.SafeEditor(root, allowed_modify=targets, allowed_create=[], mutation_guard=guard)
    return editor.replace(path, find, replacement, expected_sha256=proposal["expected_sha256"])


def setup():
    decision = common.read(screen.BASE / "screen-decision.json")
    assert decision["arms"]["minimal-json"]["passed"] == 3
    BASE.mkdir(exist_ok=False)
    original = BASE / "original"
    provenance = {}
    for path in [PREFIX + name for name in FILES] + ["pyproject.toml"]:
        target = original / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SIBLING / path, target)
        provenance[path] = {"origin": str(SIBLING / path), "sha256": common.sha(target)}
    for path in FIXTURE.glob("*.py"):
        target = BASE / "frozen-tests" / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    common.save(BASE / "provenance.json", provenance)
    snapshots = {}
    config = common.read(screen.OLD / ".agent/config.json")
    legacy = common.load("transfer_legacy", FIXTURE / "test_legacy_structure.py")
    for task, details in TASKS.items():
        for repeat in (1, 2):
            name = f"{task}-{repeat}"
            root = BASE / name / "isolated"
            shutil.copytree(original, root)
            shutil.copytree(screen.OLD / ".local-agents", root / ".local-agents",
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            for test in ("conftest.py", details["tests"], "test_legacy_structure.py"):
                destination = root / "tests" / test
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(FIXTURE / test, destination)
            (root / "tests/test_definition_uniqueness.py").write_text(screen.GUARD, encoding="utf-8")
            common.save(root / "tests/legacy_structure.json", {
                path: {"allowed": symbols, "ast": legacy.masked_ast((root / path).read_text(encoding="utf-8"), symbols)}
                for path, symbols in details["targets"].items()
            })
            packet = copy.deepcopy(common.read(screen.previous.OLD_RUN / "packet.json"))
            packet.update({"task_id": "repair-transfer-" + task, "feature_id": "repair-transfer-" + task,
                           "run_id": name, "goal": details["goal"], "owned_contract_ids": [task],
                           "primary_plan_sha256": hashlib.sha256(json.dumps(details, sort_keys=True).encode()).hexdigest(),
                           "required_behavior": [{"id": task, "text": details["goal"], "risk_floor": "high"}],
                           "acceptance_criteria": [{"id": task, "text": details["goal"]}],
                           "acceptance_scenarios": [{"id": name, "text": text, "observables": {"tests": details["tests"]}}
                               for name, text in [("normal", "Correct scoring and any required cross-file identity agreement"),
                                                  ("error", "Unsafe/nonmatching/non-text inputs preserve rejection or failure semantics"),
                                                  ("boundary", "Empty/whitespace/duplicate/absent values and input immutability")]],
                           "focused_tests": ["tests/" + details["tests"], "tests/test_legacy_structure.py", "tests/test_definition_uniqueness.py"],
                           "scope": {"read": ["src", "tests", "pyproject.toml"], "modify": list(details["targets"]), "create": [],
                                     "readonly": ["tests", "pyproject.toml"], "forbidden": [".agent", ".local-agents", ".git"]},
                           "edit_targets": [{"path": path, "anchor": symbol.split(".")[-1]} for path, symbols in details["targets"].items() for symbol in symbols],
                           "implementation_guidance": [], "review_feedback": []})
            packet["risk"]["reasons"] = ["Primary: scoring and reuse identity are a public compatibility boundary; cross-file contract remains one high-risk unit."]
            common.save(root / ".agent/packet.json", packet)
            common.save(root / ".agent/config.json", config)
            snapshots[name] = {p.relative_to(root).as_posix(): common.sha(p) for p in common.files(root)}
    common.save(BASE / "freeze.json", {"cases": snapshots, "driver_sha256": common.sha(Path(__file__)),
                                       "screen_driver_sha256": common.sha(KIT / "benchmarks/repair_context_factorial.py"),
                                       "tasks": TASKS, "order": ["presence-1", "keyword-reuse-1", "keyword-reuse-2", "presence-2"],
                                       "max_proposals_per_unit": 3, "selected_arm": "minimal-json",
                                       "selection_basis": "3/3 first-pass arms; equal calls; minimal-json 2649 input tokens vs minimal-code 2655 and full-json 19035. Two tokens/request is not a practical superiority claim.",
                                       "qualification": "4/4 independent all-checks pass with protected inputs unchanged; no external rework. This is editing/semantic transfer only, not Reviewer/Coordinator or product qualification.",
                                       "extension": "Same JSON output/client/sampling and target-function guard; authorize multiple named functions/files in one cohesive unit, without new model actions.",
                                       "weekly_used_ceiling": 30, "brothers_readonly": True, "commit_push": False})
    print("Four fresh real-slice transfer cases frozen", flush=True)


def checks(case, name, expected):
    values = screen.previous.checks(case, name)
    junit = ET.parse(case / f"{name}.xml").getroot()
    count = len(junit.findall(".//testcase"))
    valid = count == expected and not any(junit.findall(".//" + tag) for tag in ("failure", "error", "skipped"))
    return values, valid, count


def run(name):
    freeze = common.read(BASE / "freeze.json")
    assert common.sha(Path(__file__)) == freeze["driver_sha256"]
    assert common.sha(KIT / "benchmarks/repair_context_factorial.py") == freeze["screen_driver_sha256"]
    root = BASE / name / "isolated"
    case = root.parent
    task = name.rsplit("-", 1)[0]
    details = freeze["tasks"][task]
    for path, digest in freeze["cases"][name].items():
        assert common.sha(root / path) == digest, path
    common.save(case / "started.json", {"time": time.time()})
    baseline, _, count = checks(case, "baseline", details["expected_tests"])
    assert count == details["expected_tests"] and baseline[0]["exit"] == 1
    assert [r["exit"] for r in baseline[1:]] == [0, 0, 0]
    module = screen.previous.runtime_module(root)
    config = common.read(root / ".agent/config.json")
    packet = common.read(root / ".agent/packet.json")
    module.validate_packet(packet)
    client = module.LMStudioClient(config["lmstudio_base_url"], config["coder_model"], config["model_request_timeout_seconds"],
        max_tokens=config["coder_max_tokens"], temperature=config["coder_temperature"], top_p=config["coder_top_p"],
        top_k=config["coder_top_k"], min_p=config["coder_min_p"], repeat_penalty=config["coder_repeat_penalty"],
        context_length=config["coder_context_length"], context_safety_margin=config["model_context_safety_margin"],
        structured_output=True, action_schema=screen.previous.PATCH_SCHEMA)
    before = {path: (root / path).read_text(encoding="utf-8") for path in details["targets"]}
    prior = None
    feedback = {"validation": baseline[0]["stdout"][:6000]}
    attempts = []
    started = time.monotonic()
    with module.MODEL_RESIDENCY.role_model_lease(client, config):
        client.preflight()
        lock = module.RepoWriteLock(root, "transfer-" + name)
        lock.acquire()
        try:
            for number in range(1, 4):
                observed = {path: common.sha(root / path) for path in details["targets"]}
                current = {"current_task": details["goal"], "hard_contract_to_preserve": packet["required_behavior"],
                           "acceptance_scenarios": packet["acceptance_scenarios"], "dependencies": details["dependencies"],
                           "targets": [{"path": path, "qualified_symbol": symbol, "sha256": observed[path],
                                        "target_source": symbol_span((root / path).read_text(encoding="utf-8"), symbol)[3]}
                                       for path, symbols in details["targets"].items() for symbol in symbols]}
                messages = [{"role": "system", "content": "Implement the supplied change in existing target functions. Preserve the hard contract and change only listed target functions. Return one JSON exact block replacement with path, expected_sha256, find, replace. Use the supplied current hash and exact target-source block. Multiple files belong to the same unit; after each edit all tests/checks run and you may repair remaining failures within the call budget."},
                            {"role": "user", "content": json.dumps(current, ensure_ascii=False)}]
                if prior is not None:
                    messages.append({"role": "assistant", "content": prior})
                messages.append({"role": "user", "content": "LAST_ATTEMPT_RESULT\n" + json.dumps(feedback, ensure_ascii=False)})
                common.save(case / f"request-{number}.json", {"messages": messages, "schema": screen.previous.PATCH_SCHEMA})
                response = client.complete(messages)
                common.save(case / f"response-{number}.json", {"content": response, "stats": client.last_request_stats})
                result = {"number": number, "applied": False, "passed": False}
                try:
                    result["edit"] = apply(module, root, details["targets"], response, observed, lock.assert_owned)
                    result["applied"] = True
                    observed_checks, valid, _ = checks(case, f"validation-{number}", details["expected_tests"])
                    result["passed"] = valid and all(r["exit"] == 0 for r in observed_checks)
                    feedback = {"checks": [{"argv": r["argv"], "exit": r["exit"], "output": r["stdout"][:6000]} for r in observed_checks]}
                except (ValueError, SyntaxError, module.SafeEditError) as exc:
                    result["error"] = str(exc)
                    feedback = {"edit_rejected": str(exc)}
                common.save(case / f"proposal-{number}.json", result)
                attempts.append(result)
                if result["passed"]:
                    break
                prior = response
        finally:
            lock.release()
    final, valid, count = checks(case, "independent-final", details["expected_tests"])
    protected = [path for path, digest in freeze["cases"][name].items()
                 if path not in details["targets"] and common.sha(root / path) != digest]
    diffs = {path: "".join(difflib.unified_diff(old.splitlines(True), (root / path).read_text(encoding="utf-8").splitlines(True)))
             for path, old in before.items()}
    passed = valid and all(r["exit"] == 0 for r in final) and not protected and all(diffs.values())
    common.save(case / "result.json", {"case": name, "passed": passed, "model_calls": len(attempts),
        "attempts": attempts, "check_exits": [r["exit"] for r in final], "test_count": count,
        "protected_changes": protected, "diffs": diffs, "seconds": time.monotonic() - started,
        "reviewer_calls": 0, "product_release": False})
    print(name, "PASS" if passed else "FAIL", "calls", len(attempts), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["setup", "run"])
    parser.add_argument("--case")
    args = parser.parse_args()
    if args.action == "setup":
        setup()
    else:
        run(args.case)
