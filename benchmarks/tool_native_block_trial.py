"""Matched actual Coder/Reviewer chains, no synthetic Coder or Explorer credit."""

import argparse
import contextlib
import importlib.util
import io
import json

import tool_awaitable_trial as trial
from capability_fit import KIT, WORK, freeze, write
from inherited_context_recovery import digest, read
from layer_isolation import command, verify_hashes

BASE = WORK / "tool-native-block-1"
SNAPSHOT = WORK / "tool-native-runtime-6"
ARMS = ("control-1", "native-1", "native-2", "control-2")


def configure():
    trial.BASE, trial.SNAPSHOT, trial.ARMS = BASE, SNAPSHOT, ARMS


def register():
    if read(WORK / "coder-block-preflight-2/facts.json")["passed"] is not True:
        raise ValueError("real positive/negative native preflight required")
    if not SNAPSHOT.exists():
        freeze(SNAPSHOT.name)
    write(
        BASE / "registration.json",
        {
            "arms_in_order": list(ARMS),
            "weekly_ceiling": 23,
            "axis": "Current JSON envelope vs explicit native BLOCK-only tool bundle; not attribution to LINE removal alone",
            "common": "Same real frozen source, 12 protected tests, full risk/contract, model, sampling, contexts and budgets",
            "packet_clarification": "Every synchronous invocation including factory is off-thread; no exact patch or oracle supplied. Common to both arms, historical results not regraded.",
            "runtime": str(SNAPSHOT),
            "explorer_invoked": False,
            "handoff": "Actual canonical Coder archive verified before automatic independent Reviewer; never automatic acceptance",
            "promotion": "None from compatibility alone; independent Primary source/diff and validation required",
        },
    )


def prepare(arm):
    with contextlib.redirect_stdout(io.StringIO()):
        trial.prepare(arm)
    root = BASE / arm
    packet = read(root / ".agent/packet.json")
    packet["packet_revision"] = 2
    packet["required_behavior"][0]["text"] = packet["required_behavior"][0][
        "text"
    ].replace(
        "keep ordinary sync work off the event-loop thread",
        "keep every synchronous handler invocation, including the factory itself, off the event-loop thread",
    )
    packet["implementation_guidance"] = read(
        WORK / "tool-awaitable-5/fresh-1/.agent/packet-v2.json"
    )["implementation_guidance"]
    write(root / ".agent/packet-v2.json", packet)
    write(
        root / ".agent/input-freeze-v2.json",
        {
            "packet_sha256": digest(root / ".agent/packet-v2.json"),
            "config_sha256": digest(root / ".agent/config.json"),
        },
    )
    print(json.dumps({"prepared": arm, "explorer_invoked": False}))


def run(arm):
    if arm not in ARMS:
        raise ValueError("registered arm required")
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    root = BASE / arm
    evidence = read(root / ".agent/input-freeze-v2.json")
    verify_hashes(
        root,
        {
            ".agent/packet-v2.json": evidence["packet_sha256"],
            ".agent/config.json": evidence["config_sha256"],
        },
    )
    argv = [str(trial.PYTHON), "-B"]
    if arm.startswith("native"):
        argv += [
            str(KIT / "benchmarks/coder_native_block_adapter.py"),
            "--snapshot",
            str(SNAPSHOT),
        ]
    else:
        argv += [str(SNAPSHOT / ".local-agents/local-code.py")]
    argv += [
        "--packet",
        str(root / ".agent/packet-v2.json"),
        "--config",
        str(root / ".agent/config.json"),
        "--report",
        str(root / ".agent/coder.json"),
    ]
    invoked = command(root, argv, timeout=1500)
    write(root / ".agent/coder-invocation.json", invoked)
    report = read(root / ".agent/coder.json")
    reviewer = None
    if report["status"] == "ready_for_review" and invoked["exit"] == 0:
        spec = importlib.util.spec_from_file_location(
            "tool_native_unit_handoff", SNAPSHOT / ".local-agents/local-unit.py"
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
        reviewer = command(
            root,
            [
                str(trial.PYTHON),
                "-B",
                str(SNAPSHOT / ".local-agents/local-review.py"),
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
    facts = {
        "arm": arm,
        "coder_status": report["status"],
        "coder_seconds": invoked["seconds"],
        "reviewer_decision": read(root / ".agent/reviewer.json")["decision"]
        if reviewer
        else None,
        "reviewer_seconds": reviewer["seconds"] if reviewer else None,
        "primary_acceptance": False,
        "explorer_invoked": False,
    }
    write(BASE / (arm + ".json"), facts)
    print(json.dumps(facts))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("register", "prepare", "run", "verify"))
    parser.add_argument("--arm", choices=ARMS)
    args = parser.parse_args()
    configure()
    if args.action == "register":
        register()
    else:
        {"prepare": prepare, "run": run, "verify": trial.verify}[args.action](args.arm)
