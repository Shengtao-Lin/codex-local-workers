"""Bounded full-context patch production diagnostic, not Coder qualification."""

import hashlib
import json
from pathlib import Path

import mixed_feature_benchmark as MIXED
from capability_fit import KIT, WORK, load_worker, write


def prepare():
    base = WORK / "roleq-direct-diagnostic-1"
    base.mkdir(exist_ok=False)
    MIXED.CORPUS = WORK / "roleq-boundary-comparison-1/corpus.json"
    MIXED.WORK = base / "runs"
    cells = []
    for repetition in (1, 2):
        for case in ("window-groups", "timeout-roundtrip"):
            result = MIXED.prepare(
                case, repetition, KIT / ".local-agents/config.json", "direct1"
            )
            cells.append(
                {"case": case, "repetition": repetition, "workspace": result["root"]}
            )
    write(
        base / "manifest.json",
        {
            "axis": "Full authorized source/tests up front and one complete-patch request, no action loop",
            "classification": "Architectural diagnostic only; no Coder/Reviewer/qualification credit",
            "snapshot": str(WORK / "roleq-bindings-1"),
            "calls_max": 4,
            "unchanged": [
                "model",
                "temperature",
                "sampling",
                "context",
                "hard contract",
                "protected tests",
                "file permissions",
            ],
            "control": "Strong-boundary action loop 0/4",
            "cells": cells,
            "weekly_ceiling": 40,
        },
    )


def run(cell):
    root = Path(cell["workspace"])
    packet = json.loads(
        (root / ".agent/qual-unit-reference.json").read_text(encoding="utf-8")
    )
    config = json.loads((root / ".agent/config.json").read_text(encoding="utf-8"))
    worker = load_worker(WORK / "roleq-bindings-1")
    schema = {
        "type": "object",
        "properties": {
            "files": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["files"],
        "additionalProperties": False,
    }
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
        action_schema=schema,
        schema_name="bounded_direct_patch",
        context_length=config["coder_context_length"],
    )
    paths = packet["scope"]["modify"] + ["tests/test_target.py"]
    files = {p: (root / p).read_text(encoding="utf-8") for p in paths}
    hashes = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths}
    with worker.MODEL_RESIDENCY.role_model_lease(client, config):
        raw = client.complete(
            [
                {
                    "role": "system",
                    "content": "Implement the hard contract. Return only JSON files with complete new contents for authorized writable paths. Tests are protected. No commands or extra paths. Preserve all independent contract branches.",
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "packet": packet,
                            "project_configuration": (
                                root / "pyproject.toml"
                            ).read_text(encoding="utf-8"),
                            "files": files,
                        }
                    ),
                },
            ]
        )
    response = json.loads(raw)
    seen = set()
    for item in response["files"]:
        if (
            item["path"] not in packet["scope"]["modify"]
            or item["path"] in seen
            or not isinstance(item["content"], str)
        ):
            raise ValueError("out-of-scope or malformed patch")
        seen.add(item["path"])
    for p, digest in hashes.items():
        if hashlib.sha256((root / p).read_bytes()).hexdigest() != digest:
            raise ValueError("baseline drift")
    # Worker edit enforcement remains authoritative, including path/hash guards.
    runtime = worker.WorkerRuntime(root, packet, config, None)
    runtime.write_lock.acquire()
    try:
        runtime._prepare_run_archive()
        for item in response["files"]:
            observed = runtime.read_file({"path": item["path"]})
            runtime.safe_replace(
                {
                    "path": item["path"],
                    "expected_sha256": observed["sha256"],
                    "find": files[item["path"]],
                    "replace": item["content"],
                }
            )
        validation = runtime.validate(
            {"phase": "check", "contract_check": runtime.contract_check_template()}
        )
        write(
            root / "direct-result.json",
            {
                "classification": "Patch producer diagnostic; no qualified unit",
                "validation": validation,
                "request_stats": client.last_request_stats,
                "response_sha256": hashlib.sha256(raw.encode()).hexdigest(),
                "primary_accepted": False,
            },
        )
        print(
            json.dumps(
                {
                    "case": cell["case"],
                    "repetition": cell["repetition"],
                    "status": validation["status"],
                }
            ),
            flush=True,
        )
    finally:
        runtime.close()


if __name__ == "__main__":
    prepare()
    manifest = json.loads(
        (WORK / "roleq-direct-diagnostic-1/manifest.json").read_text(encoding="utf-8")
    )
    for cell in manifest["cells"]:
        run(cell)
