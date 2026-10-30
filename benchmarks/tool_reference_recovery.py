"""Current-input validation recovery, preserving a real failed fresh call."""

import argparse
import importlib.util
import shutil

import tool_contract_rework as repair
import tool_handshake_recovery as handshake
from capability_fit import KIT, WORK, load_worker, write
from inherited_context_recovery import digest, read
from layer_isolation import command, verify_hashes
from tool_awaitable_trial import PYTHON, TARGET


def configure():
    repair.BASE = WORK / "tool-context-reference-1"
    repair.SNAPSHOT = WORK / "tool-context-reference-runtime-10"
    repair.FIXTURE_VERSION = 10
    handshake.ROOT = repair.BASE / "fresh-1"
    handshake.SNAPSHOT = repair.SNAPSHOT


def prepare():
    handshake.prepare()
    root = handshake.ROOT
    # No import of a successful oracle and no source edits: the actual failed
    # call's draft was independently checked. Canonical inheritance retains it.
    shutil.copyfile(
        root / ".agent/handshake-a2.json", root / ".agent/scope-rework-a2.json"
    )
    repair.register_actual("fresh-1")


def register_corrected():
    root = handshake.ROOT
    child = read(root / ".agent/handshake-a2.json")
    child["review_feedback"] = [
        {
            "text": "The actual prior call changed source but its final model response was truncated before validating current final inputs. Primary independently checked the actual draft; this is not Coder validation evidence. Re-read current implementation against all inherited contracts and VALIDATE current inputs with truthful correctly shaped contract_check. No production edit is requested unless current validation demonstrates a defect. Do not infer prior evidence remains current. No scope, contract, test or budget expansion.",
            "verify_in_review": False,
        }
    ]
    worker = load_worker(repair.SNAPSHOT)
    resolved = worker.resolve_inherited_packet(root, child)
    worker.validate_packet(resolved)
    if resolved["_inheritance"]["parent_input_state"]["status"] != "unchanged":
        raise ValueError("parent draft drift")
    write(root / ".agent/reference-recovery-a2.json", child)
    write(
        root / ".agent/reference-recovery-inputs-a2.json",
        {
            "files": {
                name: digest(root / name)
                for name in (
                    ".agent/reference-recovery-a2.json",
                    ".agent/scope-rework-config-a2.json",
                )
            },
            "source_sha256": digest(root / TARGET),
            "operator_preparation": "Unused handshake/scope preparation contained an old scenario's incorrect missing-order description. Never invoked; correct feedback has a new immutable packet path. No model failure credit.",
        },
    )


def run():
    root = handshake.ROOT
    verify_hashes(
        root / "reference", read(repair.BASE / "registration.json")["reference_files"]
    )
    facts = read(root / ".agent/reference-recovery-inputs-a2.json")
    verify_hashes(root, {TARGET: facts["source_sha256"], **facts["files"]})
    verify_hashes(repair.SNAPSHOT, read(repair.SNAPSHOT / "freeze.json")["files"])
    config = root / ".agent/scope-rework-config-a2.json"
    result = command(
        root,
        [
            str(PYTHON),
            "-B",
            str(KIT / "benchmarks/coder_native_repair_history_adapter.py"),
            "--snapshot",
            str(repair.SNAPSHOT),
            "--packet",
            str(root / ".agent/reference-recovery-a2.json"),
            "--config",
            str(config),
            "--report",
            str(root / ".agent/coder-a2.json"),
        ],
        timeout=1500,
    )
    write(root / ".agent/reference-recovery-invocation-a2.json", result)
    report = read(root / ".agent/coder-a2.json")
    if report["status"] == "ready_for_review":
        spec = importlib.util.spec_from_file_location(
            "reference_recovery_unit", repair.SNAPSHOT / ".local-agents/local-unit.py"
        )
        unit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(unit)
        identity = unit.verify_handoff(root, report)
        request = root / ".agent/review-request-a2.json"
        write(
            request,
            {
                "schema_version": 1,
                **identity,
                "review_id": identity["run_id"] + "-review",
            },
        )
        invoked = command(
            root,
            [
                str(PYTHON),
                "-B",
                str(repair.SNAPSHOT / ".local-agents/local-review.py"),
                "--request",
                str(request),
                "--config",
                str(config),
                "--report",
                str(root / ".agent/reviewer-a2.json"),
            ],
            timeout=900,
        )
        write(root / ".agent/reviewer-invocation-a2.json", invoked)
    print({"coder_status": report["status"], "fresh_success_credit": False})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "register-corrected", "run"))
    args = parser.parse_args()
    configure()
    {"prepare": prepare, "register-corrected": register_corrected, "run": run}[
        args.action
    ]()
