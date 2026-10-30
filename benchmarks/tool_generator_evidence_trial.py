"""Prospective fresh atomic units with twenty protected tests; no oracle patch."""

import argparse
import copy
import importlib.util
import shutil

from capability_fit import KIT, WORK, load_worker, write
from inherited_context_recovery import digest, read
from layer_isolation import command, verify_hashes
from tool_awaitable_trial import PYTHON, TARGET

BASE = WORK / "tool-generator-evidence-28"
FROZEN = KIT / "benchmarks/fixtures/tool-awaitable-v14"
SNAPSHOT = WORK / "reviewer-all-lines-runtime-16"
TEMPLATE = WORK / "tool-plain-result-3/fresh-1/.agent"
REFERENCE = KIT / "benchmarks/fixtures/tool-library-reference-v1"
PROTOCOL = KIT / "benchmarks/fixtures/tool-library-reference-v2"
ARMS = ("candidate-1", "candidate-2")
TEST = "tests/unit/test_deadline_registration.py"
GENERATOR = "tests/unit/test_generator_coroutine.py"
ADAPTERS = (
    "native_coder_adapter.py",
    "coder_native_block_adapter.py",
    "coder_native_history_adapter.py",
    "coder_native_repair_history_adapter.py",
    "reviewer_required_tool_adapter.py",
    "reviewer_sampling_probe_adapter.py",
    "reviewer_staged_assessment_adapter.py",
    "reviewer_staged_final_gate_adapter.py",
    "reviewer_range_staged_adapter.py",
    "reviewer_dependency_evidence_adapter.py",
    "reviewer_dependency_investigation_adapter.py",
    "reviewer_catalog_staged_adapter.py",
    "reviewer_evidence_catalog_adapter_v2.py",
    "reviewer_anchored_catalog_adapter.py",
    "reviewer_contract_test_read_adapter.py",
    "reviewer_investigation_phase_adapter.py",
    "reviewer_wire_budget_adapter.py",
    "reviewer_boundary_analogy_adapter.py",
    "reviewer_assembled_request_adapter.py",
    "fixtures/reviewer-protocol-analogy-v1.json",
    "fixtures/reviewer_protocol_analogy_v1.py",
    "reviewer_citation_bundle_adapter.py",
    "reviewer_retained_evidence_v7_adapter.py",
    "reviewer_execution_phase_v2_adapter.py",
    "reviewer_visible_quote_compaction.py",
    "reviewer_retained_wire_v2_adapter.py",
    "fixtures/tool-awaitable-extra/test_generator_coroutine_portable_v3.py",
    "tool_generator_evidence_trial.py",
)


def register():
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    verify_hashes(PROTOCOL, read(PROTOCOL / "provenance.json")["files"])
    facts = read(WORK / "tool-deadline-fixture-2/registration.json")
    if not all(item["passed_preflight"] for item in facts["facts"].values()):
        raise ValueError("actual twenty-test positive/negative preflight required")
    write(
        BASE / "registration.json",
        {
            "arms": ARMS,
            "weekly_ceiling": 30,
            "fixture": "v14 original source with twenty unchanged protected tests plus independently reproduced legal generator-coroutine regression",
            "risk": "High feature/unit/integration: atomic public result/deadline/cancellation/context boundary; no split of invariant or lowered risk.",
            "axis": "Fresh original-source real units with same twenty-one tests, protected scope, models and budgets. Replace generic Coder analogy with bounded actual readonly CPython dependency source evidence already inside scope; not target code, expected patch, enforced implementation shape or model-selected navigation. Reviewer preserves visible evidence and presents necessary approved execution before assessment, handling core report-only nudge without empty required tools. Combined guided profile, not a causal factorial comparison or unguided baseline.",
            "explorer": "Already located same ToolRegistry and answered dependency semantics; no duplicate investigation or fabricated Explorer credit.",
            "credit": "New fresh C/R units, not replay of incomplete old source or guided recovery. Keep all prior failures and independent reviewer-negative denominators; no Coordinator release or savings inferred.",
            "files": {name: digest(KIT / "benchmarks" / name) for name in ADAPTERS},
            "template_files": {
                name: digest(TEMPLATE / name)
                for name in ("plain-packet.json", "plain-config.json", "pyright.json")
            },
            "reference_files": read(REFERENCE / "provenance.json")["files"],
            "protocol_files": read(PROTOCOL / "provenance.json")["files"],
            "fixture_files": read(FROZEN / "provenance.json")["files"],
        },
    )


