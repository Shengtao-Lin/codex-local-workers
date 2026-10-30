"""D1: six preregistered high-level briefs × two independent Muse proposals."""

import argparse
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import time

from convergence_coder import KIT, save
from system_convergence import read_object, ref, sha256

BASE = KIT / "benchmarks/work/system-convergence/d1-20261010-1"
RUNTIME = BASE / "candidate-kit/.local-agents"
FIXTURE = KIT / "benchmarks/fixtures/convergence-decomposition"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def prepare():
    definitions = [
        (
            "single",
            "Harden is_internal_trace for malformed nested telemetry without changing valid dictionary inputs.",
            [
                (
                    "classification-shapes",
                    "Non-dict raw or truthy non-dict attributes, metadata or resource must classify False without raising. All existing valid evaluator markers, custom service names and nonmutation behavior remain unchanged.",
                    "medium",
                )
            ],
            ["src/evaluation_harness/telemetry/classification.py"],
            ["tests/test_classification_shapes.py"],
            [],
            [],
            "single cohesive unit",
        ),
        (
            "independent",
            "Add a read-only runtime attribute-name snapshot and independently harden telemetry classification shapes.",
            [
                (
                    "attribute-snapshot",
                    "runtime_attribute_names() returns a tuple of sorted unique string values of existing uppercase attribute constants. Preserve every existing constant and do not expose mutable state.",
                    "medium",
                ),
                (
                    "classification-shapes",
                    "Non-dict raw or truthy non-dict attributes, metadata or resource must classify False without raising. Preserve all existing valid marker/custom-service behavior and inputs.",
                    "medium",
                ),
            ],
            [
                "src/agent_runtime/telemetry/attributes.py",
                "src/evaluation_harness/telemetry/classification.py",
            ],
            ["tests/test_attribute_names.py", "tests/test_classification_shapes.py"],
            [],
            [],
            "two independent behaviors may be separate; no invented dependency",
        ),
        (
            "producer-consumer",
            "Normalize lookup keys and ensure public lookups consume precisely the same input representation.",
            [
                (
                    "normalized-key",
                    "normalize_key accepts strings, strips outer whitespace only, rejects non-strings with TypeError and empty/whitespace-only with ValueError; do not remove internal characters.",
                    "medium",
                ),
                (
                    "lookup-roundtrip",
                    "lookup(mapping,key) consumes normalize_key output for the exact padded string form, preserves stored falsy values and does not mutate mapping. Missing keys keep KeyError.",
                    "medium",
                ),
            ],
            ["src/product/producer.py", "src/product/consumer.py"],
            ["tests/test_roundtrip.py"],
            [["normalized-key", "lookup-roundtrip"]],
            [],
            "consumer depends on producer when split; exact padded-input integration mandatory",
        ),
        (
            "atomic",
            "Change the accepted input and doubled output of the public compute boundary as one indivisible compatibility change.",
            [
                (
                    "accepted-input",
                    "compute accepts integers and outer-whitespace signed decimal strings, without coercing arbitrary types or changing valid integer behavior.",
                    "high",
                ),
                (
                    "atomic-output",
                    "compute returns twice the normalized integer. Its helper and entry-point must agree for negative/zero/positive and padded inputs; no intermediate accepted-but-misinterpreted state may be dispatched or accepted.",
                    "high",
                ),
            ],
            ["src/product/entry.py", "src/product/core.py"],
            ["tests/test_atomic.py"],
            [],
            [["accepted-input", "atomic-output"]],
            "one atomic unit despite two source files; high floor",
        ),
        (
            "unknown",
            "Implement the external report endpoint, whose location and wire contract have not been supplied.",
            [
                (
                    "unspecified-endpoint",
                    "Primary must supply the actual endpoint path and response schema before edits; do not invent an API, default semantics or executable acceptance from a placeholder test.",
                    "medium",
                )
            ],
            [],
            ["tests/test_unknown.py"],
            [],
            [],
            "unresolved with concrete question, no fabricated units or source evidence",
        ),
        (
            "protected-context",
            "Implement display_name in the writable wrapper with the same presence semantics as the read-only legacy context.",
            [
                (
                    "presence-wrapper",
                    "display_name returns present name unchanged including None/empty string, unnamed only for absent key, and never mutates input. Only writable wrapper may change; context/legacy.py and tests are protected.",
                    "medium",
                )
            ],
            ["src/product/wrapper.py"],
            ["tests/test_wrapper.py"],
            [],
            [],
            "single wrapper, no write to legacy or tests",
        ),
    ]
    module = load("d1_prepare", RUNTIME / "coordinator-brief.py")
    briefs = []
    for name, goal, contracts, writes, tests, edges, atomic, oracle in definitions:
        root = BASE / "fixtures" / name
        root.mkdir(parents=True)
        provenance = []
        for path in [
            *writes,
            *tests,
            "pyproject.toml",
            *(["context/legacy.py"] if name == "protected-context" else []),
        ]:
            sibling = (
                Path("F:/ChatGPT/agent-evaluation-harness")
                if path.startswith("src/evaluation_harness/")
                else Path("F:/ChatGPT/agent-runtime-kit")
                if path.startswith("src/agent_runtime/")
                else None
            )
            source = sibling / path if sibling else FIXTURE / path
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            provenance.append(
                {
                    "source": str(source),
                    "destination": path,
                    "sha256": sha256(target),
                    "sibling_read_only": bool(sibling),
                }
            )
        read_roots = sorted({p.split("/")[0] for p in [*writes, *tests]})
        readonly = tests + ["pyproject.toml"]
        if name == "protected-context":
            read_roots.append("context")
            readonly.append("context/legacy.py")
        read_roots.append("pyproject.toml")
        risk = "high" if name == "atomic" else "medium"
        brief = {
            "schema_version": 1,
            "revision": 1,
            "feature_id": "d1-" + name,
            "task_id": "d1-" + name,
            "goal": goal,
            "feature_risk": risk,
            "integration_risk": risk,
            "risk_rationale": "Public behavior and protected compatibility tests; atomic input/output boundary high where stated",
            "contracts": [
                {"id": ident, "text": text, "risk_floor": floor} for ident, text, floor in contracts
            ],
            "authority": {
                "read_roots": read_roots,
                "modify": writes,
                "create": [],
                "readonly": readonly,
                "forbidden": [".agent", "AGENTS.md", ".local-agents"],
            },
            "max_units": 3,
            "atomic_contract_groups": atomic,
            "contract_edges": edges,
            "integration_tests": tests,
            "source_hashes": {p["destination"]: p["sha256"] for p in provenance},
            "unknowns": ["Endpoint location and wire schema missing"] if name == "unknown" else [],
            "validation_profile": "mixed-strict",
        }
        module.validate_brief(brief)
        context = {
            p["destination"]: (root / p["destination"]).read_text(encoding="utf-8-sig")
            for p in provenance
        }
        save(root / ".agent/brief.json", brief)
        save(root / ".agent/context.json", context)
        save(root / ".agent/provenance.json", provenance)
        briefs.append(
            {
                "id": name,
                "root": str(root),
                "brief": ref(root, ".agent/brief.json"),
                "context": ref(root, ".agent/context.json"),
                "oracle_primary_only": oracle,
                "source_hashes": brief["source_hashes"],
                "new_same_task_not_previously_exposed": name in ("single", "independent"),
                "assisted_navigation": "Full bounded source/test context; no preassigned units/dependencies/owners",
            }
        )
    config = read_object(
        KIT
        / "benchmarks/work/system-convergence/c1-20261010-1/cells/async-baseline/.agent/config.json"
    )
    assert config["coordinator_enabled"] is False and config["single_model_residency"] is True
    save(BASE / "config.json", config)
    cells = [
        {"id": brief["id"] + f"-r{repeat}", "brief_id": brief["id"], "repeat": repeat}
        for repeat in (1, 2)
        for brief in briefs
    ]
    save(
        BASE / "registration.json",
        {
            "stage": "D1",
            "registered": 12,
            "cells": cells,
            "briefs": briefs,
            "runtime": [
                ref(RUNTIME, p.relative_to(RUNTIME).as_posix()) for p in RUNTIME.rglob("*.py")
            ],
            "driver": ref(KIT, "benchmarks/convergence_decomposition.py"),
            "config": ref(BASE, "config.json"),
            "gate": "12 drafts with no critical violation; at least 10 acceptable/mechanical-only, at most two with one semantic revision; unresolved control may safely pause",
            "maximum_explorer_questions_per_proposal": 2,
            "maximum_protocol_corrections": 1,
            "maximum_semantic_revisions": 1,
            "dispatch_allowed": False,
            "coder_calls": 0,
            "weekly_used_start": 0,
            "previous_window_last_observed": 52,
            "weekly_used_ceiling": 60,
            "cloud_tokens": None,
            "primary_active_seconds": None,
        },
    )


