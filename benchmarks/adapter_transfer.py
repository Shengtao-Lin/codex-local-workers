"""Frozen paired candidate transfer; shared first answer and independent repairs."""

import argparse
import json
import sys
import time
from pathlib import Path

import adapter_transfer_cases as CASES
import complete_file_candidate as ADAPTER
import contract_presentation_repair as OLD
from capability_fit import KIT, WORK, freeze, load_worker, write
from inherited_context_recovery import digest, read

FA, SCREEN = OLD.FA, OLD.SCREEN
BASE = WORK / "complete-file-transfer-1"
SNAPSHOT = WORK / "complete-file-transfer-baseline-1"


def prepare():
    BASE.mkdir(exist_ok=False)
    if SCREEN.residents():
        raise ValueError("expected empty residency")
    freeze(SNAPSHOT.name)
    data, references = CASES.cases(
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
        broken = FA.LAYER.check(root, "broken")
        for p, source in references[name].items():
            (root / p).write_text(source, encoding="utf-8")
        FA.LAYER.command(root, [sys.executable, "-m", "ruff", "format", "src"])
        reference = FA.LAYER.check(root, "reference")
        mutant = dict(references[name])
        if name == "window-bounds":
            mutant["src/product/target.py"] = mutant["src/product/target.py"].replace(
                "type(start) is not int or type(size) is not int",
                "not isinstance(start, int) or not isinstance(size, int)",
            )
        elif name == "port-roundtrip":
            mutant["src/product/options.py"] = mutant["src/product/options.py"].replace(
                "any(c < '0' or c > '9' for c in text)", "not text.isdigit()"
            )
        else:
            mutant["src/product/target.py"] = mutant["src/product/target.py"].replace(
                "value is None", "not value"
            )
        for p, source in mutant.items():
            (root / p).write_text(source, encoding="utf-8")
        near = FA.LAYER.check(root, "near-mutant")
        proofs.append(
            {
                "case": name,
                "broken": broken,
                "reference": reference,
                "near_mutant": near,
            }
        )
    write(BASE / "preflight.json", proofs)
    if not all(
        p["reference"]["all_checks_pass"]
        and not p["broken"]["semantic_pass"]
        and not p["near_mutant"]["semantic_pass"]
        for p in proofs
    ):
        raise ValueError("preflight failed")
    FA.MIXED.WORK = BASE / "runs"
    groups = []
    for model_index, model in enumerate(SCREEN.MODELS):
        for repetition in (1, 2):
            for case in data["cases"]:
                cells = []
                for arm in ("baseline", "candidate"):
                    root = Path(
                        FA.MIXED.prepare(
                            case["case_id"],
                            repetition,
                            SNAPSHOT / ".local-agents/config.json",
                            f"m{model_index}-{arm}",
                        )["root"]
                    )
                    paths = [
                        *case["files"],
                        "pyproject.toml",
                        ".agent/config.json",
                        ".agent/qual-unit-reference.json",
                    ]
                    cell = {
                        "arm": arm,
                        "root": str(root),
                        "hashes": {p: digest(root / p) for p in paths},
                    }
                    cells.append(cell)
                payloads = [FA.FORM.payload(Path(c["root"]), c) for c in cells]
                if payloads[0] != payloads[1]:
                    raise ValueError("paired input mismatch")
                groups.append(
                    {
                        "id": f"m{model_index}-r{repetition}-{case['case_id']}",
                        "index": model_index,
                        "model": model,
                        "repetition": repetition,
                        "case": case["case_id"],
                        "cells": cells,
                        "payload": payloads[0],
                    }
                )
    drivers = list(
        dict.fromkeys(
            [
                Path(__file__).resolve(),
                Path(CASES.__file__),
                Path(ADAPTER.__file__),
                Path(OLD.__file__),
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
            "feature_id": "complete-file-adapter-transfer",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "risk_rationale": "Parsing model source and executing protected tests; candidate diagnostic only",
            "contracts": [
                "shared-initial-answer",
                "scope-hash-guards",
                "no-action-extraction",
                "ast-preserving-format",
                "one-pytest-repair",
                "single-residency",
            ],
            "groups": groups,
            "drivers": {str(p): digest(p) for p in drivers},
            "preferences": read(OLD.BASE / "manifest.json")["preferences"],
            "corpus_sha256": digest(BASE / "corpus.json"),
            "initial_calls": 18,
            "max_calls": 54,
            "repetitions": 2,
            "weekly_used_start": 54,
            "weekly_used_ceiling": 60,
            "qualification_credit": False,
            "decision": "At completion stop for stage decision. Candidate useful if >=2 additional all-check successes, no loss of baseline success and no guard violation; require per-model/family replication before any production proposal. Not Coordinator qualification.",
            "limits": "Three new near-transfer tasks in known semantic families. Candidate bundles bounded normalization plus AST-preserving formatting; metrics separate normalized, semantic and all-check gains. Same initial response, repairs diverge by observed pytest evidence. No repair for decode/static-only failures.",
        },
    )
    print("prepared 18 paired initial responses, at most 36 repairs", flush=True)


def evaluate(raw, cell, runtime, attempt):
    root = Path(cell["root"])
    writable = runtime.packet["scope"]["modify"]
    result = {"semantic_pass": None, "all_checks_pass": False, "error": None}
    try:
        patch, metadata = ADAPTER.prepare_patch(
            raw, writable, enabled=cell["arm"] == "candidate"
        )
        result["adapter"] = metadata
        result["skipped"] = OLD.apply_complete_files(runtime, root, patch)
        checks = FA.LAYER.check(root, f"attempt-{attempt}")
        FA.LAYER.verify_hashes(
            root, {p: sha for p, sha in cell["hashes"].items() if p not in writable}
        )
        result.update(
            semantic_pass=checks["semantic_pass"],
            all_checks_pass=checks["all_checks_pass"],
            validation=checks,
        )
    except (ValueError, SyntaxError) as error:
        result["error"] = str(error)
    write(root / f".agent/attempt-{attempt}-result.json", result)
    return result


def call(client, messages, path):
    write(path.with_name(path.stem + "-request.json"), messages)
    started = time.monotonic()
    raw = client.complete(messages)
    write(
        path,
        {
            "raw": raw,
            "stats": client.last_request_stats,
            "seconds": time.monotonic() - started,
        },
    )
    return raw


def run_group(group, client, worker):
    payload = group["payload"]
    instruction = (
        FA.FORM.output_instruction("python")
        if len(payload["writable"]) == 1
        else 'Implement the contract. Tests are read-only. Return only JSON {"files":[{"path":"...","content":"complete Python source"}]} including every authorized writable file. No Markdown, prose or commands.'
    )
    messages = [
        {"role": "system", "content": instruction},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
    directory = BASE / "responses" / group["id"]
    for cell in group["cells"]:
        FA.LAYER.verify_hashes(Path(cell["root"]), cell["hashes"])
    raw = call(client, messages, directory / "initial.json")
    summaries = []
    order = (
        group["cells"] if group["repetition"] == 1 else list(reversed(group["cells"]))
    )
    for cell in order:
        root = Path(cell["root"])
        runtime = worker.WorkerRuntime(
            root,
            read(root / ".agent/qual-unit-reference.json"),
            read(root / ".agent/config.json"),
            None,
        )
        try:
            runtime.write_lock.acquire()
            runtime._prepare_run_archive()
            result = evaluate(raw, cell, runtime, 0)
            initial = dict(result)
            repaired = OLD.repair_eligible(result)
            if repaired:
                feedback = (
                    "Repair the implementation to satisfy the original contract. Same required complete-file output, no test changes. Actual protected pytest output:\n"
                    + result["validation"]["checks"][0]["output"]
                    + "\nCurrent writable files:\n"
                    + "\n\n".join(
                        f"--- {p} ---\n{(root / p).read_text(encoding='utf-8')}"
                        for p in payload["writable"]
                    )
                )
                repair = call(
                    client,
                    [
                        *messages,
                        {"role": "assistant", "content": raw},
                        {"role": "user", "content": feedback},
                    ],
                    directory / f"{cell['arm']}-repair.json",
                )
                result = evaluate(repair, cell, runtime, 1)
            summaries.append(
                {
                    "arm": cell["arm"],
                    "initial_semantic": initial["semantic_pass"],
                    "initial_all_checks": initial["all_checks_pass"],
                    "repair_attempted": repaired,
                    "final_semantic": result["semantic_pass"],
                    "final_all_checks": result["all_checks_pass"],
                    "normalized": any(
                        r.get("adapter", {}).get("normalized", False)
                        for r in (initial, result)
                    ),
                }
            )
        finally:
            runtime.close()
    write(BASE / f"{group['id']}-result.json", summaries)
    print(json.dumps({"group": group["id"], "results": summaries}), flush=True)


def run(index, repetition):
    manifest = read(BASE / "manifest.json")
    for p, sha in {**manifest["drivers"], **manifest["preferences"]}.items():
        if digest(Path(p)) != sha:
            raise ValueError("frozen driver/preferences drift")
    FA.LAYER.verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    FA.LAYER.verify_hashes(BASE, {"corpus.json": manifest["corpus_sha256"]})
    directory = BASE / f"batch-{index}-{repetition}"
    directory.mkdir(exist_ok=False)
    if SCREEN.residents():
        raise ValueError("expected empty residency")
    worker = load_worker(SNAPSHOT)
    model = SCREEN.MODELS[index]
    config = read(SNAPSHOT / ".local-agents/config.json")
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
    print(json.dumps({"loading": model, "repetition": repetition}), flush=True)
    try:
        with worker.MODEL_RESIDENCY.role_model_lease(client, config):
            instance = SCREEN.loaded_config(model)
            write(directory / "loaded.json", instance)
            try:
                for group in manifest["groups"]:
                    if group["index"] == index and group["repetition"] == repetition:
                        SCREEN.guard_residents(SCREEN.residents(), model)
                        if SCREEN.loaded_config(model) != instance:
                            raise ValueError("load drift")
                        run_group(group, client, worker)
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
            {"error": f"{type(error).__name__}: {error}"},
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("prepare", "0-1", "0-2", "1-1", "1-2", "2-1", "2-2")
    )
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    else:
        run(*map(int, args.action.split("-")))
