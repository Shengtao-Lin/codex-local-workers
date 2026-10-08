"""Paired raw-Python/JSON diagnostics. Never accepts units or changes defaults."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

import layer_isolation as LAYER
import mixed_feature_benchmark as MIXED
from capability_fit import KIT, WORK, load_worker, write
from inherited_context_recovery import digest, read
from layer_isolation_cases import corpus

BASE = WORK / "roleq-output-form-1"
SNAPSHOT = WORK / "roleq-output-baseline-1"
CASES = ("exact-count", "stable-latest", "async-fetch", "missing-label")
ARMS = ("python", "json")
DRIVERS = [
    Path(__file__),
    Path(LAYER.__file__),
    Path(MIXED.__file__),
    KIT / "benchmarks/layer_isolation_cases.py",
    KIT / "benchmarks/capability_fit.py",
    KIT / "benchmarks/inherited_context_recovery.py",
]


def output_instruction(arm):
    shared = "Implement the contract. Tests are read-only. No prose, Markdown, commands or additional files. "
    if arm == "python":
        return (
            shared
            + "Return only the complete Python source for the single authorized writable file."
        )
    if arm == "json":
        return (
            shared
            + 'Return only JSON {"files":[{"path":"...","content":"complete Python source"}]} for the single authorized writable file.'
        )
    raise ValueError("unknown arm")


def decode_output(raw, arm, writable):
    if arm not in ARMS or len(writable) != 1:
        raise ValueError("one writable file and a registered arm required")
    stripped = raw.strip()
    lines = stripped.splitlines()
    removed = False
    if lines and lines[0] in {"```", "```json", "```python", "```py"}:
        if (
            len(lines) < 3
            or lines[-1] != "```"
            or any("```" in line for line in lines[1:-1])
        ):
            raise ValueError("incomplete or nested fence")
        stripped = "\n".join(lines[1:-1])
        removed = True
    elif "```" in stripped:
        raise ValueError("prose or embedded fence; no substring extraction")
    if not stripped:
        raise ValueError("empty output")
    patch = (
        LAYER.parse_patch(stripped, writable)
        if arm == "json"
        else [{"path": writable[0], "content": stripped.rstrip("\r\n") + "\n"}]
    )
    return patch, removed


def payload(root, cell):
    packet = read(root / ".agent/qual-unit-reference.json")
    return {
        "contract": packet["goal"],
        "writable": packet["scope"]["modify"],
        "files": {
            p: (root / p).read_text(encoding="utf-8")
            for p in cell["hashes"]
            if not p.startswith(".agent/")
        },
    }


def prepare():
    BASE.mkdir(exist_ok=False)
    LAYER.verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    template = read(KIT / "benchmarks/fixtures/mixed-features-v1.json")["cases"][0]
    data, oracles = corpus(template)
    data["cases"] = [
        next(c for c in data["cases"] if c["case_id"] == name) for name in CASES
    ]
    write(BASE / "corpus.json", data)
    write(BASE / "oracles-primary-only.json", {name: oracles[name] for name in CASES})
    MIXED.CORPUS, MIXED.WORK = BASE / "corpus.json", BASE / "preflight"
    preflight = []
    for case in data["cases"]:
        name = case["case_id"]
        root = Path(
            MIXED.prepare(name, 1, SNAPSHOT / ".local-agents/config.json", "of-pre")[
                "root"
            ]
        )
        mutant = LAYER.check(root, "mutant")
        for relative, text in oracles[name]["reference"].items():
            (root / relative).write_text(text, encoding="utf-8")
        LAYER.command(root, [LAYER.sys.executable, "-m", "ruff", "format", "src"])
        reference = LAYER.check(root, "reference")
        preflight.append({"case": name, "mutant": mutant, "reference": reference})
    write(BASE / "preflight.json", preflight)
    if not all(
        r["reference"]["all_checks_pass"] and not r["mutant"]["semantic_pass"]
        for r in preflight
    ):
        raise ValueError("reference/mutant preflight failed")
    MIXED.WORK = BASE / "runs"
    worker = load_worker(SNAPSHOT)
    cells = []
    for repetition in (1, 2):
        order = CASES if repetition == 1 else tuple(reversed(CASES))
        for name in order:
            arms = (
                ARMS if (CASES.index(name) + repetition) % 2 else tuple(reversed(ARMS))
            )
            pair = []
            for arm in arms:
                root = Path(
                    MIXED.prepare(
                        name,
                        repetition,
                        SNAPSHOT / ".local-agents/config.json",
                        "of1-" + arm,
                    )["root"]
                )
                packet = read(root / ".agent/qual-unit-reference.json")
                worker.validate_packet(packet)
                if len(packet["scope"]["modify"]) != 1:
                    raise ValueError("raw Python comparison must remain single-file")
                case = next(c for c in data["cases"] if c["case_id"] == name)
                paths = [
                    *case["files"],
                    "pyproject.toml",
                    ".agent/config.json",
                    ".agent/qual-unit-reference.json",
                ]
                cell = {
                    "id": f"{name}-{arm}-r{repetition}",
                    "case": name,
                    "arm": arm,
                    "repetition": repetition,
                    "root": str(root),
                    "hashes": {p: digest(root / p) for p in paths},
                }
                pair.append(payload(root, cell))
                cells.append(cell)
            if pair[0] != pair[1]:
                raise ValueError("paired user payload differs")
    # Freeze executable drivers, references and each cell before any model turn.
    for path in DRIVERS:
        dest = BASE / "drivers" / path.relative_to(KIT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    write(
        BASE / "manifest.json",
        {
            "feature_id": "output-form-isolation",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "contracts": [
                "same-payload-and-protection",
                "scope-and-hash-guards",
                "separate-format-and-semantic",
                "no-qualification-credit",
            ],
            "risk_rationale": "Model code replay with host permissions and runtime write guards; diagnostic results cannot accept a unit.",
            "snapshot": str(SNAPSHOT),
            "cells": cells,
            "drivers": {str(p): digest(p) for p in DRIVERS},
            "corpus_sha256": digest(BASE / "corpus.json"),
            "oracles_sha256": digest(BASE / "oracles-primary-only.json"),
            "calls_max": 16,
            "max_calls_per_batch": 2,
            "retries": 0,
            "axis": "Only system output-format instruction and decoder differ. Identical user payload in each pair; same model/sampling/output limit; no server grammar in either arm.",
            "format_policy": "strict_format means no fence and decodable output; content may be evaluated after removal of exactly one complete outer fence. No quote/code repair or prose extraction. Record source compilation separately.",
            "decision": "Finish all 16 unless infrastructure/budget stop. If raw Python still fails a family twice, JSON cannot be the sole cause for that family. A benefit requires both raw repeats pass where paired JSON fails; never promotes production from four selected cases.",
            "classification": "Previously exposed development cases; no model switch, loading-parameter change, Reviewer/Explorer/Coordinator credit",
            "weekly_used_start": 48,
            "weekly_used_ceiling": 60,
            "primary_accepted": False,
        },
    )
    print(json.dumps({"prepared": len(cells), "base": str(BASE)}), flush=True)


def run(cell, manifest):
    for path, sha in manifest["drivers"].items():
        if digest(Path(path)) != sha:
            raise ValueError("driver drift")
    LAYER.verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    LAYER.verify_hashes(
        BASE,
        {
            "corpus.json": manifest["corpus_sha256"],
            "oracles-primary-only.json": manifest["oracles_sha256"],
        },
    )
    root = Path(cell["root"])
    LAYER.verify_hashes(root, cell["hashes"])
    write(BASE / f"{cell['id']}-started.json", {"at": time.time()})
    packet = read(root / ".agent/qual-unit-reference.json")
    config = read(root / ".agent/config.json")
    worker = load_worker(SNAPSHOT)
    client = worker.LMStudioClient(
        config["lmstudio_base_url"],
        config["coder_model"],
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
    messages = [
        {"role": "system", "content": output_instruction(cell["arm"])},
        {
            "role": "user",
            "content": json.dumps(payload(root, cell), ensure_ascii=False),
        },
    ]
    write(
        root / ".agent/model-request.json",
        {"messages": messages, "model": config["coder_model"]},
    )
    result = {
        "cell": cell["id"],
        "case": cell["case"],
        "arm": cell["arm"],
        "repetition": cell["repetition"],
        "strict_format_pass": False,
        "decoded": False,
        "source_compiles": None,
        "semantic_evaluated": False,
        "semantic_pass": None,
        "static_pass": None,
        "primary_accepted": False,
        "infrastructure_failure": False,
        "error": None,
    }
    started = time.monotonic()
    runtime = None
    stage = "request"
    try:
        with worker.MODEL_RESIDENCY.role_model_lease(client, config):
            raw = client.complete(messages)
        write(
            root / ".agent/model-response.json",
            {"raw": raw, "request_stats": client.last_request_stats},
        )
        stage = "decode"
        patch, removed = decode_output(raw, cell["arm"], packet["scope"]["modify"])
        result.update(
            decoded=True, fence_removed=removed, strict_format_pass=not removed
        )
        stage = "compile"
        result["source_compiles"] = False
        for item in patch:
            compile(item["content"], item["path"], "exec")
        result["source_compiles"] = True
        stage = "apply"
        LAYER.verify_hashes(root, cell["hashes"])
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
        stage = "validate"
        checks = LAYER.check(root, "independent")
        result["validation"] = checks
        LAYER.verify_hashes(
            root,
            {
                p: sha
                for p, sha in cell["hashes"].items()
                if p not in packet["scope"]["modify"]
            },
        )
        result.update(
            semantic_evaluated=True,
            semantic_pass=checks["semantic_pass"],
            static_pass=checks["static_pass"],
            protected_unchanged=True,
        )
    except Exception as error:  # noqa: BLE001 -- preserve diagnostic failures
        result["error"] = f"{type(error).__name__}: {error}"
        result["failure_stage"] = stage
        result["infrastructure_failure"] = stage in {"request", "apply", "validate"}
    finally:
        if runtime is not None:
            runtime.close()
    result["seconds"] = time.monotonic() - started
    result["request_stats"] = client.last_request_stats
    result["final_source_hashes"] = {
        p: digest(root / p) for p in packet["scope"]["modify"]
    }
    write(BASE / f"{cell['id']}-result.json", result)
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "cell",
                    "strict_format_pass",
                    "decoded",
                    "source_compiles",
                    "semantic_pass",
                    "static_pass",
                    "error",
                )
            }
        ),
        flush=True,
    )
    return result


def summary(manifest):
    results, pending = [], []
    for cell in manifest["cells"]:
        path = BASE / f"{cell['id']}-result.json"
        if path.exists():
            results.append(read(path))
        else:
            pending.append(cell["id"])
    return {
        "completed": len(results),
        "pending": pending,
        "arms": {
            arm: {
                "completed": sum(r["arm"] == arm for r in results),
                "strict_format_pass": sum(
                    r["arm"] == arm and r["strict_format_pass"] for r in results
                ),
                "semantic_evaluated": sum(
                    r["arm"] == arm and r["semantic_evaluated"] for r in results
                ),
                "semantic_pass": sum(
                    r["arm"] == arm and r["semantic_pass"] is True for r in results
                ),
            }
            for arm in ARMS
        },
        "coordinator_released": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "next", "status"))
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    else:
        manifest = read(BASE / "manifest.json")
        if args.action == "next":
            pending = [
                c
                for c in manifest["cells"]
                if not (BASE / f"{c['id']}-result.json").exists()
            ]
            for cell in pending[: manifest["max_calls_per_batch"]]:
                if run(cell, manifest)["infrastructure_failure"]:
                    break
        print(json.dumps(summary(manifest)), flush=True)
