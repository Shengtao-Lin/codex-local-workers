"""Frozen three-model direct screen; no role qualification or production changes."""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import flash_attention_comparison as FA
from capability_fit import KIT, WORK, freeze, load_worker, write
from inherited_context_recovery import digest, read
from layer_isolation_followup import strengthened_corpus

BASE = WORK / "coder-model-screen-1"
SNAPSHOT = WORK / "coder-model-screen-baseline-1"
MODELS = [
    "qwen/qwen3-coder-30b",
    "qwen3-coder-30b-a3b-instruct-i1",
    "mistralai/devstral-small-2-2512",
]
PREFS = Path("C:/Users/Lin/.lmstudio/.internal/user-concrete-model-default-config")
PREF_PATHS = [
    PREFS / "qwen/qwen3-coder-30b.json",
    PREFS
    / "mradermacher/Qwen3-Coder-30B-A3B-Instruct-i1-GGUF/Qwen3-Coder-30B-A3B-Instruct.i1-IQ4_XS.gguf.json",
    PREFS / "mistralai/devstral-small-2-2512.json",
]


def residents():
    return json.loads(
        subprocess.check_output([FA.LMS, "ps", "--json"], text=True, encoding="utf-8")
    )


def guard_residents(items, target=None):
    if len(items) > 1 or any(
        x["identifier"] not in MODELS or x["status"] != "idle" or x["queued"] != 0
        for x in items
    ):
        raise ValueError("busy/foreign/multiple model; refuse switch")
    if target is not None and (len(items) != 1 or items[0]["identifier"] != target):
        raise ValueError("target not exclusively resident")


def loaded_config(model):
    items = [(m["key"], i) for m in FA.api()["models"] for i in m["loaded_instances"]]
    if len(items) != 1 or items[0][0] != model:
        raise ValueError("single-model invariant")
    conf = items[0][1]["config"]
    if (
        conf.get("context_length") != 24576
        or conf.get("parallel") != 1
        or conf.get("flash_attention") is not True
    ):
        raise ValueError("context/parallel/FA mismatch")
    return items[0][1]


def prepare():
    BASE.mkdir(exist_ok=False)
    guard_residents(residents())
    freeze(SNAPSHOT.name)
    write(BASE / "inventory.json", FA.api())
    prefs = {}
    for path in PREF_PATHS:
        obj = read(path)
        fields = {x["key"]: x["value"] for x in obj["load"]["fields"]}
        for name, value in (("k", "q8_0"), ("v", "f16")):
            if fields.get(f"llm.load.llama.{name}CacheQuantizationType") != {
                "checked": True,
                "value": value,
            }:
                raise ValueError("saved KV setting mismatch")
        prefs[str(path)] = digest(path)
    write(BASE / "saved-preferences.json", {str(p): read(p) for p in PREF_PATHS})
    data, oracles = strengthened_corpus(
        read(KIT / "benchmarks/fixtures/mixed-features-v1.json")["cases"][0]
    )
    write(BASE / "corpus.json", data)
    FA.MIXED.CORPUS, FA.MIXED.WORK = BASE / "corpus.json", BASE / "preflight"
    proofs = []
    for case in data["cases"]:
        name = case["case_id"]
        root = Path(
            FA.MIXED.prepare(name, 1, SNAPSHOT / ".local-agents/config.json", "pre")[
                "root"
            ]
        )
        mutants = []
        for n, files in enumerate(oracles[name]["mutants"]):
            for p, content in files.items():
                (root / p).write_text(content, encoding="utf-8")
            mutants.append(FA.LAYER.check(root, f"mutant-{n}"))
        for p, content in oracles[name]["reference"].items():
            (root / p).write_text(content, encoding="utf-8")
        FA.LAYER.command(root, [sys.executable, "-m", "ruff", "format", "src"])
        proof = {
            "case": name,
            "reference": FA.LAYER.check(root, "reference"),
            "mutants": mutants,
        }
        proofs.append(proof)
    write(BASE / "preflight.json", proofs)
    if not all(
        p["reference"]["all_checks_pass"]
        and all(not m["semantic_pass"] for m in p["mutants"])
        for p in proofs
    ):
        raise ValueError("preflight failed")
    FA.MIXED.WORK = BASE / "runs"
    cells = []
    for index, model in enumerate(MODELS):
        for case in data["cases"]:
            root = Path(
                FA.MIXED.prepare(
                    case["case_id"],
                    1,
                    SNAPSHOT / ".local-agents/config.json",
                    f"model-{index}",
                )["root"]
            )
            paths = [
                *case["files"],
                "pyproject.toml",
                ".agent/config.json",
                ".agent/qual-unit-reference.json",
            ]
            cells.append(
                {
                    "id": f"m{index}-{case['case_id']}",
                    "model": model,
                    "root": str(root),
                    "case": case["case_id"],
                    "hashes": {p: digest(root / p) for p in paths},
                }
            )
    drivers = list(
        dict.fromkeys(
            [
                Path(__file__).resolve(),
                Path(sys.modules[strengthened_corpus.__module__].__file__),
                *FA.DRIVERS,
            ]
        )
    )
    write(
        BASE / "manifest.json",
        {
            "feature_id": "three-coder-direct-screen",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "risk_rationale": "Temporary authorized model switching and execution of generated code in trusted fixtures",
            "contracts": [
                "single-residency",
                "immutable-evidence",
                "protected-tests",
                "no-production-change",
            ],
            "dependencies": [],
            "cells": cells,
            "drivers": {str(p): digest(p) for p in drivers},
            "preferences": prefs,
            "corpus_sha256": digest(BASE / "corpus.json"),
            "calls_max": 24,
            "retries": 0,
            "weekly_used_start": 52,
            "weekly_used_ceiling": 60,
            "qualification_credit": False,
            "decision": "One screen per model, all eight cases. >=6 semantic passes is a candidate for repeated tool-layer comparison, not acceptance. Stop after screen for evidence-backed stage decision, or infrastructure failure/usage ceiling.",
            "limits": "Known development fixtures, one repetition, raw Python single-file / JSON multi-file; same prompts per case across models. Saved KV preferences verified, actual loaded KV not independently exposed. Sampling fixed, not per-model tuned; packaging, quantization, template and backend are confounded.",
        },
    )
    print("prepared 24 calls; reference/mutant preflight passed", flush=True)


