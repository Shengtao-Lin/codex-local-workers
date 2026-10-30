"""Finite repair-harness ablation. No production runtime changes or acceptance."""

import argparse
import copy
import difflib
import json
import shutil
import subprocess
import time
from pathlib import Path

import convergence_coder_schema_trial as common

KIT = common.KIT
BASE = KIT / "benchmarks/work/system-convergence/harness-comparison-20261012-1"
OLD = KIT / "benchmarks/work/system-convergence/ruff-repair-20261011-1/repeat-1/isolated"
SOURCE = common.SOURCE
OLD_RUN = OLD / ".agent/tasks/real-trace-batch-pilot/runs/real-trace-batch-pilot-ruff-repair-r1-unit-1-a1"
REPAIR = (
    "Repair the observed Ruff E501 at src/evaluation_harness/trace_sources/mlflow.py:84:101 "
    "(159 > 100). Keep all existing behavior and protected tests unchanged. "
    "All original behavior, Ruff format/check and strict Pyright checks remain required."
)
PATCH_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {key: {"type": "string"} for key in ("path", "expected_sha256", "find", "replace")},
    "required": ["path", "expected_sha256", "find", "replace"],
}


def save(path, value):
    common.save(path, value)


def runtime_module(root):
    return common.load("comparison_runtime", root / ".local-agents/worker-runtime.py")


def checkpoint():
    BASE.mkdir(parents=True, exist_ok=False)
    listed = subprocess.run(["git", "ls-files", "-c", "-o", "--exclude-standard"], cwd=KIT,
                            check=True, capture_output=True, text=True).stdout.splitlines()
    paths = {KIT / p for p in listed if (KIT / p).is_file()}
    paths.add(KIT / ".local-agents/config.json")
    paths.update(p for p in common.files(BASE.parent) if not p.is_relative_to(BASE))
    siblings = {}
    for name in ("agent-runtime-kit", "agent-evaluation-harness"):
        sibling = KIT.parent / name
        for directory in ("src", "tests", ".agent", ".local-agents", "docs"):
            paths.update(common.files(sibling / directory))
        paths.update(p for p in (sibling / "AGENTS.md", sibling / "pyproject.toml") if p.is_file())
        siblings[name] = {
            flag: subprocess.run(["git", "-C", str(sibling), *argv], check=True,
                                 capture_output=True, text=True).stdout
            for flag, argv in {"head": ["rev-parse", "HEAD"], "status": ["status", "--short"]}.items()
        }
    save(BASE / "baseline.json", {str(p): common.sha(p) for p in sorted(paths)})
    save(BASE / "authorization.json", {
        "weekly_used_start": 11, "weekly_used_ceiling": 15, "fixed_repeats_per_arm": 3,
        "order": ["simple-1", "full-1", "full-2", "simple-2", "simple-3", "full-3"],
        "feature_id": "harness-repair-comparison", "unit_risk": "high",
        "feature_risk": "high", "integration_risk": "high", "dependencies": [],
        "owned_contract_ids": ["sequential-trace-batch"],
        "risk_rationale": "Frozen cancellation/order/legacy invariants; Primary retains classification.",
        "repair_request": REPAIR, "models_config_tests_contracts": "identical",
        "comparison": "Fresh repair contexts, same E501 failed source, not old full-history continuation.",
        "simple": "One exact/hash/scoped block-patch proposal per attempt; host executes unchanged checks; at most initial plus two repair proposals. No model VALIDATE/FINISH actions.",
        "full": "Unmodified current WorkerRuntime loop/schema/prompt/budgets, identical initial evidence supplied as a fresh user repair context.",
        "decision": "simple 3/3 and full <3/3: prioritize interface simplification; both 3/3: historical state/context suspect; both <3/3: no qualified candidate; no general model incapacity claim",
        "reviewer": "Not invoked: ablation of Coder repair, never product acceptance or chain qualification.",
        "single_model_residency": True, "commit_push": False,
        "siblings": siblings, "cloud_tokens": None, "Primary_active_seconds": None,
    })
    print("pinned", len(paths), "prior files", flush=True)


