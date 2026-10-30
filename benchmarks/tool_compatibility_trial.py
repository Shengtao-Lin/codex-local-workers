"""Protected compatibility coverage; focused repair is not fresh success credit."""

import argparse
import contextlib
import io
import shutil

import tool_awaitable_trial as trial
from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read
from layer_isolation import command, verify_hashes

BASE = WORK / "tool-compatibility-3"
FROZEN = KIT / "benchmarks/fixtures/tool-awaitable-v8"
SNAPSHOT = WORK / "tool-native-runtime-6"
EXTRA = "tests/unit/test_async_preservation.py"
ARMS = ("recovered-1", "recovered-2", "fresh-1", "fresh-2")


def freeze():
    previous = trial.FROZEN
    provenance = read(previous / "provenance.json")
    verify_hashes(previous, provenance["files"])
    shutil.copytree(previous, FROZEN)
    shutil.copyfile(
        KIT / "benchmarks/fixtures/tool-awaitable-extra/test_async_preservation.py",
        FROZEN / EXTRA,
    )
    provenance["files"][EXTRA] = digest(FROZEN / EXTRA)
    provenance["previous_fixture"] = str(previous)
    provenance["coverage"] = (
        "Existing direct async final-value compatibility; prior 12 tests unchanged"
    )
    # Only the new fixture's copied provenance is replaced, never prior history.
    (FROZEN / "provenance.json").unlink()
    write(FROZEN / "provenance.json", provenance)
    checks = [
        command(
            FROZEN,
            [
                str(trial.PYTHON),
                "-B",
                "-m",
                "ruff",
                "format",
                "--check",
                trial.TARGET,
                trial.EXTRA,
                EXTRA,
            ],
        ),
        command(
            FROZEN,
            [
                str(trial.PYTHON),
                "-B",
                "-m",
                "ruff",
                "check",
                trial.TARGET,
                trial.EXTRA,
                EXTRA,
            ],
        ),
    ]
    write(
        BASE / "fixture-static-preflight.json",
        {"checks": checks, "passed": all(check["exit"] == 0 for check in checks)},
    )
    if any(check["exit"] for check in checks):
        raise ValueError(
            "fixture's own project static preflight failed; no model invocation permitted"
        )
    write(
        BASE / "registration.json",
        {
            "arms": list(ARMS),
            "weekly_ceiling": 23,
            "repair_source": str(WORK / "tool-native-block-1/control-1"),
            "risk": "high; unchanged atomic deadline/cancellation/result contract",
            "credit": "Repair and fresh results separate; no Explorer invocation or model change",
            "new_test": EXTRA,
            "coordinator": False,
        },
    )