def run(cell_id):
    registration = read_object(BASE / "registration.json")
    assert sha256(Path(__file__)) == registration["driver"]["sha256"]
    for item in registration["runtime"]:
        assert sha256(RUNTIME / item["path"]) == item["sha256"]
    assert sha256(BASE / "config.json") == registration["config"]["sha256"]
    cell = next(c for c in registration["cells"] if c["id"] == cell_id)
    entry = next(b for b in registration["briefs"] if b["id"] == cell["brief_id"])
    root = Path(entry["root"])
    for label in ("brief", "context"):
        assert sha256(root / entry[label]["path"]) == entry[label]["sha256"]
    output = BASE / "proposals" / (cell_id + ".json")
    if output.exists():
        raise FileExistsError("proposal already attempted")
    module = load("d1_live", RUNTIME / "coordinator-brief.py")
    worker = module.load("d1_worker", "worker-runtime.py")
    residency = module.load("d1_residency", "model_residency.py")
    brief = read_object(root / entry["brief"]["path"])
    module.assert_sources_current(brief, root)
    config = read_object(BASE / "config.json")
    client = worker.LMStudioClient(
        config["lmstudio_base_url"],
        config["coordinator_model"],
        context_length=config["coordinator_context_length"],
        max_tokens=config["coordinator_max_tokens"],
        timeout=config["coordinator_request_timeout_seconds"],
        structured_output=False,
    )
    start = time.perf_counter()
    try:
        with residency.role_model_lease(client, config):
            result = module.probe(
                brief,
                read_object(root / entry["context"]["path"]),
                client,
                reasoning_strength=config.get("coordinator_reasoning_strength"),
            )
    except (OSError, ValueError, worker.WorkerError, residency.ModelResidencyError) as exc:
        result = {
            "status": "infrastructure_or_request_failure",
            "reason": str(exc),
            "request_stats": copy.deepcopy(client.last_request_stats),
            "dispatch_allowed": False,
        }
    result.update(
        cell_id=cell_id,
        command_wall_seconds=time.perf_counter() - start,
        brief_sha256=module.digest(brief),
        primary_semantic_review="pending",
        cloud_tokens=None,
    )
    module.assert_sources_current(brief, root)
    save(output, result)
    print(
        cell_id,
        result["status"],
        json.dumps(result.get("proposal", result.get("reason"))),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("cell", nargs="?")
    args = parser.parse_args()
    prepare() if args.action == "prepare" else run(args.cell)
