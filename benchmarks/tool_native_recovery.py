"""True canonical inheritance with an explicitly reviewed test-only input revision."""

import argparse
import shutil

from capability_fit import WORK, load_worker, write
from inherited_context_recovery import digest, read
from layer_isolation import command, verify_hashes
from tool_awaitable_trial import PYTHON, TARGET
from tool_compatibility_trial import EXTRA, FROZEN, SNAPSHOT

ORIGIN = WORK / "tool-native-history-1/history-2"
ROOT = WORK / "tool-native-recovery-1"


def prepare():
    provenance = read(FROZEN / "provenance.json")
    verify_hashes(FROZEN, provenance["files"])
    report = read(ORIGIN / ".agent/coder.json")
    identity = report["identity"]
    task_relative = ".agent/tasks/" + identity["task_id"]
    parent = ORIGIN / task_relative / "runs" / identity["run_id"]
    if read(parent / "review.json")["decision"] != "replan":
        raise ValueError("Primary replan required before canonical recovery")
    ROOT.mkdir(parents=True, exist_ok=False)
    for path in provenance["files"]:
        target = ROOT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile((ORIGIN if path == TARGET else FROZEN) / path, target)
    shutil.copytree(ORIGIN / task_relative, ROOT / task_relative)
    shutil.copyfile(ORIGIN / ".agent/pyright.json", ROOT / ".agent/pyright.json")
    original_packet = read(parent / "packet.json")
    child = {
        key: original_packet[key] for key in ("schema_version", "task_id", "unit_id")
    }
    child.update(
        run_id=identity["run_id"].removesuffix("-a1") + "-a2",
        parent_run_id=identity["run_id"],
        preserve_contract=True,
        attempt=2,
        packet_revision=original_packet["packet_revision"] + 1,
        plan_revision=original_packet["plan_revision"],
        review_feedback=[
            {
                "text": "Primary accepted the prior test-preparation revision request. Only the protected async preservation test's import grouping and blocking provenance I/O placement were fixed; its assertion and input are unchanged. Production code is unchanged from your real prior artifact. This is inherited recovery, not a fresh baseline. Read current source against every original contract, then VALIDATE phase final with truthful contract_check. No implementation edit is requested; passing validation permits only FINISH_SUCCESS before automatic independent Reviewer.",
                "verify_in_review": False,
            }
        ],
    )
    worker = load_worker(SNAPSHOT)
    resolved = worker.resolve_inherited_packet(ROOT, child)
    worker.validate_packet(resolved)
    if resolved["_inheritance"]["parent_input_state"]["drifted_paths"] != [EXTRA]:
        raise ValueError("only the reviewed protected test correction may drift")
    config = read(ORIGIN / ".agent/compat-config.json")
    config["validation_profiles"]["project-strict"]["pytest_argv"][-1] = (
        "--basetemp=" + str(ROOT / ".agent/worker-temp")
    )
    write(ROOT / ".agent/packet.json", child)
    write(ROOT / ".agent/config.json", config)
    write(
        ROOT / ".agent/registration.json",
        {
            "parent_archive_origin": str(parent),
            "copied_parent_is_new_execution": False,
            "copied_parent_hashes": {
                p.relative_to(parent).as_posix(): digest(p)
                for p in parent.rglob("*")
                if p.is_file()
            },
            "source_sha256": digest(ROOT / TARGET),
            "only_changed_protected_input": EXTRA,
            "credit": "Recovered actual native artifact; not new independent implementation or fresh success",
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
            str(ROOT / ".agent/packet.json"),
            "--config",
            str(ROOT / ".agent/config.json"),
            "--coder-report",
            str(ROOT / ".agent/coder-a2.json"),
            "--review-report",
            str(ROOT / ".agent/reviewer-a2.json"),
        ],
        timeout=1500,
    )
    write(ROOT / ".agent/invocation-a2.json", result)
    print(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "run"))
    (prepare if parser.parse_args().action == "prepare" else run)()
