"""Recover an ordering-ack handoff defect without changing validated code."""

import argparse
import json

from capability_fit import WORK, freeze, load_worker, write
from inherited_context_recovery import digest, read
from layer_isolation import command, verify_hashes
from tool_awaitable_trial import PYTHON

ROOT = WORK / "tool-awaitable-3/fresh-2"
SNAPSHOT = WORK / "tool-awaitable-runtime-4"


def prepare():
    if not SNAPSHOT.exists():
        freeze(SNAPSHOT.name)
    parent_report = read(ROOT / ".agent/coder.json")
    archive = ROOT / parent_report["evidence_refs"]["run_archive"]
    parent = read(archive / "packet.json")
    if read(archive / "review.json")["decision"] != "replan":
        raise ValueError("Primary replan required")
    child = {key: parent[key] for key in ("schema_version", "task_id", "unit_id")}
    child.update(
        run_id=parent["run_id"].removesuffix("-a1") + "-a2",
        parent_run_id=parent["run_id"],
        preserve_contract=True,
        attempt=2,
        packet_revision=parent["packet_revision"] + 1,
        plan_revision=1,
        review_feedback=[
            {
                "text": "Prior handoff was mechanically rejected because ordering acknowledgement was missing, not because tests failed. Re-read the unchanged actual implementation against every original contract and validate current inputs with correctly shaped, truthful contract_check. No production edit is requested; do not infer prior passing evidence is still current. No scope or contract expansion.",
                "verify_in_review": False,
            }
        ],
    )
    worker = load_worker(SNAPSHOT)
    resolved = worker.resolve_inherited_packet(ROOT, child)
    worker.validate_packet(resolved)
    if resolved["_inheritance"]["parent_input_state"]["status"] != "unchanged":
        raise ValueError("unexpected source drift")
    config = read(ROOT / ".agent/config.json")
    config["coder_post_edit_validation_hint"] = True
    config["validation_profiles"]["project-strict"]["pytest_argv"][-1] = (
        "--basetemp=" + str(ROOT / ".agent/worker-a2-temp")
    )
    write(ROOT / ".agent/handshake-a2.json", child)
    write(ROOT / ".agent/handshake-config-a2.json", config)
    write(
        ROOT / ".agent/handshake-registration-a2.json",
        {
            "packet_sha256": digest(ROOT / ".agent/handshake-a2.json"),
            "source_sha256": digest(ROOT / "src/agent_runtime/tools/registry.py"),
            "credit": "Recovered actual Coder artifact, not new independent implementation",
            "runtime": str(SNAPSHOT),
            "weekly_ceiling": 23,
        },
    )


def run():
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    result = command(
        ROOT,
        [
            str(PYTHON),
            "-B",
            str(SNAPSHOT / ".local-agents/local-unit.py"),
            "--packet",
            str(ROOT / ".agent/handshake-a2.json"),
            "--config",
            str(ROOT / ".agent/handshake-config-a2.json"),
            "--coder-report",
            str(ROOT / ".agent/coder-a2.json"),
            "--review-report",
            str(ROOT / ".agent/reviewer-a2.json"),
        ],
        timeout=1500,
    )
    write(ROOT / ".agent/handshake-invocation-a2.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "run"))
    args = parser.parse_args()
    (prepare if args.action == "prepare" else run)()
