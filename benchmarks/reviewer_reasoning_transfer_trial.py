"""Independent cancellation/rollback family; explicitly synthetic Reviewer archives."""

import argparse

from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read
from layer_isolation import command, verify_hashes
from tool_awaitable_trial import PYTHON
from tool_primary_verification import junit_counts

BASE = WORK / "reviewer-reasoning-transfer-1"
SNAPSHOT = WORK / "reviewer-read-version-runtime-14"
ROOTS = {
    "hidden": KIT
    / "benchmarks/work/mixed-v1/reviewer-controls/review-save-cancel-hidden-4c7e1416e6c4",
    "clean": KIT
    / "benchmarks/work/mixed-v1/reviewer-controls/review-save-cancel-clean-3aea7fe85653",
}
ARMS = tuple(
    f"{kind}-{mode}-{r}"
    for r in (1, 2)
    for kind in ("clean", "hidden")
    for mode in ("control", "candidate")
)
ADAPTERS = (
    "reviewer_required_tool_adapter.py",
    "reviewer_reasoning_examples_adapter.py",
    "reviewer_sampling_probe_adapter.py",
    "reviewer_reasoning_transfer_trial.py",
)


def input_paths(root):
    request = read(root / ".agent/request.json")
    archive = f".agent/tasks/{request['task_id']}/runs/{request['run_id']}"
    return [
        "src/product/target.py",
        "src/product/__init__.py",
        "tests/test_target.py",
        "pyproject.toml",
        "primary-oracle.py",
        ".agent/request.json",
        ".agent/config.json",
        *[
            archive + "/" + name
            for name in (
                "packet.json",
                "post-state.json",
                "validation.json",
                "handoff.json",
                "completed.json",
                "cumulative.diff",
            )
        ],
    ]


def register():
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    write(
        BASE / "registration.json",
        {
            "arms": ARMS,
            "weekly_ceiling": 30,
            "axis": "Only two unchanged reasoning examples; common required-native transport, fixed current sampling/model/context/budgets and original review gates",
            "family": "Independent awaited cancellation/rollback/original exception identity; examples concern attribute protocols and timer registrations, not this implementation",
            "credit": "Historical synthetic diagnostic archives, not actual Coder success, fresh feature acceptance, Explorer/Coordinator or savings. New contexts and immutable review IDs. No keyword grading.",
            "expected": "Clean source must pass. Hidden except Exception skips cleanup on CancelledError, and suppress(Exception) cannot preserve an original failure when cleanup itself raises CancelledError. Findings must explain the real branch and bounded repair, not falsely claim Exception catches cancellation.",
            "snapshot": str(SNAPSHOT),
            "files": {name: digest(KIT / "benchmarks" / name) for name in ADAPTERS},
            "roots": {
                kind: {path: digest(root / path) for path in input_paths(root)}
                for kind, root in ROOTS.items()
            },
        },
    )


def prepare(arm):
    kind = arm.split("-")[0]
    root = ROOTS[kind]
    registration = read(BASE / "registration.json")
    verify_hashes(root, registration["roots"][kind])
    executions = []
    for label, test in (
        ("normal", "tests/test_target.py"),
        ("oracle", "primary-oracle.py"),
    ):
        junit = root / ".agent" / ("heldout-" + arm + "-" + label + ".xml")
        executions.append(
            command(
                root,
                [
                    str(PYTHON),
                    "-B",
                    "-m",
                    "pytest",
                    test,
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    "--basetemp=.agent/heldout-" + arm + "-" + label + "-temp",
                    "--junitxml=" + str(junit),
                ],
            )
        )
        counts = junit_counts(junit)
        if not counts["tests"] or counts["skipped"] or counts["error"]:
            raise ValueError("preflight requires real executed JUnit cases")
        if label == "normal" or kind == "clean":
            if executions[-1]["exit"] or counts["failure"]:
                raise ValueError("positive preflight failed")
        elif executions[-1]["exit"] == 0 or not counts["failure"]:
            raise ValueError("hidden oracle must independently fail")
    write(
        BASE / (arm + ".preflight.json"),
        {"executions": executions, "model_credit": False},
    )
    config = read(root / ".agent/config.json")
    current = read(KIT / ".local-agents/config.json")
    config.update(
        {
            key: value
            for key, value in current.items()
            if key.startswith("reviewer_")
            or key
            in (
                "max_reviewer_turns",
                "max_reviewer_protocol_errors",
                "model_context_safety_margin",
                "single_model_residency",
                "model_switch_timeout_seconds",
            )
        }
    )
    config["python"] = str(PYTHON)
    config["reviewer_prepass_challenge"] = False
    config["reviewer_finding_challenge"] = False
    for profile in config["validation_profiles"].values():
        profile["python"] = str(PYTHON)
        for check in profile.get("commands", []):
            argv = check["argv"]
            if "-B" not in argv:
                argv.insert(1, "-B")
    request = read(root / ".agent/request.json")
    request["review_id"] = "reasoning-transfer-" + arm
    write(BASE / (arm + ".request.json"), request)
    write(BASE / (arm + ".config.json"), config)
    verify_hashes(root, registration["roots"][kind])
    write(
        BASE / (arm + ".inputs.json"),
        {
            "files": {
                arm + suffix: digest(BASE / (arm + suffix))
                for suffix in (".request.json", ".config.json")
            }
        },
    )


def run(arm):
    kind = arm.split("-")[0]
    root = ROOTS[kind]
    registration = read(BASE / "registration.json")
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    verify_hashes(KIT / "benchmarks", registration["files"])
    verify_hashes(root, registration["roots"][kind])
    verify_hashes(BASE, read(BASE / (arm + ".inputs.json"))["files"])
    adapter = (
        "reviewer_reasoning_examples_adapter.py"
        if "candidate" in arm
        else "reviewer_required_tool_adapter.py"
    )
    invoked = command(
        root,
        [
            str(PYTHON),
            "-B",
            str(KIT / "benchmarks" / adapter),
            "--snapshot",
            str(SNAPSHOT),
            "--request",
            str(BASE / (arm + ".request.json")),
            "--config",
            str(BASE / (arm + ".config.json")),
            "--report",
            str(BASE / (arm + ".report.json")),
        ],
        timeout=900,
    )
    write(BASE / (arm + ".invocation.json"), invoked)
    verify_hashes(root, registration["roots"][kind])
    print(
        {
            "arm": arm,
            "decision": read(BASE / (arm + ".report.json"))["decision"],
            "seconds": invoked["seconds"],
            "primary_acceptance": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("register", "prepare", "run"))
    parser.add_argument("--arm", choices=ARMS, default=ARMS[0])
    args = parser.parse_args()
    register() if args.action == "register" else {"prepare": prepare, "run": run}[
        args.action
    ](args.arm)
