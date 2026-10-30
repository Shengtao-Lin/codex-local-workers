"""Actual clean/defective archives, identical matched reviewer inputs per arm."""

import argparse
import importlib.util

from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read
from layer_isolation import command, verify_hashes
from tool_awaitable_trial import PYTHON, TARGET

BASE = WORK / "tool-reviewer-canonical-1"
SNAPSHOT = WORK / "tool-reviewer-runtime-7"
PREFIX = "canonical"
ADAPTER = "reviewer_canonical_adapter.py"
ARTIFACTS = {
    "clean": WORK / "tool-native-history-3/candidate-1",
    "hidden": WORK / "tool-native-block-1/control-1",
}


def prepare(kind, arm, repetition):
    root = ARTIFACTS[kind]
    report = read(root / ".agent/coder.json")
    if report["status"] != "ready_for_review":
        raise ValueError("real eligible Coder archive required")
    label = f"{PREFIX}-{kind}-{arm}-r{repetition}"
    config = read(
        root
        / (".agent/compat-config.json" if kind == "clean" else ".agent/config.json")
    )
    if config.get("reviewer_native_tools") is not True:
        raise ValueError("matched native Reviewer baseline required")
    spec = importlib.util.spec_from_file_location(
        "canonical_trial_unit", SNAPSHOT / ".local-agents/local-unit.py"
    )
    unit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(unit)
    identity = unit.verify_handoff(root, report)
    if not (BASE / "registration.json").exists():
        write(
            BASE / "registration.json",
            {
                "arms_in_order": [
                    "hidden-control-r1",
                    "hidden-candidate-r1",
                    "clean-candidate-r1",
                    "clean-control-r1",
                    "clean-control-r2",
                    "clean-candidate-r2",
                    "hidden-candidate-r2",
                    "hidden-control-r2",
                ],
                "axis": "Same frozen runtime: ordinary citation alternatives vs startup canonical source_refs-only template and native schema",
                "credit": "Reviewer compatibility and semantic challenge; actual prior C archives, no new Coder/Explorer/full-chain credit",
                "expected_hidden": "Direct async final awaitable consumed twice; independent original and good-output identity probes distinguish it",
                "expected_clean": "Direct handler creates outer coroutine, awaited exactly once; sync invocation remains off-thread and under shared deadline",
                "model_budgets": "Unchanged Muse, single residency, contexts, sampling and action budgets",
                "adapter_sha256": digest(
                    KIT / "benchmarks/reviewer_canonical_adapter.py"
                ),
                "weekly_ceiling": 23,
            },
        )
    write(BASE / (label + ".config.json"), config)
    write(
        BASE / (label + ".request.json"),
        {"schema_version": 1, **identity, "review_id": label},
    )
    write(
        BASE / (label + ".inputs.json"),
        {
            "root": str(root),
            "kind": kind,
            "arm": arm,
            "source_sha256": digest(root / TARGET),
            "request_sha256": digest(BASE / (label + ".request.json")),
            "config_sha256": digest(BASE / (label + ".config.json")),
        },
    )


def run(kind, arm, repetition):
    label = f"{PREFIX}-{kind}-{arm}-r{repetition}"
    root = ARTIFACTS[kind]
    evidence = read(BASE / (label + ".inputs.json"))
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    verify_hashes(root, {TARGET: evidence["source_sha256"]})
    verify_hashes(
        BASE,
        {
            label + ".request.json": evidence["request_sha256"],
            label + ".config.json": evidence["config_sha256"],
        },
    )
    verify_hashes(
        KIT / "benchmarks",
        {ADAPTER: read(BASE / "registration.json")["adapter_sha256"]},
    )
    argv = [str(PYTHON), "-B"]
    if arm == "candidate":
        argv += [
            str(KIT / "benchmarks" / ADAPTER),
            "--snapshot",
            str(SNAPSHOT),
        ]
    else:
        argv += [str(SNAPSHOT / ".local-agents/local-review.py")]
    argv += [
        "--request",
        str(BASE / (label + ".request.json")),
        "--config",
        str(BASE / (label + ".config.json")),
        "--report",
        str(BASE / (label + ".report.json")),
    ]
    invoked = command(root, argv, timeout=900)
    write(BASE / (label + ".invocation.json"), invoked)
    print(
        {
            "arm": label,
            "decision": read(BASE / (label + ".report.json"))["decision"],
            "seconds": invoked["seconds"],
            "primary_acceptance": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--kind", choices=ARTIFACTS, required=True)
    parser.add_argument("--arm", choices=("control", "candidate"), required=True)
    parser.add_argument("--repetition", type=int, choices=(1, 2), default=1)
    args = parser.parse_args()
    {"prepare": prepare, "run": run}[args.action](args.kind, args.arm, args.repetition)
