"""Explicit-root R1 continuation and fixed matched-input R2 diagnostic."""

from __future__ import annotations

import argparse
import difflib
import importlib.util
import json
import os
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

import harness_convergence as base

PYTHON = base.KIT / "benchmarks/work/stability-v1/.venv-diagnostics/Scripts/python.exe"
FIXTURE_PYTHON = base.KIT.parent / "agent-evaluation-harness/.venv/Scripts/python.exe"
DEPENDENCIES = (
    "self.get(id) is async and returns SourceTrace; preserve returned object identity."
)
REPAIR_GOAL = (
    "Repair the existing MlflowTraceSource.get_many function's observed Ruff E501. "
    "Its current behavior tests pass. Preserve all existing behavior and its signature. "
    "Only this function may change. All protected behavior tests, Ruff formatting/lint, "
    "strict Pyright and duplicate-definition protection must pass."
)


def load_runtime():
    spec = importlib.util.spec_from_file_location(
        "matched_r2_runtime", base.KIT / ".local-agents/worker-runtime.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def prepare(batch, usage):
    base.prepare(batch, usage)
    base.save(
        batch / "r1-repair-authorization.json",
        {
            "user_request": "Continue; complete R1 controls then execute the plan step by step",
            "production_modify": [".local-agents/single-function-context.py"],
            "risk": "high",
            "risk_rationale": "Preserve exact-match editing authority across newline representations",
            "preimage": "checkpoint/.local-agents/single-function-context.py",
            "historical_hold": "../r0-r2-20261013-1/decision.json",
            "contract_and_handoff_unchanged": True,
            "r3_authorized": False,
        },
    )


def checks(root, output, label):
    commands = [
        [
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests",
            "--junitxml",
            str(output / f"{label}.xml"),
        ],
        ["-m", "ruff", "format", "--check", "src", "tests"],
        ["-m", "ruff", "check", "src", "tests"],
        ["-m", "pyright", "--pythonpath", str(FIXTURE_PYTHON)],
    ]
    rows = []
    for args in commands:
        started = time.monotonic()
        result = subprocess.run(
            [str(FIXTURE_PYTHON), "-B", *args],
            cwd=root,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
        rows.append(
            {
                "argv": args,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "seconds": time.monotonic() - started,
            }
        )
    tree = ET.parse(output / f"{label}.xml")
    tests = tree.findall(".//testcase")
    valid = len(tests) == 11 and not any(
        tree.findall(".//" + tag) for tag in ("failure", "error", "skipped")
    )
    value = {
        "checks": rows,
        "junit": {"executed": len(tests), "all_behavior_pass": valid},
    }
    base.save(output / f"{label}.json", value)
    return value


def repair_context(root, evidence):
    packet = base.read(root / ".agent/packet.json")
    source = (root / base.SOURCE).read_text(encoding="utf-8-sig")
    return {
        "goal": REPAIR_GOAL,
        "required_behavior": packet["required_behavior"],
        "required_order": packet["required_order"],
        "forbidden_orderings": packet["forbidden_orderings"],
        "acceptance_scenarios": packet["acceptance_scenarios"],
        "target": {
            "path": base.SOURCE,
            "symbol": base.SYMBOL,
            "sha256": base.sha(root / base.SOURCE),
            "source": base.method(source),
            "dependencies": DEPENDENCIES,
        },
        "validation_failure": {
            "check_id": "ruff-check",
            "exit_code": evidence["checks"][2]["exit_code"],
            "output": evidence["checks"][2]["stdout"],
            "source_sha256": base.sha(root / base.SOURCE),
        },
    }


def messages_for(root, arm, evidence):
    current = repair_context(root, evidence)
    if arm == "formal":
        module = load_runtime()
        packet = base.read(root / ".agent/packet.json")
        packet["goal"] = REPAIR_GOAL
        config = base.read(root / ".agent/config.json")
        client = module.LMStudioClient("http://fixture.invalid/v1", "fixture-model", 1)
        instance = module.WorkerRuntime(root, packet, config, client)
        instance.validation = module.ValidationResult(
            "failed",
            {"status": "passed"},
            {
                "status": "passed",
                "exit_code": 0,
                "junit": {"available": True, "executed": 11},
            },
            configured_checks=[
                {
                    "id": check_id,
                    "status": "passed" if row["exit_code"] == 0 else "failed",
                    "exit_code": row["exit_code"],
                    "output": row["stdout"],
                }
                for check_id, row in zip(
                    ("ruff-format", "ruff-check", "pyright"), evidence["checks"][1:]
                )
            ],
        )
        focus = instance._validation_repair_focus(instance.validation)[0]
        # Render the production post-failure context without claiming a real edit
        # or fabricating a canonical validation archive. R2 is a diagnostic only.
        with patch.object(instance, "_required_repair_focus", return_value=focus):
            rendered = module.SINGLE_FUNCTION.patch_messages(instance, [])
        failure = json.loads(rendered[-1]["content"].split("\n", 1)[1])
        body = json.loads(rendered[1]["content"])
        body["current_validation_failure"] = failure
        body["validation_failure"] = current["validation_failure"]
        return [
            {"role": "system", "content": module.SINGLE_FUNCTION.PATCH_PROMPT},
            {"role": "user", "content": json.dumps(body, ensure_ascii=False)},
        ]
    elif arm != "minimal":
        raise ValueError("Unknown context arm")
    return [
        {"role": "system", "content": load_runtime().SINGLE_FUNCTION.PATCH_PROMPT},
        {"role": "user", "content": json.dumps(current, ensure_ascii=False)},
    ]


def apply_proposal(module, root, response, observed, lock):
    action = module.SINGLE_FUNCTION.patch_action(response)
    if action["action"] != "SAFE_REPLACE":
        return {"status": "blocked", "reason": action["arguments"]["reason"]}
    args = action["arguments"]
    editor = module.SAFE_EDIT.SafeEditor(
        root,
        allowed_modify=[base.SOURCE],
        allowed_create=[],
        mutation_guard=lock.assert_owned,
    )
    raw, current = editor.read_bytes(base.SOURCE)
    if current != observed or args["expected_sha256"] != observed:
        raise ValueError("Source changed or proposal hash is stale")
    if args["find"].replace("\r\n", "\n").replace("\r", "\n") == args[
        "replace"
    ].replace("\r\n", "\n").replace("\r", "\n"):
        raise ValueError("No-op replacement")
    module.SINGLE_FUNCTION.guard(
        {"path": base.SOURCE, "symbol": base.SYMBOL}, raw.decode("utf-8-sig"), args
    )
    return {
        "status": "applied",
        "edit": editor.replace(
            **{
                "raw_path": args["path"],
                "find": args["find"],
                "replacement": args["replace"],
                "expected_sha256": args["expected_sha256"],
            }
        ),
    }


def freeze_live(batch):
    replay = ET.parse(batch / "r1-controls.xml")
    if any(replay.findall(".//" + tag) for tag in ("failure", "error", "skipped")):
        raise ValueError("R1 controls have not passed")
    snapshot_evidence = {}
    for snapshot, case in (
        ("original", "original-minimal-1"),
        ("failed-draft", "failed-draft-formal-1"),
    ):
        output = batch / "baseline-checks" / snapshot
        output.mkdir(parents=True)
        facts = checks(batch / "cases" / case / "isolated", output, "baseline")
        if not facts["junit"]["all_behavior_pass"] or [
            r["exit_code"] for r in facts["checks"]
        ] != [0, 0, 1, 0]:
            raise ValueError(f"Unexpected baseline checks for {snapshot}")
        snapshot_evidence[snapshot] = facts
    runtime = load_runtime()
    order = base.read(batch / "registration.json")["order"]
    for name in order:
        root = batch / "cases" / name / "isolated"
        snapshot = "failed-draft" if name.startswith("failed-draft") else "original"
        arm = "formal" if "-formal-" in name else "minimal"
        messages = messages_for(root, arm, snapshot_evidence[snapshot])
        base.save(
            batch / "cases" / name / "rendered-request.json",
            {
                "messages": messages,
                "schema": runtime.SINGLE_FUNCTION.PATCH_SCHEMA,
                "current_source_sha256": base.sha(root / base.SOURCE),
                "arm": arm,
                "snapshot": snapshot,
            },
        )
    base.save(
        batch / "live-freeze.json",
        {
            "runtime": {
                str(p.relative_to(base.KIT)): base.sha(p)
                for p in base.files(base.KIT / ".local-agents")
            },
            "drivers": {
                str(p.relative_to(base.KIT)): base.sha(p)
                for p in (
                    Path(__file__),
                    base.KIT / "benchmarks/harness_convergence.py",
                )
            },
            "tests": base.sha(base.KIT / "tests/test_harness_convergence_replay.py"),
            "order": order,
            "baseline_checks": snapshot_evidence,
            "calls_per_cell": 1,
            "all_check_gate": "648-character draft 3/3 in at least one context",
            "r3_authorized": False,
        },
    )


def run(batch, name):
    frozen = base.read(batch / "live-freeze-approved.json")
    if name not in frozen["order"]:
        raise ValueError("Unregistered cell")
    for path, digest in {**frozen["runtime"], **frozen["drivers"]}.items():
        if base.sha(base.KIT / path) != digest:
            raise ValueError(f"Frozen file drift: {path}")
    case = batch / "cases" / name
    root = case / "isolated"
    for path, digest in base.read(batch / "freeze.json")["cases"][name].items():
        if base.sha(root / path) != digest:
            raise ValueError(f"Frozen input drift: {path}")
    base.save(case / "started.json", {"case": name, "time": time.time()})
    rendered = base.read(case / "rendered-request.json")
    module = load_runtime()
    config = base.read(root / ".agent/config.json")
    client = module.LMStudioClient(
        config["lmstudio_base_url"],
        config["coder_model"],
        config["model_request_timeout_seconds"],
        max_tokens=config["coder_max_tokens"],
        temperature=config["coder_temperature"],
        top_p=config["coder_top_p"],
        top_k=config["coder_top_k"],
        min_p=config["coder_min_p"],
        repeat_penalty=config["coder_repeat_penalty"],
        context_length=config["coder_context_length"],
        context_safety_margin=config["model_context_safety_margin"],
        structured_output=True,
        action_schema=module.SINGLE_FUNCTION.PATCH_SCHEMA,
        typed_action_arguments=False,
    )
    actual_requests = []
    original_urlopen = urllib.request.urlopen

    def record_request(request, *args, **kwargs):
        if (
            isinstance(request, urllib.request.Request)
            and request.get_method() == "POST"
        ):
            if actual_requests:
                raise RuntimeError(
                    "One physical completion request per cell; automatic retry forbidden"
                )
            payload = json.loads(request.data)
            actual_requests.append(payload)
            base.save(
                case / "request.json",
                {
                    "url": request.full_url,
                    "method": "POST",
                    "body": payload,
                    "request_sha256": __import__("hashlib")
                    .sha256(request.data)
                    .hexdigest(),
                },
            )
        return original_urlopen(request, *args, **kwargs)

    before = (root / base.SOURCE).read_text(encoding="utf-8-sig")
    started = time.monotonic()
    outcome = {
        "case": name,
        "applied": False,
        "parse_pass": False,
        "all_check_pass": False,
        "reviewer_calls": 0,
        "product_acceptance": False,
    }
    with module.MODEL_RESIDENCY.role_model_lease(client, config):
        client.preflight()
        lock = module.RepoWriteLock(root, "matched-r2-" + name)
        lock.acquire()
        try:
            try:
                with patch.object(
                    urllib.request, "urlopen", side_effect=record_request
                ):
                    response = client.complete(rendered["messages"])
            except Exception as exc:
                base.save(
                    case / "response-error.json",
                    {
                        "type": type(exc).__name__,
                        "error": str(exc),
                        "model_calls": len(actual_requests),
                        "stats": client.last_request_stats,
                    },
                )
                raise
            base.save(
                case / "response.json",
                {"content": response, "stats": client.last_request_stats},
            )
            try:
                module.SINGLE_FUNCTION.patch_action(response)
                outcome["parse_pass"] = True
                proposal = apply_proposal(
                    module, root, response, rendered["current_source_sha256"], lock
                )
                base.save(case / "proposal.json", proposal)
                outcome["applied"] = proposal["status"] == "applied"
                outcome["terminal"] = proposal["status"]
            except (ValueError, SyntaxError, module.SafeEditError) as exc:
                outcome.update(terminal="rejected", error=str(exc))
                base.save(
                    case / "proposal.json", {"status": "rejected", "error": str(exc)}
                )
            facts = checks(root, case, "independent-final")
            outcome["behavior_pass"] = facts["junit"]["all_behavior_pass"]
            outcome["check_exits"] = [r["exit_code"] for r in facts["checks"]]
            outcome["protected_changes"] = [
                p
                for p, h in base.read(batch / "freeze.json")["cases"][name].items()
                if p != base.SOURCE and base.sha(root / p) != h
            ]
            outcome["all_check_pass"] = (
                outcome["applied"]
                and outcome["behavior_pass"]
                and all(r["exit_code"] == 0 for r in facts["checks"])
                and not outcome["protected_changes"]
            )
        finally:
            lock.release()
    after = (root / base.SOURCE).read_text(encoding="utf-8-sig")
    outcome.update(
        model_calls=len(actual_requests),
        source_sha256=base.sha(root / base.SOURCE),
        seconds=time.monotonic() - started,
    )
    with (case / "diff.patch").open("x", encoding="utf-8") as handle:
        handle.write(
            "".join(
                difflib.unified_diff(before.splitlines(True), after.splitlines(True))
            )
        )
    base.save(case / "result.json", outcome)
    print(json.dumps(outcome, ensure_ascii=False), flush=True)


def finalize_freeze(batch):
    if list((batch / "cases").glob("*/started.json")):
        raise ValueError("Cannot amend a freeze after any live attempt")
    frozen = base.read(batch / "live-freeze.json")
    frozen["drivers"] = {
        str(p.relative_to(base.KIT)): base.sha(p)
        for p in (Path(__file__), base.KIT / "benchmarks/harness_convergence.py")
    }
    frozen["pre_live_amendment"] = (
        "Preserve transport-error evidence before exiting; zero live calls so far. Original live-freeze retained."
    )
    base.save(batch / "live-freeze-approved.json", frozen)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "freeze", "finalize", "run"])
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--usage", type=int, default=2)
    parser.add_argument("--case")
    args = parser.parse_args()
    batch = args.batch.resolve()
    if args.action == "prepare":
        prepare(batch, args.usage)
    elif args.action == "freeze":
        freeze_live(batch)
    elif args.action == "finalize":
        finalize_freeze(batch)
    else:
        run(batch, args.case)