def prepare(arm):
    trial.BASE, trial.FROZEN, trial.SNAPSHOT, trial.ARMS = BASE, FROZEN, SNAPSHOT, ARMS
    with contextlib.redirect_stdout(io.StringIO()):
        trial.prepare(arm)
    root = BASE / arm
    packet = read(root / ".agent/packet.json")
    packet["packet_revision"] = 3
    packet["focused_tests"].append(EXTRA)
    packet["required_behavior"][0]["text"] = packet["required_behavior"][0][
        "text"
    ].replace(
        "keep ordinary sync work off the event-loop thread",
        "keep every synchronous handler invocation, including the factory itself, off the event-loop thread",
    )
    packet["acceptance_scenarios"].append(
        {
            "id": "async-compatibility",
            "text": "A direct async handler returning an already-completed Future retains that exact object as its final output, as before this extension",
            "observables": {"output_identity": "unchanged", "handler_calls": "one"},
        }
    )
    if arm in {"repair-1", "repair-2"}:
        origin = WORK / "tool-native-block-1/control-1"
        shutil.copyfile(origin / trial.TARGET, root / trial.TARGET)
        packet["review_feedback"] = [
            {
                "finding_id": "direct-async-double-await",
                "contract_id": "resolved-output",
                "text": "Primary verified original and prior accepted output preserve a completed Future returned by a direct async handler. This artifact instead returns 42, awaiting the final value twice. Repair this compatibility regression while retaining off-thread factories, the one deadline, cancellation and all other protected behavior. The new protected test reproduces the defect; prior 12 passing tests and Reviewer pass did not establish compatibility.",
                "verify_in_review": True,
                "source_anchor": "iscoroutinefunction",
            }
        ]
    packet["implementation_guidance"] = [
        "For a multi-line edit use SAFE_REPLACE with the exact current find block and hash. SAFE_REPLACE_LINE instead requires a positive integer line and a single replacement line; do not substitute block arguments for its line field. This is transport guidance, not an implementation prescription."
    ]
    if arm == "repair-2":
        packet["implementation_guidance"].append(
            "Primary diagnostic from repair-1: checking whether handler_result is a coroutine or Future did not solve the failure; both cases still awaited it. A completed Future may be either a synchronous factory's awaitable (new behavior must resolve it) or an async handler's already-final return value (existing behavior must preserve it). Compare invocation provenance, not merely the returned object's type. The protected tests require both paths; do not special-case 42, the test name or handler name."
        )
    if arm.startswith("recovered"):
        origin = WORK / "tool-native-history-1/history-2"
        shutil.copyfile(origin / trial.TARGET, root / trial.TARGET)
        packet["review_feedback"] = [
            {
                "text": "Prior Coder correctly requested contract revision because Primary's protected test had project-specific Ruff defects. Only the new test's import grouping and provenance I/O placement were corrected in a new fixture. Production code is the prior actual model artifact, not an oracle. No production edit is requested: independently validate every current protected test and static check, and truthfully acknowledge the existing contracts.",
                "verify_in_review": False,
            }
        ]
    config = read(root / ".agent/config.json")
    for check in config["validation_profiles"]["project-strict"]["commands"][:2]:
        check["argv"].append(EXTRA)
    write(root / ".agent/compat-packet.json", packet)
    write(root / ".agent/compat-config.json", config)
    write(
        root / ".agent/compat-freeze.json",
        {
            "packet": digest(root / ".agent/compat-packet.json"),
            "config": digest(root / ".agent/compat-config.json"),
            "source": digest(root / trial.TARGET),
            "credit": "actual artifact recovery, not fresh success"
            if arm.startswith("recovered")
            else "fresh implementation",
        },
    )
    baseline = command(
        root,
        [
            str(trial.PYTHON),
            "-B",
            "-m",
            "pytest",
            "-o",
            "pythonpath=src",
            "tests",
            "-q",
            "-p",
            "no:cacheprovider",
            "--basetemp=.agent/compat-baseline-temp",
            "--junitxml=.agent/compat-baseline.xml",
        ],
    )
    write(root / ".agent/compat-baseline.json", baseline)


def run(arm):
    root = BASE / arm
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    result = command(
        root,
        [
            str(trial.PYTHON),
            "-B",
            str(SNAPSHOT / ".local-agents/local-unit.py"),
            "--packet",
            str(root / ".agent/compat-packet.json"),
            "--config",
            str(root / ".agent/compat-config.json"),
            "--coder-report",
            str(root / ".agent/compat-coder.json"),
            "--review-report",
            str(root / ".agent/compat-reviewer.json"),
        ],
        timeout=1500,
    )
    write(root / ".agent/compat-invocation.json", result)
    print(result)


def positive_control():
    root = BASE / "accepted-control"
    provenance = read(FROZEN / "provenance.json")
    verify_hashes(FROZEN, provenance["files"])
    root.mkdir(parents=True, exist_ok=False)
    for path in provenance["files"]:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FROZEN / path, target)
    origin = WORK / "tool-awaitable-3/fresh-2"
    shutil.copyfile(origin / trial.TARGET, root / trial.TARGET)
    result = command(
        root,
        [
            str(trial.PYTHON),
            "-B",
            "-m",
            "pytest",
            "-o",
            "pythonpath=src",
            "tests",
            "-q",
            "-p",
            "no:cacheprovider",
            "--basetemp=.agent/positive-temp",
            "--junitxml=.agent/positive.xml",
        ],
    )
    write(
        root / ".agent/positive.json",
        {
            "result": result,
            "source_sha256": digest(root / trial.TARGET),
            "credit": "Previously accepted artifact, not new implementation",
            "passed": result["exit"] == 0,
        },
    )
    print({"positive_exit": result["exit"]})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("freeze", "prepare", "run", "positive"))
    parser.add_argument("--arm", choices=ARMS)
    args = parser.parse_args()
    if args.action == "freeze":
        freeze()
    elif args.action == "positive":
        positive_control()
    else:
        {"prepare": prepare, "run": run}[args.action](args.arm)
