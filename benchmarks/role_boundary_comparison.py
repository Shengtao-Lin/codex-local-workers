"""Freeze stronger contract boundary evidence, without changing worker prompts."""

import argparse
import hashlib
import json
from pathlib import Path

import mixed_feature_benchmark as MIXED
from capability_fit import KIT, WORK, load_worker, write
from role_qualification_cases import corpus


def prepare(temperature=None, plain_json=False, vocabulary=False):
    base = WORK / (
        "roleq-plain-json-comparison-1"
        if plain_json
        else "roleq-temperature-comparison-1"
        if temperature is not None
        else "roleq-boundary-comparison-1"
    )
    if plain_json:
        base = WORK / "roleq-plain-json-comparison-1"
    if vocabulary:
        base = WORK / "roleq-vocabulary-comparison-2"
    base.mkdir(exist_ok=False)
    template = json.loads(
        (KIT / "benchmarks/fixtures/mixed-features-v1.json").read_text(encoding="utf-8")
    )["cases"][0]
    cases, oracles = corpus(template)
    write(base / "corpus.json", cases)
    write(base / "primary-only-oracles.json", oracles)
    MIXED.CORPUS = base / "corpus.json"
    MIXED.WORK = base / "runs"
    config_path = KIT / ".local-agents/config.json"
    if temperature is not None or plain_json:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        if temperature is not None:
            config["coder_temperature"] = temperature
        if plain_json:
            config["coder_structured_output"] = False
        config_path = base / "candidate-config.json"
        write(config_path, config)
    cells = []
    worker = load_worker(WORK / "roleq-bindings-1")
    for repetition in (1, 2):
        for case in ("window-groups", "timeout-roundtrip"):
            prepared = MIXED.prepare(
                case,
                repetition,
                config_path,
                "plainjson1"
                if plain_json
                else "temperature1"
                if temperature is not None
                else "boundary1",
            )
            root = Path(prepared["root"])
            if vocabulary:
                path = root / ".agent/qual-unit-reference.json"
                packet = json.loads(path.read_text(encoding="utf-8"))
                packet["implementation_guidance"] = [
                    "Contract vocabulary: EXACT TYPE means runtime type identity, NOT inheritance membership. Integer subclasses, including bool, are excluded by exact-int contracts. MISSING KEY means absence of that key, NOT a present None or false-like value. Defaults apply only to missing keys; reject invalid present values according to the contract. These are reusable definitions, not permission to change tests or hard behavior."
                ]
                worker.validate_packet(packet)
                # New workspace, before first model call; frozen old packets untouched.
                path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
            else:
                worker.validate_packet(
                    json.loads(
                        (root / ".agent/qual-unit-reference.json").read_text(
                            encoding="utf-8"
                        )
                    )
                )
            spec = next(c for c in cases["cases"] if c["case_id"] == case)
            cells.append(
                {
                    "case": case,
                    "repetition": repetition,
                    "workspace": str(root),
                    "initial_hashes": {
                        p: hashlib.sha256((root / p).read_bytes()).hexdigest()
                        for p in spec["files"]
                    },
                    "packet_sha256": hashlib.sha256(
                        (root / ".agent/qual-unit-reference.json").read_bytes()
                    ).hexdigest(),
                    "config_sha256": hashlib.sha256(
                        (root / ".agent/config.json").read_bytes()
                    ).hexdigest(),
                }
            )
    write(
        base / "manifest.json",
        {
            "classification": "Known development cases, not unseen qualification",
            "cells": cells,
            "runtime_snapshot": str(WORK / "roleq-bindings-1"),
            "explorer_cases": [],
            "axis": "Only packet contract vocabulary, guided development not unseen credit"
            if vocabulary
            else "Only coder_structured_output true -> false; JSON parser and action gates unchanged"
            if plain_json
            else "Only coder_temperature 0.1 -> 0.7"
            if temperature is not None
            else "Only protected exact-int subclass/False counterexamples; same hard contract",
            "control": "Strong-boundary fresh comparison 0/4"
            if temperature is not None or plain_json or vocabulary
            else "Binding-only fresh comparison 0/4; guided recovery 4/4 old-test passes but 0/4 exact-int Primary acceptance",
            "unchanged": [
                "source baseline",
                "models",
                "top_p/top_k/repeat_penalty (only temperature differs)"
                if temperature is not None
                else "sampling",
                "context",
                "budgets",
                "system prompt (packet advisory vocabulary differs)"
                if vocabulary
                else "prompts",
                "permissions",
                "hard contract",
                "runtime",
            ],
            "candidate_calls_max": 4,
            "criterion": "All protected checks, independent Reviewer and Primary source review; improvement only supports further qualification",
            "weekly_ceiling": 40,
            "preflight": "boundary-fixture-check-1.xml: 6 passed; references pass and near-correct subclass mutants rejected",
            "temperature_rationale": "Qwen official model card suggests 0.7; testing temperature component only, not full recommended sampling profile"
            if temperature is not None
            else None,
            "source": "https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct"
            if temperature is not None
            else None,
        },
    )
    print(base)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--temperature", type=float, choices=(0.7,))
    parser.add_argument("--plain-json", action="store_true")
    parser.add_argument("--vocabulary", action="store_true")
    args = parser.parse_args()
    if sum((args.temperature is not None, args.plain_json, args.vocabulary)) > 1:
        parser.error("choose one axis only")
    prepare(args.temperature, args.plain_json, args.vocabulary)
