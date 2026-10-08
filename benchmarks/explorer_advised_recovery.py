"""Single local-Explorer repair recommendation, followed by gated inherited work."""

import argparse
import subprocess
import sys
import time
from pathlib import Path

from capability_fit import WORK, load_worker, write
from inherited_context_recovery import digest, read

BASE = WORK / "roleq-explorer-advice-1"
ROOT = WORK / "roleq-protocol-transfer-1/runs/v1/canonical1/window-groups-round-1"
SNAPSHOT = WORK / "roleq-prefetch-guard-candidate-1"
QUESTION = (
    "Read src/product/target.py::groups and tests/test_target.py, including normal "
    "positive widths and test_exact_integer_boundary. What minimal guard change "
    "would reject bool and IntegerSubclass while retaining ordinary positive int "
    "widths and nonmutation? Cite the actual current guard and protected assertions. "
    "Provide a concrete Python guard expression as a read-only research recommendation, "
    "explain its behavior on those inputs, and state uncertainty. Do not edit or "
    "claim to have executed tests. This is one focused repair question, not a broad audit."
)


def prepare():
    BASE.mkdir(exist_ok=False)
    parent = read(ROOT / ".agent/fresh-context-a2.json")
    config = read(ROOT / ".agent/config.json")
    config["explorer_mode"] = "investigate"
    write(BASE / "explorer-config.json", config)
    write(
        BASE / "plan.json",
        {
            "feature_id": "local-role-complementarity-diagnostic",
            "unit_id": parent["unit_id"],
            "task_id": parent["task_id"],
            "parent_run_id": parent["run_id"],
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "risk_rationale": "Qualification authority; never convert guided recovery to independent success",
            "dependencies": [parent["run_id"]],
            "owned_contract_ids": ["unchanged-contract", "local-advice-provenance"],
            "classification": "Local-Explorer-guided recovery, not initial qualification",
            "question": QUESTION,
            "max_calls": {"explorer": 1, "coder": 1, "reviewer": "only after handoff"},
            "difference": "Earlier Explorer supplied causal notes only; this call explicitly requests an executable recommendation. Primary may verify but must not invent the implementation answer.",
            "stop": "No retry; require Primary-verified useful recommendation before Coder. Stop at weekly used 40 percent.",
            "coordinator_started": False,
            "driver_sha256": digest(Path(__file__)),
            "input_hashes": {
                p.relative_to(ROOT).as_posix(): digest(p)
                for p in ROOT.rglob("*.py")
                if ".agent" not in p.parts
            },
            "config_sha256": digest(ROOT / ".agent/config.json"),
            "explorer_config_sha256": digest(BASE / "explorer-config.json"),
        },
    )


def check(plan):
    if digest(Path(__file__)) != plan["driver_sha256"]:
        raise ValueError("driver drift")
    for relative, sha in read(SNAPSHOT / "freeze.json")["files"].items():
        if digest(SNAPSHOT / relative) != sha:
            raise ValueError("runtime drift")
    for relative, sha in plan["input_hashes"].items():
        if digest(ROOT / relative) != sha:
            raise ValueError("draft or protected input drift")
    if digest(ROOT / ".agent/config.json") != plan["config_sha256"]:
        raise ValueError("config drift")
    if digest(BASE / "explorer-config.json") != plan["explorer_config_sha256"]:
        raise ValueError("explorer config drift")


def run(role):
    plan = read(BASE / "plan.json")
    check(plan)
    if role == "explorer":
        command = [
            str(SNAPSHOT / ".local-agents/local-explore.py"),
            "--task",
            QUESTION,
            "--task-id",
            plan["task_id"],
            "--config",
            str(BASE / "explorer-config.json"),
            "--report",
            str(ROOT / ".agent/explorer-advice-a3.json"),
            "--full-report",
        ]
    else:
        approval = read(BASE / "primary-advice-review.json")
        if approval.get("decision") != "use_local_recommendation":
            raise ValueError("no accepted local recommendation")
        report = ROOT / ".agent/explorer-advice-a3.json"
        if digest(report) != approval["explorer_report_sha256"]:
            raise ValueError("advice changed")
        parent = read(ROOT / ".agent/fresh-context-a2.json")
        child = {k: parent[k] for k in ("schema_version", "task_id", "unit_id")}
        child.update(
            run_id=parent["run_id"].replace("-a2", "-a3"),
            parent_run_id=parent["run_id"],
            preserve_contract=True,
            attempt=3,
            packet_revision=3,
            plan_revision=1,
            review_feedback=[
                {"text": approval["verbatim_local_advice"], "verify_in_review": False}
            ],
        )
        worker = load_worker(SNAPSHOT)
        resolved = worker.resolve_inherited_packet(ROOT, child)
        worker.validate_packet(resolved)
        if resolved["_inheritance"]["parent_input_state"]["status"] != "unchanged":
            raise ValueError("parent input drift")
        path = ROOT / ".agent/explorer-advised-a3.json"
        write(path, child)
        command = [
            str(SNAPSHOT / ".local-agents/local-unit.py"),
            "--packet",
            str(path),
            "--config",
            str(ROOT / ".agent/config.json"),
            "--coder-report",
            str(ROOT / ".agent/explorer-advised-coder-a3.json"),
            "--review-report",
            str(ROOT / ".agent/explorer-advised-reviewer-a3.json"),
        ]
    write(BASE / f"{role}-started.json", {"started_at": time.time()})
    start = time.monotonic()
    result = subprocess.run(
        [sys.executable, *command],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=1200,
        check=False,
    )
    record = {
        "exit": result.returncode,
        "seconds": time.monotonic() - start,
        "output": result.stdout + result.stderr,
        "primary_accepted": False,
    }
    write(BASE / f"{role}-result.json", record)
    print(record, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "explorer", "coder"))
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    else:
        run(args.action)