def setup():
    assert (BASE / "baseline.json").exists()
    packet = common.read(OLD_RUN / "packet.json")
    config = common.read(OLD / ".agent/config.json")
    assert common.sha(OLD / SOURCE) == "53a07351d7b381c318868446de5ef702e8bfb0070bddb81e1518eaa464874738"
    registration = {}
    for arm in ("simple", "full"):
        for index in range(1, 4):
            case = BASE / f"{arm}-{index}"
            root = case / "isolated"
            root.mkdir(parents=True, exist_ok=False)
            for path in common.files(OLD / ".local-agents"):
                target = root / path.relative_to(OLD)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
            for directory in ("src", "tests"):
                shutil.copytree(OLD / directory, root / directory,
                                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            shutil.copyfile(OLD / "pyproject.toml", root / "pyproject.toml")
            fresh = copy.deepcopy(packet)
            fresh["run_id"] = f"harness-comparison-{arm}-{index}-unit-1-a1"
            save(root / ".agent/packet.json", fresh)
            save(root / ".agent/config.json", config)
            initial = {
                "repair_request": REPAIR, "path": SOURCE, "sha256": common.sha(root / SOURCE),
                "source": (root / SOURCE).read_text(encoding="utf-8"),
                "contract": packet["required_behavior"],
                "acceptance_scenarios": packet["acceptance_scenarios"],
                "read_only_context": {p: (root / p).read_text(encoding="utf-8")
                                      for p in packet["scope"]["readonly"]},
            }
            save(case / "initial-evidence.json", initial)
            registration[case.name] = {str(p.relative_to(root)): common.sha(p)
                                       for p in common.files(root)}
    save(BASE / "freeze.json", {
        "cases": registration, "driver_sha256": common.sha(Path(__file__)),
        "repair_schema": PATCH_SCHEMA, "production_candidate_unchanged": True,
    })
    print("six independent failed-source copies frozen", flush=True)


def apply_patch_proposal(module, root, proposal):
    if not isinstance(proposal, dict) or set(proposal) != set(PATCH_SCHEMA["required"]):
        raise ValueError("Expected exactly path, expected_sha256, find, replace")
    if any(not isinstance(value, str) for value in proposal.values()):
        raise ValueError("Patch fields must all be strings")
    if proposal["find"] == proposal["replace"]:
        raise ValueError("Unchanged replacement is not a repair")
    editor = module.SAFE_EDIT.SafeEditor(root, allowed_modify=[SOURCE], allowed_create=[])
    return editor.replace(proposal["path"], proposal["find"], proposal["replace"],
                          expected_sha256=proposal["expected_sha256"])


def checks(case, name):
    root = case / "isolated"
    results = []
    commands = [
        ["-m", "pytest", "-q", "-p", "no:cacheprovider", "tests", "--junitxml", str(case / f"{name}.xml")],
        ["-m", "ruff", "format", "--check", "src", "tests"],
        ["-m", "ruff", "check", "src", "tests"],
        ["-m", "pyright", "--pythonpath", str(common.PYTHON)],
    ]
    for argv in commands:
        start = time.monotonic()
        result = subprocess.run([str(common.PYTHON), "-B", *argv], cwd=root, env=common.ENV,
                                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
        results.append({"argv": argv, "exit": result.returncode, "stdout": result.stdout,
                        "stderr": result.stderr, "seconds": time.monotonic() - start})
    save(case / f"{name}.json", results)
    return results


def run(arm, index):
    case = BASE / f"{arm}-{index}"
    root = case / "isolated"
    freeze = common.read(BASE / "freeze.json")
    assert common.sha(Path(__file__)) == freeze["driver_sha256"]
    for path, digest in freeze["cases"][case.name].items():
        assert common.sha(root / path) == digest, path
    assert not (case / "result.json").exists()
    baseline = checks(case, "baseline-checks")
    assert [r["exit"] for r in baseline] == [0, 0, 1, 0]
    assert "E501" in baseline[2]["stdout"]
    module = runtime_module(root)
    config = common.read(root / ".agent/config.json")
    evidence = common.read(case / "initial-evidence.json")
    evidence["actual_checks"] = baseline
    context = json.dumps(evidence, ensure_ascii=False)
    count = 0

    class Recorder(module.LMStudioClient):
        def complete(self, messages):
            nonlocal count
            count += 1
            if arm == "full" and count == 1:
                messages = [*messages, {"role": "user", "content": "FRESH_REPAIR_CONTEXT\n" + context}]
            save(case / f"request-{count}.json", {"messages": messages, "action_schema": self.action_schema})
            started = time.monotonic()
            try:
                response = super().complete(messages)
            except Exception as exc:
                save(case / f"response-{count}-error.json", {"error": str(exc), "type": type(exc).__name__})
                raise
            save(case / f"response-{count}.json", {"content": response, "stats": self.last_request_stats,
                                                   "seconds": time.monotonic() - started})
            return response

    client = Recorder(config["lmstudio_base_url"], config["coder_model"],
                      config["model_request_timeout_seconds"], max_tokens=config["coder_max_tokens"],
                      temperature=config["coder_temperature"], top_p=config["coder_top_p"],
                      top_k=config["coder_top_k"], min_p=config["coder_min_p"],
                      repeat_penalty=config["coder_repeat_penalty"], structured_output=True,
                      action_schema=PATCH_SCHEMA if arm == "simple" else None,
                      context_length=config["coder_context_length"],
                      context_safety_margin=config["model_context_safety_margin"],
                      typed_action_arguments=config["coder_typed_action_arguments"] if arm == "full" else False)
    started = time.monotonic()
    report = {}
    with module.MODEL_RESIDENCY.role_model_lease(client, config):
        client.preflight()
        if arm == "full":
            runtime = module.WorkerRuntime(root, common.read(root / ".agent/packet.json"), config, client)
            runtime.preflight()
            report = runtime.run()
            save(case / "coder-report.json", report)
        else:
            lock = module.RepoWriteLock(root, f"simple-comparison-{index}")
            lock.acquire()
            try:
                messages = [
                    {"role": "system", "content": "Repair the provided source. Return one JSON exact block replacement with path, expected_sha256, find, replace. No shell or other file writes. Preserve the supplied contract and protected tests."},
                    {"role": "user", "content": context},
                ]
                for attempt in range(1, 4):
                    response = client.complete(messages)
                    try:
                        applied = apply_patch_proposal(module, root, json.loads(response))
                        observed = checks(case, f"attempt-{attempt}-checks")
                        feedback = {"edit": applied, "checks": observed}
                        save(case / f"edit-{attempt}.json", feedback)
                        if all(item["exit"] == 0 for item in observed):
                            break
                    except (ValueError, module.SafeEditError) as exc:
                        feedback = {"error": str(exc)}
                        save(case / f"edit-{attempt}-rejected.json", feedback)
                    feedback["current_sha256"] = common.sha(root / SOURCE)
                    feedback["current_source"] = (root / SOURCE).read_text(encoding="utf-8")
                    messages += [{"role": "assistant", "content": response},
                                 {"role": "user", "content": json.dumps(feedback, ensure_ascii=False)}]
            finally:
                lock.release()
    final = checks(case, "independent-final-checks")
    unchanged = all(common.sha(root / path) == digest
                    for path, digest in freeze["cases"][case.name].items()
                    if path != SOURCE)
    before = evidence["source"]
    after = (root / SOURCE).read_text(encoding="utf-8")
    diff = "".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                       fromfile="failed-source", tofile="final-source"))
    save(case / "result.json", {
        "arm": arm, "repeat": index, "model_calls": count,
        "seconds": time.monotonic() - started, "protected_inputs_unchanged": unchanged,
        "all_checks_passed": all(r["exit"] == 0 for r in final),
        "effective_repair": unchanged and bool(diff) and all(r["exit"] == 0 for r in final),
        "runtime_status": report.get("status"), "runtime_failure": report.get("failure_reason"),
        "diff": diff, "final_sha256": common.sha(root / SOURCE),
        "reviewer_calls": 0, "acceptance": "not evaluated", "cloud_tokens": None,
    })
    print(case.name, "effective repair", common.read(case / "result.json")["effective_repair"],
          "calls", count, flush=True)


def audit():
    changed = [path for path, digest in common.read(BASE / "baseline.json").items()
               if not Path(path).is_file() or common.sha(Path(path)) != digest]
    results = {case.name: common.read(case / "result.json") for case in BASE.iterdir()
               if case.is_dir() and (case / "result.json").exists()}
    save(BASE / "decision.json", {"results": results, "prior_files_changed": changed,
                                  "product_release": False, "reviewer_assessed": False})
    print(json.dumps({"results": {key: value["effective_repair"] for key, value in results.items()},
                      "prior_files_changed": changed}, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["checkpoint", "setup", "run", "audit"])
    parser.add_argument("--arm", choices=["simple", "full"])
    parser.add_argument("--repeat", type=int, choices=[1, 2, 3])
    args = parser.parse_args()
    if args.action == "run":
        run(args.arm, args.repeat)
    else:
        globals()[args.action]()