def prepare(arm):
    registration = read(BASE / "registration.json")
    verify_hashes(TEMPLATE, registration["template_files"])
    verify_hashes(FROZEN, registration["fixture_files"])
    verify_hashes(REFERENCE, registration["reference_files"])
    verify_hashes(PROTOCOL, registration["protocol_files"])
    root = BASE / arm
    shutil.copytree(FROZEN, root)
    shutil.copyfile(
        KIT
        / "benchmarks/fixtures/tool-awaitable-extra/test_generator_coroutine_portable_v3.py",
        root / GENERATOR,
    )
    shutil.copytree(REFERENCE, root / "reference")
    shutil.copyfile(
        PROTOCOL / "awaitable_protocol.txt", root / "reference/awaitable_protocol.txt"
    )
    packet = copy.deepcopy(read(TEMPLATE / "plain-packet.json"))
    task_id = BASE.name + "-" + arm
    packet.update(
        task_id=task_id, feature_id=task_id, run_id=task_id + "-a1", packet_revision=7
    )
    packet["focused_tests"].append(TEST)
    packet["scope"]["read"].append(TEST)
    packet["scope"]["readonly"].append(TEST)
    packet["focused_tests"].append(GENERATOR)
    packet["scope"]["read"].append(GENERATOR)
    packet["scope"]["readonly"].append(GENERATOR)
    packet["scope"]["read"].append("reference/awaitable_protocol.txt")
    packet["scope"]["readonly"].append("reference/awaitable_protocol.txt")
    packet["implementation_guidance"] = [
        "Consider reading reference/awaitable_protocol.txt before choosing a returned-value classification. It contains actual dependency acceptance/rejection branches, including legal generator coroutines and explicit protocol opt-out. Reconcile both branches with the protected tests rather than inventing extra conversion/consumption. This is readonly navigation and advisory evidence, not a required edit sequence or code shape.",
        "Primary-provided actual readonly dependency source evidence, not target implementation, expected patch or mandatory code shape. Scope path reference/awaitable_protocol.txt, sha256="
        + digest(root / "reference/awaitable_protocol.txt")
        + ":\n"
        + "\n".join(
            f"{number}: {line}"
            for number, line in enumerate(
                (root / "reference/awaitable_protocol.txt")
                .read_text(encoding="utf-8")
                .splitlines(),
                1,
            )
        ),
    ]
    for behavior in packet["required_behavior"]:
        if behavior["id"] == "resolved-output":
            behavior["text"] += (
                " A legal generator-based coroutine returned by a synchronous factory is also an awaitable even though it has no __await__ attribute; complete it once on the caller loop and return its final value."
            )
            behavior["text"] += (
                " A valid plain JSON-compatible mapping may explicitly disable participation in the await protocol (__await__ = None); it must be returned unchanged, not awaited or turned into an execution failure merely because that attribute exists."
            )
    packet["acceptance_scenarios"].append(
        {
            "id": "plain-result-protocol-opt-out",
            "text": "A synchronous handler returns a JSON-compatible mapping with an explicitly disabled await protocol. This is a plain successful result, not an awaitable.",
            "observables": {
                "handler_calls": 1,
                "output_identity": "same mapping object",
                "result_status": "succeeded",
                "spurious_execution_error": False,
            },
        }
    )
    packet["acceptance_scenarios"].append(
        {
            "id": "one-registered-deadline",
            "text": "The synchronous factory and its returned completion use the existing single execution deadline; no separate timeout registration is introduced.",
            "observables": {
                "execution_timeout_registrations": "one, observed through public asyncio.Timeout on current CPython 3.12"
            },
        }
    )
    if (
        packet["review_feedback"]
        or digest(root / TARGET) != registration["fixture_files"][TARGET]
    ):
        raise ValueError(
            "fresh original source and no inherited repair recipe required"
        )
    load_worker(SNAPSHOT).validate_packet(packet)
    config = copy.deepcopy(read(TEMPLATE / "plain-config.json"))
    config["reviewer_dependency_evidence"] = [
        {
            "contract_id": "caller-context",
            "path": "reference/asyncio_threads.py",
            "anchors": ["copy_context", "ctx.run"],
        },
        {
            "contract_id": "resolved-output",
            "path": "reference/awaitable_protocol.txt",
            "anchors": [
                "def isawaitable",
                "_check_methods(C,",
                "B.__dict__[method] is None",
            ],
        },
    ]
    config["reviewer_contract_test_reads"] = [
        {
            "contract_id": "resolved-output",
            "path": "tests/unit/test_async_preservation.py",
        },
        {
            "contract_id": "resolved-output",
            "path": "tests/unit/test_async_generality.py",
        },
    ]
    config["python"] = str(PYTHON)
    config["reviewer_require_approved_execution"] = True
    config["reviewer_provided_read_evidence"] = [
        {"path": TARGET, "start_line": 1, "end_line": 160},
        {
            "path": "tests/unit/test_async_preservation.py",
            "start_line": 1,
            "end_line": 40,
        },
        {
            "path": "tests/unit/test_async_generality.py",
            "start_line": 1,
            "end_line": 61,
        },
        {"path": "reference/awaitable_protocol.txt", "start_line": 1, "end_line": 36},
        {"path": "reference/asyncio_threads.py", "start_line": 1, "end_line": 25},
    ]
    for profile in config["validation_profiles"].values():
        profile["python"] = str(PYTHON)
        profile["pytest_argv"] = [
            "--basetemp=" + str(root / ".agent/worker-temp-a1")
            if item.startswith("--basetemp=")
            else item
            for item in profile["pytest_argv"]
        ]
    for check in config["validation_profiles"]["project-strict"]["commands"][:2]:
        check["argv"].append(TEST)
        check["argv"].append(GENERATOR)
    write(root / ".agent/packet.json", packet)
    write(root / ".agent/config.json", config)
    write(root / ".agent/pyright.json", read(TEMPLATE / "pyright.json"))
    protected = {
        GENERATOR: digest(root / GENERATOR),
        **registration["fixture_files"],
        **{
            "reference/" + key: value
            for key, value in registration["reference_files"].items()
        },
        "reference/awaitable_protocol.txt": registration["protocol_files"][
            "awaitable_protocol.txt"
        ],
    }
    write(
        root / ".agent/inputs.json",
        {
            "files": {
                name: digest(root / name)
                for name in (
                    ".agent/packet.json",
                    ".agent/config.json",
                    ".agent/pyright.json",
                )
            },
            "protected": protected,
        },
    )
    preflight = []
    for check in config["validation_profiles"]["project-strict"]["commands"]:
        result = command(
            root,
            [str(PYTHON) if value == "{python}" else value for value in check["argv"]],
            timeout=180,
        )
        preflight.append({"id": check["id"], **result})
    write(root / ".agent/preflight-static-1.json", preflight)
    if any(item["exit"] for item in preflight):
        raise ValueError(
            "target-directory fixture static preflight failed; no model may start"
        )


