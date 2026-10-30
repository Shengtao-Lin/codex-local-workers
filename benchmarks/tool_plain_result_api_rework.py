"""One narrower API-evidence repair after the actual inherited heuristic failed."""

import argparse
import importlib.util

from capability_fit import KIT, WORK, load_worker, write
from inherited_context_recovery import digest, read
from layer_isolation import command, verify_hashes
from tool_awaitable_trial import PYTHON, TARGET

ROOT = WORK / "tool-native-nudge-1/fresh-1"
SNAPSHOT = WORK / "tool-plain-result-runtime-12"


def prepare():
    parent_id = "tool-native-nudge-1-fresh-1-a2"
    parent_archive = ROOT / ".agent/tasks/tool-native-nudge-1-fresh-1/runs" / parent_id
    if read(parent_archive / "review.json")["decision"] != "rework":
        raise ValueError("actual Primary rework required")
    child = {
        "schema_version": 2,
        "task_id": "tool-native-nudge-1-fresh-1",
        "unit_id": "awaitable-tools",
        "run_id": "tool-native-nudge-1-fresh-1-a3",
        "parent_run_id": parent_id,
        "preserve_contract": True,
        "attempt": 3,
        "packet_revision": 7,
        "plan_revision": 1,
        "review_feedback": [
            {
                "finding_id": "plain-result-1",
                "contract_id": "resolved-output",
                "source_anchor": "async def execute",
                "verify_in_review": True,
                "text": "Your actual a2 only excludes classes; the same normal mapping instance with __await__ = None still fails. Primary verified installed Python 3.12 inspect.py lines 468-473: inspect.isawaitable is the documented predicate for values accepted by await, using coroutine/flagged-generator/Awaitable checks rather than attribute presence. inspect is already imported in your source. This is dependency API evidence, not a replacement patch. Repair true awaitability classification, preserving plain sync results, invocation once, thread/context ownership, direct async final identity and existing single deadline/error/hook behavior. No scope, contract, tests or budget changes.",
            }
        ],
    }
    worker = load_worker(SNAPSHOT)
    resolved = worker.resolve_inherited_packet(ROOT, child)
    worker.validate_packet(resolved)
    if resolved["_inheritance"]["parent_input_state"]["status"] != "unchanged":
        raise ValueError("parent source drift")
    write(ROOT / ".agent/plain-api-a3.json", child)
    config = read(ROOT / ".agent/scope-rework-config-a2.json")
    config["validation_profiles"]["project-strict"]["pytest_argv"][-1] = (
        "--basetemp=" + str(ROOT / ".agent/worker-a3-temp")
    )
    write(ROOT / ".agent/plain-api-config-a3.json", config)
    write(
        ROOT / ".agent/plain-api-registration-a3.json",
        {
            "files": {
                p: digest(ROOT / p)
                for p in (
                    ".agent/plain-api-a3.json",
                    ".agent/plain-api-config-a3.json",
                    TARGET,
                )
            },
            "driver_sha256": digest(KIT / "benchmarks/tool_plain_result_api_rework.py"),
            "adapters": read(ROOT / ".agent/scope-rework-registration-a2.json")[
                "adapters"
            ],
            "credit": "Source-backed Primary-guided a3, not fresh success. Historical a1/a2 and independent failed probes retained.",
        },
    )


def run():
    facts = read(ROOT / ".agent/plain-api-registration-a3.json")
    verify_hashes(ROOT, facts["files"])
    verify_hashes(
        KIT / "benchmarks",
        {
            "tool_plain_result_api_rework.py": facts["driver_sha256"],
            **facts["adapters"],
        },
    )
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    config = ROOT / ".agent/plain-api-config-a3.json"
    invoked = command(
        ROOT,
        [
            str(PYTHON),
            "-B",
            str(KIT / "benchmarks/coder_native_repair_history_adapter.py"),
            "--snapshot",
            str(SNAPSHOT),
            "--packet",
            str(ROOT / ".agent/plain-api-a3.json"),
            "--config",
            str(config),
            "--report",
            str(ROOT / ".agent/coder-a3.json"),
        ],
        timeout=1500,
    )
    write(ROOT / ".agent/plain-api-invocation-a3.json", invoked)
    report = read(ROOT / ".agent/coder-a3.json")
    if report["status"] == "ready_for_review":
        spec = importlib.util.spec_from_file_location(
            "plain_api_unit", SNAPSHOT / ".local-agents/local-unit.py"
        )
        unit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(unit)
        identity = unit.verify_handoff(ROOT, report)
        request = ROOT / ".agent/review-request-a3.json"
        write(
            request,
            {
                "schema_version": 1,
                **identity,
                "review_id": identity["run_id"] + "-review",
            },
        )
        review = command(
            ROOT,
            [
                str(PYTHON),
                "-B",
                str(SNAPSHOT / ".local-agents/local-review.py"),
                "--request",
                str(request),
                "--config",
                str(config),
                "--report",
                str(ROOT / ".agent/reviewer-a3.json"),
            ],
            timeout=900,
        )
        write(ROOT / ".agent/reviewer-invocation-a3.json", review)
    print({"coder_status": report["status"], "fresh_success_credit": False})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "run"))
    args = parser.parse_args()
    {"prepare": prepare, "run": run}[args.action]()
