"""Reversible load-time FA diagnostic. No saved preferences or defaults edited."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.request
from pathlib import Path

import layer_isolation as LAYER
import mixed_feature_benchmark as MIXED
import output_form_comparison as FORM
from capability_fit import KIT, WORK, load_worker, write
from inherited_context_recovery import digest, read
from layer_isolation_cases import corpus

BASE = WORK / "roleq-flash-attention-1"
SNAPSHOT = WORK / "roleq-fa-baseline-1"
MODEL = "qwen/qwen3-coder-30b"
NATIVE = "http://127.0.0.1:12345/api/v1/models"
LMS = "C:/Users/Lin/.lmstudio/bin/lms.exe"
PHASES = ("on-r1", "off-r1", "on-r2", "off-r2", "restored-on")
LOAD_KEYS = (
    "context_length",
    "eval_batch_size",
    "flash_attention",
    "num_experts",
    "offload_kv_cache_to_gpu",
)
DRIVERS = [
    Path(__file__),
    Path(FORM.__file__),
    Path(LAYER.__file__),
    Path(MIXED.__file__),
    KIT / "benchmarks/layer_isolation_cases.py",
    KIT / "benchmarks/capability_fit.py",
    KIT / "benchmarks/inherited_context_recovery.py",
]


def api(suffix="", body=None):
    req = urllib.request.Request(
        NATIVE + suffix,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="GET" if body is None else "POST",
    )
    with urllib.request.urlopen(req, timeout=600 if body else 30) as response:
        return json.load(response)


def instance(inventory):
    loaded = [
        (model["key"], item)
        for model in inventory["models"]
        for item in model["loaded_instances"]
    ]
    if len(loaded) != 1 or loaded[0][0] != MODEL or loaded[0][1]["id"] != MODEL:
        raise ValueError("expected only original Qwen instance; refuse foreign unload")
    return loaded[0][1]


def require_config(actual, original, enabled):
    expected = dict(original, flash_attention=enabled)
    if actual != expected:
        differences = sorted(
            key
            for key in actual.keys() | expected.keys()
            if actual.get(key) != expected.get(key)
        )
        raise ValueError("load config drift: " + ", ".join(differences))


def reload_model(original, enabled, directory, label):
    """Call under the kit's exclusive role lease. At most the target is unloaded."""
    current = instance(api())
    write(directory / f"{label}-before.json", current)
    status = subprocess.run(
        [LMS, "ps", "--json"], capture_output=True, text=True, check=True, timeout=30
    )
    models = json.loads(status.stdout)
    if (
        len(models) != 1
        or models[0]["identifier"] != MODEL
        or models[0]["status"] != "idle"
        or models[0]["queued"] != 0
    ):
        raise ValueError("model busy/foreign; do not unload")
    write(directory / f"{label}-unload-intent.json", {"instance_id": MODEL})
    unloaded = api("/unload", {"instance_id": MODEL})
    write(directory / f"{label}-unloaded.json", unloaded)
    if unloaded.get("instance_id") != MODEL:
        raise ValueError("unload not confirmed")
    if any(m["loaded_instances"] for m in api()["models"]):
        raise ValueError("a model appeared after unload; refuse overlapping load")
    body = {
        "model": MODEL,
        "echo_load_config": True,
        **{key: original[key] for key in LOAD_KEYS},
    }
    body["flash_attention"] = enabled
    write(directory / f"{label}-load-request.json", body)
    started = time.monotonic()
    print(json.dumps({"loading": label, "flash_attention": enabled}), flush=True)
    result = api("/load", body)
    write(
        directory / f"{label}-load-response.json",
        {"response": result, "seconds": time.monotonic() - started},
    )
    if result.get("status") != "loaded":
        raise ValueError("load not confirmed")
    loaded = instance(api())
    write(directory / f"{label}-after.json", loaded)
    require_config(loaded["config"], original, enabled)


def restore_model(original, directory):
    """Restore even if the candidate load failed and left no resident instance."""
    inventory = api()
    loaded = [
        item for model in inventory["models"] for item in model["loaded_instances"]
    ]
    if not loaded:
        body = {
            "model": MODEL,
            "echo_load_config": True,
            **{key: original[key] for key in LOAD_KEYS},
        }
        write(directory / "restore-empty-request.json", body)
        response = api("/load", body)
        write(directory / "restore-empty-response.json", response)
    else:
        current = instance(inventory)
        if current["config"] != original:
            reload_model(original, original["flash_attention"], directory, "restore")
    current = instance(api())
    require_config(current["config"], original, original["flash_attention"])
    write(directory / "restoration.json", {"restored": True, "instance": current})