def run(arm):
    root = BASE / arm
    registration = read(BASE / "registration.json")
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    verify_hashes(KIT / "benchmarks", registration["files"])
    inputs = read(root / ".agent/inputs.json")
    verify_hashes(root, {**inputs["files"], **inputs["protected"]})
    coder = command(
        root,
        [
            str(PYTHON),
            "-B",
            str(KIT / "benchmarks/coder_native_repair_history_adapter.py"),
            "--snapshot",
            str(SNAPSHOT),
            "--packet",
            str(root / ".agent/packet.json"),
            "--config",
            str(root / ".agent/config.json"),
            "--report",
            str(root / ".agent/coder.json"),
        ],
        timeout=1500,
    )
    write(root / ".agent/coder-invocation.json", coder)
    report = read(root / ".agent/coder.json")
    verify_hashes(
        root, {name: sha for name, sha in inputs["protected"].items() if name != TARGET}
    )
    reviewer = None
    if coder["exit"] == 0 and report["status"] == "ready_for_review":
        spec = importlib.util.spec_from_file_location(
            "deadline_fresh_unit", SNAPSHOT / ".local-agents/local-unit.py"
        )
        unit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(unit)
        identity = unit.verify_handoff(root, report)
        write(
            root / ".agent/review-request.json",
            {
                "schema_version": 1,
                **identity,
                "review_id": identity["run_id"] + "-review",
            },
        )
        adapter = "reviewer_retained_evidence_v7_adapter.py"
        reviewer = command(
            root,
            [
                str(PYTHON),
                "-B",
                str(KIT / "benchmarks" / adapter),
                "--snapshot",
                str(SNAPSHOT),
                "--request",
                str(root / ".agent/review-request.json"),
                "--config",
                str(root / ".agent/config.json"),
                "--report",
                str(root / ".agent/reviewer.json"),
            ],
            timeout=900,
        )
        write(root / ".agent/reviewer-invocation.json", reviewer)
    verify_hashes(
        root, {name: sha for name, sha in inputs["protected"].items() if name != TARGET}
    )
    facts = {
        "arm": arm,
        "coder_status": report["status"],
        "coder_seconds": coder["seconds"],
        "reviewer_decision": read(root / ".agent/reviewer.json")["decision"]
        if reviewer
        else None,
        "reviewer_seconds": reviewer["seconds"] if reviewer else None,
        "primary_acceptance": False,
        "explorer_invoked": False,
        "coordinator_invoked": False,
    }
    write(BASE / (arm + ".json"), facts)
    print(facts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("register", "prepare", "run"))
    parser.add_argument("--arm", choices=ARMS, default=ARMS[0])
    args = parser.parse_args()
    if args.action == "register":
        register()
    else:
        {"prepare": prepare, "run": run}[args.action](args.arm)
