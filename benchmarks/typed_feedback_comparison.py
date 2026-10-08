"""One final, frozen error-feedback comparison using ALL archived first failures."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import adapter_transfer as PRIOR
from capability_fit import KIT, WORK, freeze, load_worker, write
from inherited_context_recovery import digest, read

BASE = WORK / "typed-feedback-1"
SNAPSHOT = WORK / "typed-feedback-baseline-1"
PROBE = KIT / "benchmarks/typed_counterexample_probe.py"


def prepare():
    BASE.mkdir(exist_ok=False)
    if PRIOR.SCREEN.residents():
        raise ValueError("expected empty residency")
    freeze(SNAPSHOT.name)
    old = read(PRIOR.BASE / "manifest.json")
    PRIOR.FA.LAYER.verify_hashes(PRIOR.BASE, {"corpus.json": old["corpus_sha256"]})
    write(BASE / "corpus.json", read(PRIOR.BASE / "corpus.json"))
    PRIOR.FA.MIXED.CORPUS, PRIOR.FA.MIXED.WORK = BASE / "corpus.json", BASE / "runs"
    groups = []
    for group in old["groups"]:
        results = read(PRIOR.BASE / f"{group['id']}-result.json")
        if not all(r["initial_semantic"] is False for r in results):
            continue
        raw_path = PRIOR.BASE / "responses" / group["id"] / "initial.json"
        cells = []
        for arm in ("traceback", "typed"):
            root = Path(
                PRIOR.FA.MIXED.prepare(
                    group["case"],
                    group["repetition"],
                    SNAPSHOT / ".local-agents/config.json",
                    f"m{group['index']}-{arm}",
                )["root"]
            )
            hashes = {p: digest(root / p) for p in group["cells"][0]["hashes"]}
            for p, sha in hashes.items():
                if (
                    not p.startswith(".agent/")
                    and sha != group["cells"][0]["hashes"][p]
                ):
                    raise ValueError("fixture drift")
            probe_copy = root / ".agent/typed-probe.py"
            probe_copy.write_bytes(PROBE.read_bytes())
            hashes[".agent/typed-probe.py"] = digest(probe_copy)
            cells.append({"arm": arm, "root": str(root), "hashes": hashes})
        groups.append(
            {
                **{
                    k: group[k]
                    for k in ("id", "index", "model", "repetition", "case", "payload")
                },
                "cells": cells,
                "initial_response": str(raw_path),
                "initial_sha256": digest(raw_path),
            }
        )
    drivers = list(
        dict.fromkeys(
            [
                Path(__file__).resolve(),
                PROBE,
                Path(PRIOR.__file__),
                Path(PRIOR.ADAPTER.__file__),
                *[Path(p) for p in old["drivers"]],
            ]
        )
    )
    write(
        BASE / "manifest.json",
        {
            "feature_id": "typed-counterexample-repair",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "risk_rationale": "Execute model source in trusted fixtures and compare bounded evidence feedback",
            "contracts": [
                "all-prior-first-failures",
                "same-initial-source",
                "observed-facts-only",
                "single-residency",
                "one-repair",
                "immutable-evidence",
            ],
            "dependencies": ["complete-file-transfer-1"],
            "groups": groups,
            "drivers": {str(p): digest(p) for p in drivers},
            "preferences": old["preferences"],
            "corpus_sha256": digest(BASE / "corpus.json"),
            "calls_max": 2 * len(groups),
            "weekly_used_start": 56,
            "weekly_used_ceiling": 60,
            "qualification_credit": False,
            "decision": "Exactly one repair per arm. Typed feedback candidate requires >=2 additional semantic conversions, no loss, and gains repeated in a family/model; otherwise no demonstrated repeatable benefit. Close this prompt branch after cohort regardless; continue supervised scope and real harness if budget remains.",
            "limitations": "Known failed tasks, paired archive repair rather than fresh tasks. Typed arm appends executed facts, so information and token length differ. Both arms use the same default-off diagnostic adapter explicitly enabled and formatter; production unaffected.",
        },
    )
    print(
        json.dumps({"groups": len(groups), "planned_calls": 2 * len(groups)}),
        flush=True,
    )


def facts(root, case):
    process = subprocess.run(
        [sys.executable, "-B", ".agent/typed-probe.py", case],
        cwd=root,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=30,
        check=True,
    )
    result = json.loads(process.stdout)
    if not result["counterexamples"]:
        raise ValueError("failed pytest without probe counterexample")
    return result


def repair_group(group, client, worker):
    raw = read(Path(group["initial_response"]))["raw"]
    payload = group["payload"]
    instruction = (
        PRIOR.FA.FORM.output_instruction("python")
        if len(payload["writable"]) == 1
        else 'Implement the contract. Tests are read-only. Return only JSON {"files":[{"path":"...","content":"complete Python source"}]} including every authorized writable file. No Markdown, prose or commands.'
    )
    first_messages = [
        {"role": "system", "content": instruction},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        {"role": "assistant", "content": raw},
    ]
    shared = None
    summaries = []
    order = (
        group["cells"] if group["repetition"] == 1 else list(reversed(group["cells"]))
    )
    for cell in order:
        root = Path(cell["root"])
        PRIOR.FA.LAYER.verify_hashes(root, cell["hashes"])
        runtime = worker.WorkerRuntime(
            root,
            read(root / ".agent/qual-unit-reference.json"),
            read(root / ".agent/config.json"),
            None,
        )
        # Same normalization and formatting in both arms; only feedback changes.
        evaluated_cell = dict(cell, arm="candidate")
        try:
            runtime.write_lock.acquire()
            runtime._prepare_run_archive()
            initial = PRIOR.evaluate(raw, evaluated_cell, runtime, 0)
            if initial["semantic_pass"] is not False:
                raise ValueError("archived initial no longer reproduces")
            observed = facts(root, group["case"])
            write(root / ".agent/counterexamples.json", observed)
            source = "\n\n".join(
                f"--- {p} ---\n{(root / p).read_text(encoding='utf-8')}"
                for p in payload["writable"]
            )
            if shared is None:
                shared = (
                    "Repair the implementation to satisfy the original contract. Same required complete-file output, no test changes. Actual protected pytest output:\n"
                    + initial["validation"]["checks"][0]["output"]
                    + "\nCurrent writable files:\n"
                    + source
                )
                shared_facts, shared_source = observed, source
            elif observed != shared_facts or source != shared_source:
                raise ValueError("paired observations or source differ")
            feedback = shared
            if cell["arm"] == "typed":
                feedback += (
                    "\nAdditional actual execution observations (input types, contract expectation, observed result):\n"
                    + json.dumps(observed, ensure_ascii=False)
                )
            response = PRIOR.call(
                client,
                [*first_messages, {"role": "user", "content": feedback}],
                BASE / "responses" / group["id"] / f"{cell['arm']}.json",
            )
            final = PRIOR.evaluate(response, evaluated_cell, runtime, 1)
            summaries.append(
                {
                    "arm": cell["arm"],
                    "semantic_pass": final["semantic_pass"],
                    "all_checks_pass": final["all_checks_pass"],
                    "error": final["error"],
                }
            )
        finally:
            runtime.close()
    write(BASE / f"{group['id']}-result.json", summaries)
    print(json.dumps({"group": group["id"], "results": summaries}), flush=True)


def run(index):
    manifest = read(BASE / "manifest.json")
    for p, sha in {**manifest["drivers"], **manifest["preferences"]}.items():
        if digest(Path(p)) != sha:
            raise ValueError("driver/preferences drift")
    PRIOR.FA.LAYER.verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    PRIOR.FA.LAYER.verify_hashes(BASE, {"corpus.json": manifest["corpus_sha256"]})
    for group in manifest["groups"]:
        if digest(Path(group["initial_response"])) != group["initial_sha256"]:
            raise ValueError("archived response drift")
    directory = BASE / f"model-{index}"
    directory.mkdir(exist_ok=False)
    if PRIOR.SCREEN.residents():
        raise ValueError("expected empty residency")
    worker = load_worker(SNAPSHOT)
    model = PRIOR.SCREEN.MODELS[index]
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
    print(json.dumps({"loading": model}), flush=True)
    with worker.MODEL_RESIDENCY.role_model_lease(client, config):
        instance = PRIOR.SCREEN.loaded_config(model)
        write(directory / "loaded.json", instance)
        try:
            for group in manifest["groups"]:
                if group["index"] == index:
                    PRIOR.SCREEN.guard_residents(PRIOR.SCREEN.residents(), model)
                    if PRIOR.SCREEN.loaded_config(model) != instance:
                        raise ValueError("loaded config drift")
                    repair_group(group, client, worker)
            write(directory / "completed.json", {"completed": True})
        except Exception as error:
            write(
                directory / "infrastructure-error.json",
                {"error": f"{type(error).__name__}: {error}"},
            )
            raise
        finally:
            PRIOR.SCREEN.guard_residents(PRIOR.SCREEN.residents(), model)
            write(
                directory / "unloaded.json",
                PRIOR.FA.api("/unload", {"instance_id": instance["id"]}),
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "0", "1", "2"))
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    else:
        run(int(args.action))
