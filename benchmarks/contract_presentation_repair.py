"""Paired contract rendering and one observed-pytest-feedback repair diagnostic."""

import argparse
import json
import time
from pathlib import Path

import coder_model_screen as SCREEN
from coder_model_screen_audit import apply_complete_files
from capability_fit import KIT, WORK, freeze, load_worker, write
from inherited_context_recovery import digest, read

FA = SCREEN.FA
BASE = WORK / "contract-presentation-repair-1"
SNAPSHOT = WORK / "contract-presentation-repair-baseline-1"
CASES = ("exact-count", "missing-label", "duration-pair", "encoded-path", "async-fetch")


def render(payload, arm):
    if arm == "json":
        return json.dumps(payload, ensure_ascii=False)
    if arm != "sections":
        raise ValueError("unknown rendering")
    return (
        "Contract:\n"
        + payload["contract"]
        + "\n\nWritable files:\n"
        + "\n".join(payload["writable"])
        + "\n\nFiles (tests and project configuration are read-only):\n"
        + "\n\n".join(f"--- {p} ---\n{text}" for p, text in payload["files"].items())
    )


def decode(raw, writable):
    if len(writable) == 1:
        return FA.FORM.decode_output(raw, "python", writable)
    stripped = raw.strip()
    fenced = stripped.startswith("```json\n") and stripped.endswith("\n```")
    patch = FA.LAYER.parse_patch(stripped[8:-4] if fenced else stripped, writable)
    return patch, fenced


def repair_eligible(result):
    return result.get("semantic_pass") is False and "validation" in result


