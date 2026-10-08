"""Frozen mixed-goal preparation and explicitly authorized supervised steps.

Never accepts units/features, repairs failed workers, or writes source projects.
Primary must inspect canonical evidence and record acceptance between units.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import localization_route_smoke as ROUTE
from complex_fixture_cases import extend

KIT = Path(__file__).resolve().parents[1]
CORPUS = KIT / "benchmarks/fixtures/mixed-features-v1.json"
WORK = KIT / "benchmarks/work/mixed-v1"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)


def prepare(case_id, round_number, config_path, batch="candidate-1", suite="v1"):
    corpus = read(CORPUS)
    if suite not in ("v1", "complex-v2"):
        raise ValueError("unknown suite")
    if suite == "complex-v2":
        corpus = extend(corpus)
    if round_number not in (1, 2):
        raise ValueError("only preregistered rounds 1 and 2 are allowed")
    case = next(case for case in corpus["cases"] if case["case_id"] == case_id)
    if not batch or any(
        char not in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in batch
    ):
        raise ValueError("invalid batch identifier")
    root = WORK / suite / batch / f"{case_id}-round-{round_number}"
    root.mkdir(parents=True, exist_ok=False)
    for relative, content in case["files"].items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\npythonpath = ["src"]\n'
        '[tool.ruff]\nline-length = 100\ntarget-version = "py311"\n'
        '[tool.ruff.lint]\nselect = ["E4", "E7", "E9", "F"]\n',
        encoding="utf-8",
    )
    formatted = subprocess.run(
        [sys.executable, "-m", "ruff", "format", "src", "tests"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    # Freeze an explicit project rule set, rather than inheriting host defaults.
    # Protected fixture tests must pass before a worker can be blamed for lint.
    subprocess.run(
        [sys.executable, "-m", "ruff", "check", "src", "tests"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    config = copy.deepcopy(read(config_path))
    config.update(
        python=sys.executable, explorer_mode="locate", single_model_residency=True
    )
    config["validation_profiles"] = {
        "mixed-strict": {
            "python": sys.executable,
            "compile": True,
            "pytest_argv": ["-B", "-m", "pytest"],
            "commands": [
                {
                    "id": "ruff-format",
                    "argv": [
                        "{python}",
                        "-m",
                        "ruff",
                        "format",
                        "--check",
                        "src",
                        "tests",
                    ],
                },
                {
                    "id": "ruff-check",
                    "argv": ["{python}", "-m", "ruff", "check", "src", "tests"],
                },
            ],
        }
    }
    write(root / ".agent/config.json", config)
    packets = []
    plans = []
    task_id = f"mixed-{suite}-{batch}-{case_id}-r{round_number}"
    for unit in case["units"]:
        writable = unit.get("paths", [unit["path"]])
        packet = {
            "schema_version": 2,
            "task_id": task_id,
            "feature_id": task_id,
            "unit_id": unit["unit_id"],
            "run_id": f"{task_id}-{unit['unit_id']}-a1",
            "attempt": 1,
            "plan_revision": 1,
            "packet_revision": 1,
            "goal": unit["contract"],
            "risk": {
                "feature": case["feature_risk"],
                "unit": unit["risk"],
                "integration": case["integration_risk"],
                "reasons": [
                    "Cross-unit input/response compatibility; risk retained at each owned contract boundary."
                ],
            },
            "dependencies": unit["dependencies"],
            "owned_contract_ids": [unit["unit_id"]],
            "scope": {
                "read": ["src", "tests"],
                "modify": writable,
                "create": [],
                "readonly": [p for p in case["files"] if p not in writable],
                "forbidden": [".git", ".agent", ".local-agents"],
            },
            "edit_targets": [
                {
                    "path": path,
                    "anchor": unit.get("anchors", {}).get(path, unit["anchor"]),
                }
                for path in writable
            ],
            "focused_tests": unit["tests"],
            "supplemental_tests": [],
            "required_behavior": [
                {
                    "id": unit["unit_id"],
                    "risk_floor": unit["risk"],
                    "text": unit["contract"],
                }
            ],
            "required_order": unit.get("required_order", []),
            "forbidden_orderings": unit.get("forbidden_orderings", []),
            "contract_check_required": True,
            "acceptance_criteria": [
                {
                    "id": "protected",
                    "text": "Protected tests and configured checks pass without weakening the contract.",
                }
            ],
            "acceptance_scenarios": copy.deepcopy(
                unit.get(
                    "acceptance_scenarios",
                    [
                        {
                            "id": "normal",
                            "text": "Normal behavior matches the protected assertions.",
                            "observables": {"protected_normal_assertions": True},
                        },
                        {
                            "id": "boundary",
                            "text": "Protected error and boundary assertions pass.",
                            "observables": {"protected_boundary_assertions": True},
                        },
                    ],
                )
            ),
            "validation_profile": "mixed-strict",
            "implementation_guidance": [],
            "review_feedback": [],
        }
        packets.append(packet)
        plans.append(ROUTE.primary_plan_for_packet(packet))
    plan = plans[0]
    plan["contracts"] = [contract for item in plans for contract in item["contracts"]]
    plan["units"] = [unit for item in plans for unit in item["units"]]
    write(root / ".agent/feature-plan.json", plan)
    write(root / ".agent/run-refs.json", {})
    for packet in packets:
        unit_id = packet["unit_id"]
        write(root / f".agent/{unit_id}-reference.json", packet)
        write(
            root / f".agent/{unit_id}-context.json",
            {
                "identity": {
                    key: packet[key]
                    for key in ("unit_id", "run_id", "attempt", "packet_revision")
                },
                "goal": packet["goal"],
                "navigation_targets": packet["edit_targets"],
                "question": "Propose one bounded unit within Primary ceilings. Preserve protected tests and accepted dependencies; no supplemental tests or scope expansion.",
            },
        )
        write(
            root / f".agent/{unit_id}-request.json",
            {
                "task_id": task_id,
                "unit_id": unit_id,
                "capability": "localization_only",
                "question": f"Locate the existing {packet['edit_targets'][0]['anchor']} implementation in {packet['scope']['modify'][0]} and the relevant protected assertions in {packet['focused_tests'][0]}. Read both; return exact ranges only, not a repair prediction.",
            },
        )
    baseline = subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "tests", "-q"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    files = {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
        and ".agent" not in path.parts
        and "__pycache__" not in path.parts
        and ".pytest_cache" not in path.parts
        and ".ruff_cache" not in path.parts
    }
    write(
        root / "freeze.json",
        {
            "case": case_id,
            "round": round_number,
            "origin": case["origin"],
            "corpus_sha256": hashlib.sha256(CORPUS.read_bytes()).hexdigest(),
            "suite": suite,
            "drivers": {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in (
                    Path(__file__),
                    KIT / "benchmarks/complex_fixture_cases.py",
                )
            },
            "files": files,
            "runtime": ROUTE.runtime_manifest(config),
            "baseline_exit": baseline.returncode,
            "baseline_output": baseline.stdout + baseline.stderr,
            "format_output": formatted.stdout,
            "primary_accepted": False,
            "cloud_tokens": None,
        },
    )
    if baseline.returncode != 1 or "failed" not in baseline.stdout:
        raise ValueError(
            "baseline must collect tests and fail assertions, not pass or collection-error"
        )
    return {
        "root": str(root),
        "baseline_exit": baseline.returncode,
        "units": [p["unit_id"] for p in packets],
    }


def step(root, unit_id):
    root = root.resolve()
    root.relative_to(WORK.resolve())
    config = read(root / ".agent/config.json")
    frozen = read(root / "freeze.json")
    for name, digest in frozen.get("drivers", {}).items():
        if (
            hashlib.sha256((KIT / "benchmarks" / name).read_bytes()).hexdigest()
            != digest
        ):
            raise ValueError("benchmark driver changed after freeze")
    if hashlib.sha256(CORPUS.read_bytes()).hexdigest() != frozen["corpus_sha256"]:
        raise ValueError("corpus changed after freeze")
    for relative, digest in frozen["files"].items():
        if (
            relative.startswith("tests/")
            and hashlib.sha256((root / relative).read_bytes()).hexdigest() != digest
        ):
            raise ValueError("protected fixture changed after freeze")
    if ROUTE.runtime_manifest(config) != frozen["runtime"]:
        raise ValueError("runtime/config changed after freeze")
    plan = read(root / ".agent/feature-plan.json")
    if unit_id not in {unit["unit_id"] for unit in plan["units"]}:
        raise ValueError("unapproved unit")
    spec = importlib.util.spec_from_file_location(
        "mixed_contract", KIT / ".local-agents/coordinator-contract.py"
    )
    assert spec and spec.loader
    contract = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = contract
    spec.loader.exec_module(contract)
    state = contract.load_coordinator_state(
        plan, root, root / ".agent/coordinator" / plan["feature_id"] / "state.json"
    )
    command = [
        sys.executable,
        "-B",
        str(KIT / ".local-agents/coordinator-supervised.py"),
        "--plan",
        str(root / ".agent/feature-plan.json"),
        "--context",
        str(root / f".agent/{unit_id}-context.json"),
        "--request",
        str(root / f".agent/{unit_id}-request.json"),
        "--run-refs",
        str(root / ".agent/run-refs.json"),
        "--config",
        str(root / ".agent/config.json"),
        "--authorize-step",
        "--expected-sequence",
        str(state["sequence"]),
        "--manage-exploration",
    ]
    return subprocess.run(command, cwd=root, check=False).returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--case", required=True)
    prep.add_argument("--round", type=int, required=True)
    prep.add_argument("--batch", default="candidate-1")
    prep.add_argument("--suite", choices=("v1", "complex-v2"), default="v1")
    prep.add_argument("--config", type=Path, default=KIT / ".local-agents/config.json")
    run = commands.add_parser("step")
    run.add_argument("--root", type=Path, required=True)
    run.add_argument("--unit", required=True)
    run.add_argument("--authorize-step", action="store_true", required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        print(
            json.dumps(
                prepare(args.case, args.round, args.config, args.batch, args.suite),
                indent=2,
            )
        )
        return 0
    return step(args.root, args.unit)


if __name__ == "__main__":
    raise SystemExit(main())
