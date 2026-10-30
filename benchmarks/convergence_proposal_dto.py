"""Same frozen D1 briefs, smaller protocol, unchanged decomposition rubric."""

import argparse
import ast
import shutil
from pathlib import Path

import convergence_decomposition as previous
from convergence_coder import KIT, save
from convergence_followup import BASE
from system_convergence import read_object, ref, sha256

ROOT = BASE / "decomposition"
RUNTIME = BASE / "coordinator-kit/.local-agents"
OLD = KIT / "benchmarks/work/system-convergence/d1-20261010-1"


def catalog(brief, root):
    selectors = {
        "classification-shapes": ["tests/test_classification_shapes.py"],
        "attribute-snapshot": ["tests/test_attribute_names.py"],
        "normalized-key": [
            "tests/test_roundtrip.py::test_rejection_and_mapping_not_mutated"
        ],
        "lookup-roundtrip": ["tests/test_roundtrip.py"],
        "accepted-input": ["tests/test_atomic.py"],
        "atomic-output": ["tests/test_atomic.py"],
        "presence-wrapper": ["tests/test_wrapper.py"],
        "unspecified-endpoint": ["tests/test_unknown.py"],
    }
    result = {}
    for contract in brief["contracts"]:
        ident = contract["id"]
        tests = selectors[ident]
        scenarios = []
        for selector in tests:
            path, _, selected = selector.partition("::")
            source = (root / path).read_text(encoding="utf-8")
            for node in ast.parse(source).body:
                if (
                    isinstance(node, ast.FunctionDef)
                    and node.name.startswith("test_")
                    and (not selected or selected == node.name)
                ):
                    scenarios.append(
                        {
                            "id": ident + "-" + node.name.replace("_", "-"),
                            "text": ast.get_source_segment(source, node),
                            "observables": {
                                "protected_test": path + "::" + node.name,
                                "expected": "Original protected assertions must pass; no semantic confirmation inferred",
                            },
                        }
                    )
        result[ident] = {
            "acceptance_criteria": [{"id": ident, "text": contract["text"]}],
            "acceptance_scenarios": scenarios,
            "required_order": [],
            "forbidden_orderings": [],
            "validation_profile": brief["validation_profile"],
            "required_focused_tests": tests,
        }
    return result


def prepare():
    original = read_object(OLD / "registration.json")
    briefs = []
    for item in original["briefs"]:
        source = Path(item["root"])
        root = ROOT / "fixtures" / item["id"]
        root.mkdir(parents=True, exist_ok=False)
        brief = read_object(source / item["brief"]["path"])
        for relative, digest in brief["source_hashes"].items():
            assert sha256(source / relative) == digest
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / relative, target)
        brief["feature_id"] = "dto-" + item["id"]
        brief["task_id"] = "dto-" + item["id"]
        brief["acceptance_catalog"] = catalog(brief, root)
        save(root / ".agent/brief.json", brief)
        save(
            root / ".agent/context.json", read_object(source / item["context"]["path"])
        )
        briefs.append(
            {
                **item,
                "root": str(root),
                "brief": ref(root, ".agent/brief.json"),
                "context": ref(root, ".agent/context.json"),
                "new_same_task_not_previously_exposed": False,
                "exposure": "Same previously registered brief; new protocol comparison, not blind novel-task credit",
            }
        )
    save(ROOT / "config.json", read_object(OLD / "config.json"))
    save(
        ROOT / "registration.json",
        {
            **original,
            "briefs": briefs,
            "driver": ref(KIT, "benchmarks/convergence_decomposition.py"),
            "wrapper": ref(KIT, "benchmarks/convergence_proposal_dto.py"),
            "config": ref(ROOT, "config.json"),
            "runtime": [
                ref(RUNTIME, p.relative_to(RUNTIME).as_posix())
                for p in RUNTIME.rglob("*.py")
            ],
            "weekly_used_start": 1,
            "weekly_used_ceiling": 15,
            "candidate": "small-proposal-trusted-materialization-1",
            "original_registration": ref(
                KIT, (OLD / "registration.json").relative_to(KIT).as_posix()
            ),
            "primary_catalog_extra_preparation_cost": "AST extraction plus Primary review of original protected assertion functions; tokens/time unmeasured",
            "old_standard_unchanged": True,
        },
    )


def run(cell):
    registration = read_object(ROOT / "registration.json")
    assert sha256(Path(__file__)) == registration["wrapper"]["sha256"]
    previous.BASE, previous.RUNTIME = ROOT, RUNTIME
    previous.run(cell)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("cell", nargs="?")
    args = parser.parse_args()
    prepare() if args.action == "prepare" else run(args.cell)
