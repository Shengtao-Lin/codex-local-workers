"""Freeze new functionality to test formal-contract transfer before qualification."""

import argparse
import hashlib
import json
from pathlib import Path

import mixed_feature_benchmark as MIXED
from capability_fit import KIT, WORK, load_worker, write
from role_contract_transfer_cases import corpus


def prepare(examples=False):
    base = WORK / (
        "roleq-semantic-examples-1" if examples else "roleq-formal-transfer-1"
    )
    base.mkdir(exist_ok=False)
    template = json.loads(
        (KIT / "benchmarks/fixtures/mixed-features-v1.json").read_text(encoding="utf-8")
    )["cases"][0]
    cases, oracles = corpus(template)
    write(base / "corpus.json", cases)
    write(base / "primary-only-oracles.json", oracles)
    MIXED.CORPUS, MIXED.WORK = base / "corpus.json", base / "runs"
    worker = load_worker(WORK / "roleq-bindings-1")
    cells = []
    for repetition in (1, 2):
        for case in cases["cases"]:
            prepared = MIXED.prepare(
                case["case_id"],
                repetition,
                KIT / ".local-agents/config.json",
                "semantic1" if examples else "formal1",
            )
            root = Path(prepared["root"])
            path = root / ".agent/qual-unit-reference.json"
            packet = json.loads(path.read_text(encoding="utf-8"))
            if examples:
                packet["implementation_guidance"] = [
                    "Unrelated Python semantic examples (not this unit's implementation):\nclass IntegerChild(int): pass\nassert isinstance(True, int) and isinstance(IntegerChild(4), int)\n# Exact type identity, unlike inheritance membership:\nassert type(True) is not int and type(IntegerChild(4)) is not int\nassert type(4) is int\nclass FloatChild(float): pass\nassert isinstance(FloatChild(0.4), float) and type(FloatChild(0.4)) is not float\n# Missing-key default retains present values for separate validation:\nassert {}.get('label', 'auto') == 'auto'\nassert {'label': None}.get('label', 'auto') is None\nassert {'label': 0}.get('label', 'auto') == 0\nThese facts explain the hard contract vocabulary; do not weaken tests or copy a function implementation."
                ]
            packet["acceptance_scenarios"] = [
                {
                    "id": "normal",
                    "text": "Protected normal transformations pass without mutation.",
                    "observables": {"normal": True},
                },
                {
                    "id": "error",
                    "text": "Every invalid type/value raises ValueError, including subtype and present-null boundaries.",
                    "observables": {"error": True},
                },
                {
                    "id": "boundary",
                    "text": "Zero/exact byte boundaries or finite inclusive ratio boundaries are preserved.",
                    "observables": {"boundary": True},
                },
            ]
            worker.validate_packet(packet)
            path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
            config_path = root / ".agent/config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config.update(
                explorer_required_citation_paths=["tests/test_target.py"],
                explorer_require_test_assertion_citation=True,
            )
            config_path.write_text(
                json.dumps(config, indent=2) + "\n", encoding="utf-8"
            )
            cells.append(
                {
                    "case": case["case_id"],
                    "repetition": repetition,
                    "workspace": str(root),
                    "initial_hashes": {
                        p: hashlib.sha256((root / p).read_bytes()).hexdigest()
                        for p in case["files"]
                    },
                    "packet_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "config_sha256": hashlib.sha256(
                        config_path.read_bytes()
                    ).hexdigest(),
                    "explorer_task": "Locate parse_ratio in src/product/options.py and the protected invalid-input assertion in tests/test_target.py. Cite the source and test lines actually read. One question only; do not implement or review.",
                }
            )
    write(
        base / "manifest.json",
        {
            "classification": "Two new-functionality formal-contract transfer tasks; not complete six-task qualification",
            "runtime_snapshot": str(WORK / "roleq-bindings-1"),
            "cells": cells,
            "explorer_cases": ["ratio-report-boundary"],
            "preflight": "formal-transfer-preflight-1.xml: 8 passed (two new, six regression), all references pass and close mutants fail",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "risk_rationale": "Qualification decisions own independent evidence and admission gate; functional units medium and no existing public compatibility guarantee.",
            "contracts": [
                "independent-role-evidence",
                "qualification-before-coordinator",
            ],
            "difference": "Hard contract input predicates explicitly specified; no implementation body. Candidate additionally supplies unrelated semantic examples"
            if examples
            else "Hard contract input predicates explicitly specified; no preferred editing sequence or implementation body, no rework or solution examples",
            "candidate_axis": "Only packet semantic examples; source/tests/config/runtime unchanged"
            if examples
            else None,
            "control": "formal-transfer-1 actual outcomes, kept separately"
            if examples
            else None,
            "per_unit_stop": "First candidate round failure means do not replay its second round; no further same-work candidates"
            if examples
            else None,
            "criterion": "Four accepted units plus both independent Explorer calls before expanding qualification; any failure remains denominator",
            "calls_max": 4,
            "weekly_ceiling": 40,
            "coordinator_started": False,
            "unchanged": [
                "models",
                "sampling",
                "context",
                "budgets",
                "runtime",
                "system prompts",
            ],
            "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--examples", action="store_true")
    prepare(parser.parse_args().examples)