def prepare():
    BASE.mkdir(exist_ok=False)
    LAYER.verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    original = instance(api())
    if original["config"]["flash_attention"] is not True:
        raise ValueError("expected original FA on")
    write(BASE / "original-instance.json", original)
    engine = subprocess.run(
        [LMS, "runtime", "ls"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
        timeout=30,
    )
    write(
        BASE / "selected-engine.json",
        {
            "output": engine.stdout,
            "note": "Selected installation, not independent process build identity",
        },
    )
    template = read(KIT / "benchmarks/fixtures/mixed-features-v1.json")["cases"][0]
    data, _ = corpus(template)
    data["cases"] = [
        c for c in data["cases"] if c["case_id"] in ("exact-count", "missing-label")
    ]
    write(BASE / "corpus.json", data)
    MIXED.CORPUS, MIXED.WORK = BASE / "corpus.json", BASE / "runs"
    cells = []
    for phase in PHASES:
        for case in data["cases"]:
            root = Path(
                MIXED.prepare(
                    case["case_id"],
                    1,
                    SNAPSHOT / ".local-agents/config.json",
                    "fa-" + phase,
                )["root"]
            )
            files = [
                *case["files"],
                "pyproject.toml",
                ".agent/config.json",
                ".agent/qual-unit-reference.json",
            ]
            cells.append(
                {
                    "id": f"{phase}-{case['case_id']}",
                    "phase": phase,
                    "case": case["case_id"],
                    "root": str(root),
                    "hashes": {p: digest(root / p) for p in files},
                }
            )
    for driver in DRIVERS:
        dest = BASE / "drivers" / driver.relative_to(KIT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(driver.read_bytes())
    write(
        BASE / "manifest.json",
        {
            "feature_id": "serving-fa-isolation",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "contracts": [
                "single-residency",
                "restore-original-load-config",
                "immutable-evidence",
                "no-qualification-credit",
            ],
            "risk_rationale": "Temporary load setting change and model-code validation; no production defaults or saved preferences edited",
            "original": original,
            "phases": PHASES,
            "cells": cells,
            "snapshot": str(SNAPSHOT),
            "drivers": {str(p): digest(p) for p in DRIVERS},
            "corpus_sha256": digest(BASE / "corpus.json"),
            "calls_max": 15,
            "calls_per_phase": 3,
            "retries": 0,
            "weekly_used_start": 50,
            "weekly_used_ceiling": 60,
            "micro_question": "In Python 3: class Child(int): pass. For each x in [2, True, Child(2)], give the boolean value of type(x) is int. Return only the three-element JSON array.",
            "micro_expected": [True, False, False],
            "decision": "on/off each twice, then restored-on once. Benefit requires off correct in both repeats while on fails, without visible config drift; otherwise no promotion. Stop on infrastructure error. Every phase finally verifies original settings.",
            "limits": "Only inventory-visible load config is compared; hidden KV precision/template/engine internals are not exposed by this endpoint. Reload/cache effects not fully isolated. Prior four-case reference/mutant preflight reused only after fixture hash checks.",
            "qualification_credit": False,
        },
    )
    # Fixtures must exactly match the previously executed reference/mutant cohort.
    prior = read(WORK / "roleq-output-form-1/manifest.json")
    for cell in cells:
        old = next(c for c in prior["cells"] if c["case"] == cell["case"])
        for p, sha in cell["hashes"].items():
            if not p.startswith(".agent/") and old["hashes"][p] != sha:
                raise ValueError("prior fixture proof no longer applies")
    write(
        BASE / "preflight-reuse.json",
        {
            "verified": True,
            "source": str(WORK / "roleq-output-form-1/preflight.json"),
            "sha256": digest(WORK / "roleq-output-form-1/preflight.json"),
        },
    )
    print(json.dumps({"prepared": len(cells), "calls": 15}), flush=True)


def implementation(cell, client, worker):
    root = Path(cell["root"])
    LAYER.verify_hashes(root, cell["hashes"])
    packet, config = (
        read(root / ".agent/qual-unit-reference.json"),
        read(root / ".agent/config.json"),
    )
    messages = [
        {"role": "system", "content": FORM.output_instruction("python")},
        {
            "role": "user",
            "content": json.dumps(FORM.payload(root, cell), ensure_ascii=False),
        },
    ]
    write(root / ".agent/request.json", messages)
    raw = client.complete(messages)
    write(
        root / ".agent/response.json", {"raw": raw, "stats": client.last_request_stats}
    )
    outcome = {
        "cell": cell["id"],
        "semantic_evaluated": False,
        "semantic_pass": None,
        "error": None,
    }
    runtime = None
    try:
        patch, fence = FORM.decode_output(raw, "python", packet["scope"]["modify"])
        outcome["fence_removed"] = fence
        for item in patch:
            compile(item["content"], item["path"], "exec")
        runtime = worker.WorkerRuntime(root, packet, config, None)
        runtime.write_lock.acquire()
        runtime._prepare_run_archive()
        for item in patch:
            observed = runtime.read_file({"path": item["path"]})
            runtime.safe_replace(
                {
                    "path": item["path"],
                    "expected_sha256": observed["sha256"],
                    "find": (root / item["path"]).read_text(encoding="utf-8"),
                    "replace": item["content"],
                }
            )
        checks = LAYER.check(root, "independent")
        LAYER.verify_hashes(
            root,
            {
                p: sha
                for p, sha in cell["hashes"].items()
                if p not in packet["scope"]["modify"]
            },
        )
        outcome.update(
            semantic_evaluated=True,
            semantic_pass=checks["semantic_pass"],
            validation=checks,
        )
    except (ValueError, SyntaxError) as error:
        outcome["error"] = str(error)
    finally:
        if runtime:
            runtime.close()
    write(BASE / f"{cell['id']}-result.json", outcome)
    print(
        json.dumps(
            {
                k: outcome[k]
                for k in ("cell", "semantic_evaluated", "semantic_pass", "error")
            }
        ),
        flush=True,
    )


def phase_run(phase):
    manifest = read(BASE / "manifest.json")
    if phase not in PHASES:
        raise ValueError("unregistered phase")
    for previous in PHASES[: PHASES.index(phase)]:
        if not read(BASE / previous / "phase-result.json")["completed"]:
            raise ValueError("previous phase failed")
    for p, sha in manifest["drivers"].items():
        if digest(Path(p)) != sha:
            raise ValueError("driver drift")
    LAYER.verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    LAYER.verify_hashes(BASE, {"corpus.json": manifest["corpus_sha256"]})
    if read(BASE / "preflight-reuse.json")["verified"] is not True:
        raise ValueError("fixture evidence missing")
    directory = BASE / phase
    directory.mkdir(exist_ok=False)
    config = read(SNAPSHOT / ".local-agents/config.json")
    worker = load_worker(SNAPSHOT)
    client = worker.LMStudioClient(
        config["lmstudio_base_url"],
        MODEL,
        config["model_request_timeout_seconds"],
        max_tokens=config["coder_max_tokens"],
        temperature=config["coder_temperature"],
        top_p=config["coder_top_p"],
        top_k=config["coder_top_k"],
        min_p=config["coder_min_p"],
        repeat_penalty=config["coder_repeat_penalty"],
        structured_output=False,
        context_length=config["coder_context_length"],
    )
    original = manifest["original"]["config"]
    result = {"phase": phase, "completed": False, "error": None, "restored": False}
    with worker.MODEL_RESIDENCY.role_model_lease(client, config):
        require_config(instance(api())["config"], original, True)
        try:
            enabled = not phase.startswith("off")
            if not enabled:
                reload_model(original, False, directory, "candidate")
            require_config(instance(api())["config"], original, enabled)
            for cell in manifest["cells"]:
                if cell["phase"] == phase:
                    require_config(instance(api())["config"], original, enabled)
                    implementation(cell, client, worker)
            messages = [
                {
                    "role": "system",
                    "content": "Answer the Python question accurately. Return only the requested JSON array, no prose or Markdown.",
                },
                {"role": "user", "content": manifest["micro_question"]},
            ]
            raw = client.complete(messages)
            correct = False
            try:
                correct = json.dumps(json.loads(raw)) == json.dumps(
                    manifest["micro_expected"]
                )
            except ValueError:
                pass
            write(
                directory / "micro.json",
                {
                    "messages": messages,
                    "raw": raw,
                    "correct": correct,
                    "stats": client.last_request_stats,
                },
            )
            result["completed"] = True
        except Exception as error:  # noqa: BLE001 -- restore first, retain failure
            result["error"] = f"{type(error).__name__}: {error}"
        finally:
            try:
                restore_model(original, directory)
                result["restored"] = True
            except Exception as error:  # noqa: BLE001 -- restoration failure must be visible
                result["restore_error"] = f"{type(error).__name__}: {error}"
            write(directory / "phase-result.json", result)
    print(json.dumps(result), flush=True)
    if not result["completed"] or not result["restored"]:
        raise RuntimeError(
            "phase incomplete; inspect immutable result before proceeding"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", *PHASES))
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    else:
        phase_run(args.action)