def prepare():
    BASE.mkdir(exist_ok=False)
    if SCREEN.residents():
        raise ValueError("start from empty residency")
    freeze(SNAPSHOT.name)
    old = read(SCREEN.BASE / "manifest.json")
    proofs = read(SCREEN.BASE / "preflight.json")
    if not all(
        p["reference"]["all_checks_pass"]
        and all(not m["semantic_pass"] for m in p["mutants"])
        for p in proofs
    ):
        raise ValueError("prior fixture proof incomplete")
    FA.LAYER.verify_hashes(SCREEN.BASE, {"corpus.json": old["corpus_sha256"]})
    data = read(SCREEN.BASE / "corpus.json")
    data["cases"] = [
        next(c for c in data["cases"] if c["case_id"] == name) for name in CASES
    ]
    write(BASE / "corpus.json", data)
    FA.MIXED.CORPUS, FA.MIXED.WORK = BASE / "corpus.json", BASE / "runs"
    cells = []
    for index, model in enumerate(SCREEN.MODELS):
        for number, case in enumerate(data["cases"]):
            arms = (
                ("json", "sections")
                if (index + number) % 2 == 0
                else ("sections", "json")
            )
            for arm in arms:
                name = case["case_id"]
                root = Path(
                    FA.MIXED.prepare(
                        name,
                        1,
                        SNAPSHOT / ".local-agents/config.json",
                        f"m{index}-{arm}",
                    )["root"]
                )
                paths = [
                    *case["files"],
                    "pyproject.toml",
                    ".agent/config.json",
                    ".agent/qual-unit-reference.json",
                ]
                hashes = {p: digest(root / p) for p in paths}
                prior = next(c for c in old["cells"] if c["case"] == name)
                if any(
                    sha != prior["hashes"][p]
                    for p, sha in hashes.items()
                    if not p.startswith(".agent/")
                ):
                    raise ValueError("fixture differs from preflight-tested corpus")
                cell = {
                    "id": f"m{index}-{name}-{arm}",
                    "model": model,
                    "case": name,
                    "arm": arm,
                    "root": str(root),
                    "hashes": hashes,
                }
                write(root / ".agent/frozen-payload.json", FA.FORM.payload(root, cell))
                hashes[".agent/frozen-payload.json"] = digest(
                    root / ".agent/frozen-payload.json"
                )
                cells.append(cell)
    drivers = list(
        dict.fromkeys(
            [
                Path(__file__).resolve(),
                Path(SCREEN.__file__),
                KIT / "benchmarks/coder_model_screen_audit.py",
                *FA.DRIVERS,
            ]
        )
    )
    for p in drivers:
        dest = BASE / "drivers" / p.relative_to(KIT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(p.read_bytes())
    write(
        BASE / "manifest.json",
        {
            "feature_id": "paired-contract-presentation-and-repair",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "risk_rationale": "Generated code executes in trusted isolated fixtures; temporary model switching",
            "contracts": [
                "same-semantic-inputs",
                "single-residency",
                "one-observed-error-repair",
                "immutable-evidence",
                "no-qualification-credit",
            ],
            "dependencies": ["coder-model-screen-1 preflight"],
            "cells": cells,
            "drivers": {str(p): digest(p) for p in drivers},
            "preferences": old["preferences"],
            "corpus_sha256": digest(BASE / "corpus.json"),
            "preflight_sha256": digest(SCREEN.BASE / "preflight.json"),
            "max_calls": 60,
            "initial_calls": 30,
            "repairs_per_cell": 1,
            "weekly_used_start": 53,
            "weekly_used_ceiling": 60,
            "qualification_credit": False,
            "decision": "Complete all pairs, then stop for stage decision. Rendering benefit requires >=2 sections-only semantic wins and no json-only loss for a model in this small screen; otherwise inconclusive/no benefit. Report observed pytest-failure repair conversions separately. No stability or production promotion from one repetition.",
            "repair_policy": "Only parsed, executed pytest semantic failures get one repair. Include actual complete pytest stdout/stderr plus current writable source and original conversation. No reference answer, extra hint, static-only repair or decode repair. Same output instruction retained.",
            "limits": "Five known cases, one repetition, adaptive repair denominators, common sampling, visible batch sizes differ. Actual KV precision/template not independently verified.",
        },
    )
    print("prepared 30 first answers, at most 30 one-shot repairs", flush=True)


def evaluate(raw, root, runtime, cell, attempt):
    packet = runtime.packet
    writable = packet["scope"]["modify"]
    result = {"semantic_pass": None, "format_pass": False, "error": None}
    try:
        patch, fenced = decode(raw, writable)
        for item in patch:
            compile(item["content"], item["path"], "exec")
        result["format_pass"] = not fenced
        result["skipped_identical_files"] = apply_complete_files(runtime, root, patch)
        checks = FA.LAYER.check(root, f"attempt-{attempt}")
        FA.LAYER.verify_hashes(
            root, {p: sha for p, sha in cell["hashes"].items() if p not in writable}
        )
        result.update(semantic_pass=checks["semantic_pass"], validation=checks)
    except (ValueError, SyntaxError) as error:
        result["error"] = str(error)
    write(root / f".agent/attempt-{attempt}-result.json", result)
    return result


def run_cell(cell, client, worker):
    root = Path(cell["root"])
    FA.LAYER.verify_hashes(root, cell["hashes"])
    payload = read(root / ".agent/frozen-payload.json")
    instruction = (
        FA.FORM.output_instruction("python")
        if len(payload["writable"]) == 1
        else 'Implement the contract. Tests are read-only. Return only JSON {"files":[{"path":"...","content":"complete Python source"}]} including every authorized writable file. No Markdown, prose or commands.'
    )
    messages = [
        {"role": "system", "content": instruction},
        {"role": "user", "content": render(payload, cell["arm"])},
    ]
    packet, config = (
        read(root / ".agent/qual-unit-reference.json"),
        read(root / ".agent/config.json"),
    )
    runtime = worker.WorkerRuntime(root, packet, config, None)
    results = []
    try:
        runtime.write_lock.acquire()
        runtime._prepare_run_archive()
        for attempt in (0, 1):
            write(root / f".agent/attempt-{attempt}-request.json", messages)
            started = time.monotonic()
            raw = client.complete(messages)
            write(
                root / f".agent/attempt-{attempt}-response.json",
                {
                    "raw": raw,
                    "stats": client.last_request_stats,
                    "seconds": time.monotonic() - started,
                },
            )
            result = evaluate(raw, root, runtime, cell, attempt)
            results.append(result)
            if attempt == 1 or not repair_eligible(result):
                break
            feedback = (
                "The implementation failed the actual protected pytest run below. Repair it to satisfy the original contract. Return the same required complete-file output format. Do not change tests.\n\nActual pytest output:\n"
                + result["validation"]["checks"][0]["output"]
                + "\n\nCurrent writable files:\n"
                + "\n\n".join(
                    f"--- {p} ---\n{(root / p).read_text(encoding='utf-8')}"
                    for p in payload["writable"]
                )
            )
            messages = [
                *messages,
                {"role": "assistant", "content": raw},
                {"role": "user", "content": feedback},
            ]
    finally:
        runtime.close()
    summary = {
        "cell": cell["id"],
        "initial_semantic": results[0]["semantic_pass"],
        "repair_attempted": len(results) == 2,
        "final_semantic": results[-1]["semantic_pass"],
        "final_all_checks": results[-1]
        .get("validation", {})
        .get("all_checks_pass", False),
    }
    write(BASE / f"{cell['id']}-result.json", summary)
    print(json.dumps(summary), flush=True)


def run(index):
    manifest = read(BASE / "manifest.json")
    for p, sha in {**manifest["drivers"], **manifest["preferences"]}.items():
        if digest(Path(p)) != sha:
            raise ValueError("frozen driver or preference changed")
    FA.LAYER.verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    FA.LAYER.verify_hashes(BASE, {"corpus.json": manifest["corpus_sha256"]})
    directory = BASE / f"model-{index}"
    directory.mkdir(exist_ok=False)
    if SCREEN.residents():
        raise ValueError("expected empty residency before load")
    worker = load_worker(SNAPSHOT)
    config = read(SNAPSHOT / ".local-agents/config.json")
    model = SCREEN.MODELS[index]
    config.update(coder_model=model, model_switch_timeout_seconds=900)
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
            instance = SCREEN.loaded_config(model)
            write(
                directory / "loaded.json",
                {
                    "instance": instance,
                    "seconds": time.monotonic() - started,
                    "cli": SCREEN.residents(),
                },
            )
            try:
                for cell in manifest["cells"]:
                    if cell["model"] == model:
                        SCREEN.guard_residents(SCREEN.residents(), model)
                        if SCREEN.loaded_config(model) != instance:
                            raise ValueError("load drift")
                        run_cell(cell, client, worker)
                write(directory / "completed.json", {"completed": True})
            finally:
                SCREEN.guard_residents(SCREEN.residents(), model)
                write(
                    directory / "unloaded.json",
                    FA.api("/unload", {"instance_id": instance["id"]}),
                )
                if SCREEN.residents():
                    raise ValueError("residency not empty")
    except Exception as error:
        write(
            directory / "infrastructure-error.json",
            {
                "error": f"{type(error).__name__}: {error}",
                "residents": SCREEN.residents(),
            },
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
