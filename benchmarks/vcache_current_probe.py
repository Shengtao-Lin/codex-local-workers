"""Test user-loaded V-cache settings without reloading or changing preferences."""

import argparse
import json
from pathlib import Path

import flash_attention_comparison as FA
from capability_fit import WORK, load_worker, write
from inherited_context_recovery import digest, read

BASE = WORK / "roleq-vcache-f16-user-1"


def prepare():
    BASE.mkdir(exist_ok=False)
    previous = read(FA.BASE / "manifest.json")
    FA.LAYER.verify_hashes(FA.SNAPSHOT, read(FA.SNAPSHOT / "freeze.json")["files"])
    original = FA.instance(FA.api())
    FA.require_config(original["config"], previous["original"]["config"], True)
    data = read(FA.BASE / "corpus.json")
    write(BASE / "corpus.json", data)
    FA.MIXED.CORPUS, FA.MIXED.WORK = BASE / "corpus.json", BASE / "runs"
    cells = []
    for repetition in (1, 2):
        for case in data["cases"]:
            root = Path(
                FA.MIXED.prepare(
                    case["case_id"],
                    repetition,
                    FA.SNAPSHOT / ".local-agents/config.json",
                    "vf1",
                )["root"]
            )
            paths = [
                *case["files"],
                "pyproject.toml",
                ".agent/config.json",
                ".agent/qual-unit-reference.json",
            ]
            cell = {
                "id": f"{case['case_id']}-r{repetition}",
                "case": case["case_id"],
                "repetition": repetition,
                "root": str(root),
                "hashes": {p: digest(root / p) for p in paths},
            }
            old = next(c for c in previous["cells"] if c["case"] == case["case_id"])
            for p, sha in cell["hashes"].items():
                if not p.startswith(".agent/") and old["hashes"][p] != sha:
                    raise ValueError("fixture differs from prior control")
            cells.append(cell)
    drivers = [Path(__file__), *FA.DRIVERS]
    for p in drivers:
        dest = BASE / "drivers" / p.relative_to(FA.KIT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(p.read_bytes())
    write(
        BASE / "manifest.json",
        {
            "feature_id": "user-loaded-vcache-probe",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "risk_rationale": "Generated source executes in trusted isolated fixture; no load mutations or acceptance",
            "contracts": [
                "no-reload",
                "same-protected-inputs",
                "immutable-history",
                "no-qualification-credit",
            ],
            "original_instance": original,
            "cells": cells,
            "calls_max": 6,
            "drivers": {str(p): digest(p) for p in drivers},
            "corpus_sha256": digest(BASE / "corpus.json"),
            "micro_question": previous["micro_question"],
            "micro_expected": previous["micro_expected"],
            "user_reported": {
                "k_cache": "Q8_0",
                "v_cache": "F16",
                "flash_attention": True,
                "reloaded": True,
            },
            "precision_verified_via_api": False,
            "limits": "Screenshot and user confirmation only for KV precision; API omits precision. No claim of causal f16 comparison without loaded-precision proof.",
            "weekly_used_start": 51,
            "weekly_used_ceiling": 60,
            "retries": 0,
            "qualification_credit": False,
            "coordinator_released": False,
        },
    )
    print(json.dumps({"prepared": len(cells), "planned_calls": 6}), flush=True)


def run(repetition):
    manifest = read(BASE / "manifest.json")
    for p, sha in manifest["drivers"].items():
        if digest(Path(p)) != sha:
            raise ValueError("driver drift")
    FA.LAYER.verify_hashes(FA.SNAPSHOT, read(FA.SNAPSHOT / "freeze.json")["files"])
    FA.LAYER.verify_hashes(BASE, {"corpus.json": manifest["corpus_sha256"]})
    write(BASE / f"r{repetition}-started.json", {"repetition": repetition})
    config = read(FA.SNAPSHOT / ".local-agents/config.json")
    worker = load_worker(FA.SNAPSHOT)
    client = worker.LMStudioClient(
        config["lmstudio_base_url"],
        FA.MODEL,
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
    original = manifest["original_instance"]["config"]
    # Reject absent/foreign models before the lease can auto-load any instance.
    FA.require_config(FA.instance(FA.api())["config"], original, True)
    FA.BASE = BASE
    with worker.MODEL_RESIDENCY.role_model_lease(client, config):
        for cell in manifest["cells"]:
            if cell["repetition"] == repetition:
                FA.require_config(FA.instance(FA.api())["config"], original, True)
                FA.implementation(cell, client, worker)
        messages = [
            {
                "role": "system",
                "content": "Answer the Python question accurately. Return only the requested JSON array, no prose or Markdown.",
            },
            {"role": "user", "content": manifest["micro_question"]},
        ]
        raw = client.complete(messages)
        correct, valid_json = False, False
        try:
            parsed = json.loads(raw)
            valid_json = True
            correct = json.dumps(parsed) == json.dumps(manifest["micro_expected"])
        except ValueError:
            pass
        write(
            BASE / f"micro-r{repetition}.json",
            {
                "messages": messages,
                "raw": raw,
                "valid_json": valid_json,
                "correct": correct,
                "stats": client.last_request_stats,
            },
        )
        after = FA.instance(FA.api())
        FA.require_config(after["config"], original, True)
        write(
            BASE / f"r{repetition}-complete.json",
            {
                "completed": True,
                "instance_after": after,
                "micro_correct": correct,
                "load_mutations": 0,
            },
        )
        print(
            json.dumps(
                {"repetition": repetition, "micro_correct": correct, "raw": raw}
            ),
            flush=True,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "r1", "r2"))
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    else:
        run(int(args.action[-1]))