def run_cell(cell, client, worker):
    root = Path(cell["root"])
    FA.LAYER.verify_hashes(root, cell["hashes"])
    packet = read(root / ".agent/qual-unit-reference.json")
    writable = packet["scope"]["modify"]
    single = len(writable) == 1
    instruction = (
        FA.FORM.output_instruction("python")
        if single
        else 'Implement the contract. Tests are read-only. Return only JSON {"files":[{"path":"...","content":"complete Python source"}]} including every authorized writable file. No Markdown, prose or commands.'
    )
    messages = [
        {"role": "system", "content": instruction},
        {
            "role": "user",
            "content": json.dumps(FA.FORM.payload(root, cell), ensure_ascii=False),
        },
    ]
    write(root / ".agent/request.json", messages)
    started = time.monotonic()
    raw = client.complete(messages)
    write(
        root / ".agent/response.json",
        {
            "raw": raw,
            "stats": client.last_request_stats,
            "seconds": time.monotonic() - started,
        },
    )
    outcome = {
        "cell": cell["id"],
        "semantic_pass": None,
        "format_pass": False,
        "error": None,
    }
    runtime = None
    try:
        if single:
            patch, fence = FA.FORM.decode_output(raw, "python", writable)
        else:
            stripped = raw.strip()
            fence = stripped.startswith("```json\n") and stripped.endswith("\n```")
            patch = FA.LAYER.parse_patch(
                stripped[8:-4] if fence else stripped, writable
            )
        for item in patch:
            compile(item["content"], item["path"], "exec")
        outcome["format_pass"] = not fence
        runtime = worker.WorkerRuntime(
            root, packet, read(root / ".agent/config.json"), None
        )
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
        result = FA.LAYER.check(root, "independent")
        FA.LAYER.verify_hashes(
            root, {p: sha for p, sha in cell["hashes"].items() if p not in writable}
        )
        outcome.update(semantic_pass=result["semantic_pass"], validation=result)
    except (ValueError, SyntaxError) as error:
        outcome["error"] = str(error)
    finally:
        if runtime:
            runtime.close()
    write(BASE / f"{cell['id']}-result.json", outcome)
    print(
        json.dumps({k: v for k, v in outcome.items() if k != "validation"}), flush=True
    )


def run(index):
    manifest = read(BASE / "manifest.json")
    for p, sha in {**manifest["drivers"], **manifest["preferences"]}.items():
        if digest(Path(p)) != sha:
            raise ValueError("driver/preferences drift")
    FA.LAYER.verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    FA.LAYER.verify_hashes(BASE, {"corpus.json": manifest["corpus_sha256"]})
    model = MODELS[index]
    directory = BASE / f"model-{index}"
    directory.mkdir(exist_ok=False)
    guard_residents(residents())
    config = read(SNAPSHOT / ".local-agents/config.json")
    config.update(
        explorer_model=MODELS[0],
        coder_model=model,
        reviewer_model=MODELS[1],
        coordinator_model=MODELS[2],
        model_switch_timeout_seconds=900,
    )
    worker = load_worker(SNAPSHOT)
    client = worker.LMStudioClient(
        config["lmstudio_base_url"],
        model,
        600,
        max_tokens=4096,
        temperature=0.1,
        top_p=0.9,
        top_k=40,
        min_p=0.0,
        repeat_penalty=1.0,
        structured_output=False,
        context_length=24576,
    )
    started = time.monotonic()
    print(json.dumps({"loading": model}), flush=True)
    try:
        with worker.MODEL_RESIDENCY.role_model_lease(client, config):
            instance = loaded_config(model)
            write(
                directory / "loaded.json",
                {
                    "instance": instance,
                    "load_seconds": time.monotonic() - started,
                    "cli": residents(),
                },
            )
            for cell in manifest["cells"]:
                if cell["model"] == model:
                    guard_residents(residents(), model)
                    if loaded_config(model) != instance:
                        raise ValueError("loaded config drift")
                    run_cell(cell, client, worker)
            guard_residents(residents(), model)
            write(
                directory / "completed.json",
                {"completed": True, "instance": loaded_config(model)},
            )
            write(
                directory / "unloaded.json",
                FA.api("/unload", {"instance_id": instance["id"]}),
            )
            if residents():
                raise ValueError("unexpected residency after unload")
    except Exception as error:
        write(
            directory / "infrastructure-error.json",
            {"error": f"{type(error).__name__}: {error}", "residents": residents()},
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "0", "1", "2"))
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    else:
        run(int(args.action))
