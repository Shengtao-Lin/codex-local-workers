"""One explicit inherited recovery per frozen D2 feature; no runtime change."""

import argparse
from pathlib import Path

import convergence_execution as core
import convergence_execution_fixture as fixture
from convergence_coder import save
from system_convergence import read_object, sha256


def prepare(identity, unit_id, feedback):
    fixture.bind()
    core.verify_frozen()
    _, cell = core.entry(identity)
    root = Path(cell["root"])
    marker = root / ".agent/external-rework-1.json"
    if marker.exists():
        raise FileExistsError("one external feature recovery already spent")
    parent = read_object(root / (".agent/" + unit_id + "-packet.json"))
    coder = read_object(root / (".agent/" + unit_id + "-coder.json"))
    if coder["status"] != "failed":
        raise ValueError(
            "this entry only recovers an independently diagnosed Coder failure"
        )
    expected = dict(cell["inputs"])
    refs = {
        p.stem: read_object(p) for p in (root / ".agent/accepted-refs").glob("*.json")
    }
    plan = read_object(root / ".agent/approval.json")["approved_plan"]
    accepted = core.module().CONTRACT.accepted_units_from_archives(plan, root, refs)
    unit = next(u for u in plan["units"] if u["unit_id"] == unit_id)
    if not set(unit["dependencies"]) <= accepted:
        raise ValueError("unaccepted dependency")
    for run_ref in refs.values():
        archive = (
            root / ".agent/tasks" / run_ref["task_id"] / "runs" / run_ref["run_id"]
        )
        for change in read_object(archive / "handoff.json")["changed_files"]:
            expected[change["path"]] = change["final_sha256"]
    for change in coder["changed_files"]:
        if change["path"] not in parent["scope"]["modify"]:
            raise ValueError("scope violation requires takeover")
        expected[change["path"]] = change["final_sha256"]
    core.module().assert_sources_current({"source_hashes": expected}, root)
    child = {
        k: parent[k] for k in ("schema_version", "task_id", "unit_id", "plan_revision")
    }
    child.update(
        run_id=parent["run_id"].removesuffix("a1") + "a2",
        attempt=2,
        packet_revision=2,
        parent_run_id=parent["run_id"],
        preserve_contract=True,
        review_feedback=[feedback],
    )
    path = root / (".agent/" + unit_id + "-rework-packet.json")
    save(path, child)
    worker = core.module().load("d2_rework_shape", "worker-runtime.py")
    resolved = worker.resolve_inherited_packet(root, child)
    core.module().CONTRACT.validate_unit_packet(plan, resolved)
    save(
        marker,
        {
            "unit_id": unit_id,
            "run_id": child["run_id"],
            "parent_run_id": parent["run_id"],
            "reason": coder["failure_reason"],
            "primary_feedback": feedback,
            "current_inputs": expected,
            "packet_sha256": sha256(path),
            "limits_contract_and_runtime_unchanged": True,
            "count": 1,
        },
    )


def run(identity):
    fixture.bind()
    core.verify_frozen()
    _, cell = core.entry(identity)
    root = Path(cell["root"])
    marker = read_object(root / ".agent/external-rework-1.json")
    unit = marker["unit_id"]
    packet = root / (".agent/" + unit + "-rework-packet.json")
    assert sha256(packet) == marker["packet_sha256"]
    core.module().assert_sources_current(
        {"source_hashes": marker["current_inputs"]}, root
    )
    core.command(
        root,
        [
            core.RUNTIME / "local-unit.py",
            "--packet",
            packet,
            "--config",
            root / ".agent/config.json",
            "--coder-report",
            root / (".agent/" + unit + "-rework-coder.json"),
            "--review-report",
            root / (".agent/" + unit + "-rework-reviewer.json"),
        ],
        root / (".agent/" + unit + "-rework-invocation.json"),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("identity")
    parser.add_argument("unit", nargs="?")
    parser.add_argument("--feedback")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.identity, args.unit, args.feedback)
    else:
        run(args.identity)
