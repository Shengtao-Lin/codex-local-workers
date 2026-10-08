"""Preregistered first layer: plain, scoped patch generation without agent tools.

This is a diagnostic, not an accepted Coder implementation. Tests execute model
code with host permissions, as in the existing trusted-local-repository harness.
No model-supplied commands are accepted; all edits use the frozen SafeEditor.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import mixed_feature_benchmark as MIXED
from capability_fit import KIT, WORK, load_worker, write
from inherited_context_recovery import digest, read
from layer_isolation_cases import corpus

BASE = WORK / "roleq-layer-direct-1"
SNAPSHOT = WORK / "roleq-layer-baseline-1"
DRIVERS = [
    Path(__file__),
    KIT / "benchmarks/layer_isolation_cases.py",
    Path(MIXED.__file__),
    KIT / "benchmarks/capability_fit.py",
    KIT / "benchmarks/inherited_context_recovery.py",
]


def command(root, argv, timeout=180):
    started = time.monotonic()
    proc = subprocess.run(
        argv,
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=timeout,
    )
    return {
        "argv": argv,
        "exit": proc.returncode,
        "seconds": time.monotonic() - started,
        "output": proc.stdout + proc.stderr,
    }


def check(root, label):
    junit = root / ".agent" / f"{label}.xml"
    if junit.exists():
        raise FileExistsError(junit)
    checks = [
        command(
            root,
            [
                sys.executable,
                "-B",
                "-m",
                "pytest",
                "tests",
                "-q",
                "-p",
                "no:cacheprovider",
                f"--junitxml={junit}",
            ],
        ),
        command(root, [sys.executable, "-m", "ruff", "check", "src", "tests"]),
        command(
            root, [sys.executable, "-m", "ruff", "format", "--check", "src", "tests"]
        ),
    ]
    nodes = list(ET.parse(junit).getroot().iter("testcase")) if junit.exists() else []
    executed = sum(node.find("skipped") is None for node in nodes)
    semantic = checks[0]["exit"] == 0 and executed > 0
    return {
        "checks": checks,
        "tests_executed": executed,
        "semantic_pass": semantic,
        "static_pass": all(c["exit"] == 0 for c in checks[1:]),
        "all_checks_pass": semantic and all(c["exit"] == 0 for c in checks[1:]),
    }


def verify_hashes(root, hashes):
    for relative, expected in hashes.items():
        if digest(root / relative) != expected:
            raise ValueError("frozen input drift: " + relative)


def parse_patch(raw, allowed):
    """Validate the entire response before applying even the first file."""
    obj = json.loads(raw)
    if (
        not isinstance(obj, dict)
        or set(obj) != {"files"}
        or not isinstance(obj["files"], list)
    ):
        raise ValueError("expected exactly a files array")
    seen = set()
    for item in obj["files"]:
        if (
            not isinstance(item, dict)
            or set(item) != {"path", "content"}
            or not isinstance(item["path"], str)
            or item["path"] not in allowed
            or item["path"] in seen
            or not isinstance(item["content"], str)
        ):
            raise ValueError("duplicate, malformed or out-of-scope file")
        seen.add(item["path"])
    if seen != set(allowed):
        raise ValueError("complete contents required for every writable file")
    return obj["files"]


def prepare():
    BASE.mkdir(exist_ok=False)
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    template = read(KIT / "benchmarks/fixtures/mixed-features-v1.json")["cases"][0]
    cases, oracles = corpus(template)
    write(BASE / "corpus.json", cases)
    write(BASE / "oracles-primary-only.json", oracles)
    MIXED.CORPUS, MIXED.WORK = BASE / "corpus.json", BASE / "preflight"
    preflight = []
    for case in cases["cases"]:
        root = Path(
            MIXED.prepare(
                case["case_id"], 1, SNAPSHOT / ".local-agents/config.json", "pre"
            )["root"]
        )
        broken = check(root, "mutant")
        for relative, text in oracles[case["case_id"]]["reference"].items():
            (root / relative).write_text(text, encoding="utf-8")
        command(root, [sys.executable, "-m", "ruff", "format", "src"])
        reference = check(root, "reference")
        result = {"case": case["case_id"], "reference": reference, "mutant": broken}
        write(root / "preflight.json", result)
        preflight.append(result)
    write(BASE / "preflight.json", preflight)
    if not all(
        c["reference"]["all_checks_pass"] and not c["mutant"]["semantic_pass"]
        for c in preflight
    ):
        raise ValueError("fixture preflight failed; no model calls allowed")
    worker = load_worker(SNAPSHOT)
    MIXED.WORK = BASE / "runs"
    cells = []
    # All repetitions frozen before the first request. No stop-on-semantic-failure
    # or sample selection: a negative direct result is needed for attribution.
    for repetition in (1, 2):
        order = cases["cases"] if repetition == 1 else list(reversed(cases["cases"]))
        for case in order:
            root = Path(
                MIXED.prepare(
                    case["case_id"],
                    repetition,
                    SNAPSHOT / ".local-agents/config.json",
                    "ld1",
                )["root"]
            )
            packet = read(root / ".agent/qual-unit-reference.json")
            worker.validate_packet(packet)
            files = [
                *case["files"],
                "pyproject.toml",
                ".agent/config.json",
                ".agent/qual-unit-reference.json",
            ]
            cells.append(
                {
                    "id": f"{case['case_id']}-r{repetition}",
                    "case": case["case_id"],
                    "repetition": repetition,
                    "exposure": case["exposure"],
                    "root": str(root),
                    "hashes": {p: digest(root / p) for p in files},
                }
            )
    write(
        BASE / "manifest.json",
        {
            "feature_id": "layer-isolation",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "contracts": [
                "scope-and-hash-guards",
                "immutable-evidence",
                "separate-semantic-and-format-scores",
                "no-qualification-credit",
            ],
            "risk_rationale": "Diagnostic patch application and test execution; cannot authorize product acceptance or expand model permissions.",
            "snapshot": str(SNAPSHOT),
            "cells": cells,
            "drivers": {str(p): digest(p) for p in DRIVERS},
            "corpus_sha256": digest(BASE / "corpus.json"),
            "oracles_sha256": digest(BASE / "oracles-primary-only.json"),
            "calls_max": 16,
            "retries": 0,
            "max_calls_per_batch": 2,
            "classification": "Development diagnostic, including known semantic controls; never unseen qualification.",
            "axis": "Plain JSON complete files, no service-side grammar, no agent loop; all source/tests up front, compact contract. This is a bundled diagnostic, not single-variable causal evidence.",
            "stop": "External weekly-used check before each batch, ceiling 60; preserve incomplete cells. At 16 results, >=6 families passing semantics twice opens tool-layer comparison; otherwise investigate serving/semantic floor first. Infrastructure failure pauses batch.",
            "next_arms": [
                "bounded minimal loop",
                "current full Coder; independent Reviewer before acceptance",
            ],
            "next_arms_status": "not implemented or executed in this direct-layer cohort; require separately frozen manifest",
            "weekly_used_start": 46,
            "weekly_used_ceiling": 60,
            "coordinator_started": False,
            "explorer_invoked": False,
            "reviewer_invoked": False,
            "primary_accepted": False,
            "cloud_tokens": None,
        },
    )
    print(
        json.dumps(
            {"prepared": len(cells), "preflight": len(preflight), "base": str(BASE)}
        ),
        flush=True,
    )


def run(cell, manifest):
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    for path, sha in manifest["drivers"].items():
        if digest(Path(path)) != sha:
            raise ValueError("driver drift")
    verify_hashes(
        BASE,
        {
            "corpus.json": manifest["corpus_sha256"],
            "oracles-primary-only.json": manifest["oracles_sha256"],
        },
    )
    root = Path(cell["root"])
    verify_hashes(root, cell["hashes"])
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
        {
            "role": "system",
            "content": 'Implement the contract. Return only JSON {"files":[{"path":"...","content":"complete Python source"}]}, including every authorized writable file. No Markdown or commands. Tests are read-only.',
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "contract": packet["goal"],
                    "writable": packet["scope"]["modify"],
                    "files": {
                        p: (root / p).read_text(encoding="utf-8")
                        for p in cell["hashes"]
                        if not p.startswith(".agent/")
                    },
                },
                ensure_ascii=False,
            ),
        },
    ]
    write(
        root / ".agent/model-request.json",
        {
            "messages": messages,
            "model": config["coder_model"],
            "config_sha256": cell["hashes"][".agent/config.json"],
        },
    )
    started = time.monotonic()
    result = {
        "cell": cell["id"],
        "case": cell["case"],
        "repetition": cell["repetition"],
        "format_pass": False,
        "semantic_pass": False,
        "static_pass": False,
        "primary_accepted": False,
        "coder_invoked": False,
        "reviewer_invoked": False,
        "error": None,
        "infrastructure_failure": False,
    }
    runtime = None
    try:
        with worker.MODEL_RESIDENCY.role_model_lease(client, config):
            raw = client.complete(messages)
        write(
            root / ".agent/model-response.json",
            {"raw": raw, "request_stats": client.last_request_stats},
        )
        patch = parse_patch(raw, packet["scope"]["modify"])
        result["format_pass"] = True
        verify_hashes(root, cell["hashes"])
        runtime = worker.WorkerRuntime(root, packet, config, None)
        runtime.write_lock.acquire()
        runtime._prepare_run_archive()
        for item in patch:
            relative = item["path"]
            observed = runtime.read_file({"path": relative})
            runtime.safe_replace(
                {
                    "path": relative,
                    "expected_sha256": observed["sha256"],
                    "find": (root / relative).read_text(encoding="utf-8"),
                    "replace": item["content"],
                }
            )
        result["validation"] = check(root, "independent")
        protected = {
            p: sha
            for p, sha in cell["hashes"].items()
            if p not in packet["scope"]["modify"]
        }
        verify_hashes(root, protected)
        result.update(
            semantic_pass=result["validation"]["semantic_pass"],
            static_pass=result["validation"]["static_pass"],
            protected_unchanged=True,
        )
    except Exception as error:  # noqa: BLE001 -- preserve failed diagnostic; never accept
        result["error"] = f"{type(error).__name__}: {error}"
        result["infrastructure_failure"] = (
            not result["format_pass"]
            and not (root / ".agent/model-response.json").exists()
        )
    finally:
        if runtime is not None:
            runtime.close()
    result["request_stats"] = client.last_request_stats
    result["seconds"] = time.monotonic() - started
    result["final_source_hashes"] = {
        p: digest(root / p) for p in packet["scope"]["modify"]
    }
    result["response_sha256"] = (
        digest(root / ".agent/model-response.json")
        if (root / ".agent/model-response.json").exists()
        else None
    )
    write(BASE / f"{cell['id']}-result.json", result)
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "cell",
                    "format_pass",
                    "semantic_pass",
                    "static_pass",
                    "error",
                    "seconds",
                )
            }
        ),
        flush=True,
    )
    return result


def decision(manifest):
    results = []
    pending = []
    for cell in manifest["cells"]:
        path = BASE / f"{cell['id']}-result.json"
        if path.exists():
            results.append(read(path))
        else:
            pending.append(cell["id"])
    families = {cell["case"] for cell in manifest["cells"]}
    stable = [
        name
        for name in sorted(families)
        if sum(r["case"] == name and r["semantic_pass"] for r in results) == 2
    ]
    return {
        "completed": len(results),
        "pending": pending,
        "format_pass": sum(r["format_pass"] for r in results),
        "semantic_pass": sum(r["semantic_pass"] for r in results),
        "static_pass": sum(r["static_pass"] for r in results),
        "stable_families": stable,
        "decision": "incomplete"
        if pending
        else "tool-layer-comparison"
        if len(stable) >= 6
        else "serving-or-semantic-floor-investigation",
        "qualification_credit": False,
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
                outcome = run(cell, manifest)
                if outcome["infrastructure_failure"]:
                    break
        print(json.dumps(decision(manifest)), flush=True)
