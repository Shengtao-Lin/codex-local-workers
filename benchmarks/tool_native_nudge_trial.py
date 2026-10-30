"""Prospective fresh native-text nudge qualification; no global promotion."""

import argparse
import shutil

import tool_context_reference_trial as reference
from capability_fit import KIT, WORK, freeze, write
from inherited_context_recovery import digest, read
from layer_isolation import verify_hashes
from tool_awaitable_trial import TARGET

BASE = WORK / "tool-native-nudge-1"
SNAPSHOT = WORK / "tool-native-nudge-runtime-11"
ARMS = ("fresh-1", "fresh-2")


def configure():
    reference.BASE, reference.SNAPSHOT, reference.ARMS = BASE, SNAPSHOT, ARMS
    reference.configure()


def register():
    freeze(SNAPSHOT.name)
    reference.register()
    write(
        BASE / "nudge-registration.json",
        {
            "driver_sha256": digest(KIT / "benchmarks/tool_native_nudge_trial.py"),
            "core_regression": "current-full-native-nudge-1.xml: 876 tests and 109 subtests passed",
            "axis": "Default-off coder_native_text_truncation_nudge enabled only in these copied fixtures",
            "budget": "Same model/context/sampling/turn/error/deadline limits; at most one rejected no-tool text truncation correction",
            "credit": "Fresh qualification, not matched causal comparison. Record actual nudge activation; no benefit credit if unexercised. Historical failures retained. No Explorer or Coordinator credit.",
        },
    )


def prepare(arm):
    reference.prepare(arm)
    root = BASE / arm
    config = read(root / ".agent/reference-config.json")
    config["coder_native_text_truncation_nudge"] = True
    write(root / ".agent/nudge-config.json", config)
    write(
        root / ".agent/nudge-inputs.json",
        {
            "files": {
                path: digest(root / path)
                for path in (
                    ".agent/reference-packet.json",
                    ".agent/nudge-config.json",
                    TARGET,
                )
            }
        },
    )


def run(arm):
    configure()
    root = BASE / arm
    verify_hashes(
        KIT / "benchmarks",
        {
            "tool_native_nudge_trial.py": read(BASE / "nudge-registration.json")[
                "driver_sha256"
            ]
        },
    )
    registration = read(BASE / "registration.json")
    verify_hashes(
        KIT / "benchmarks",
        {
            "tool_context_reference_trial.py": registration["driver_sha256"],
            **registration["adapter_sha256"],
        },
    )
    verify_hashes(root / "reference", registration["reference_files"])
    provenance = read(reference.qualification.FROZEN / "provenance.json")
    verify_hashes(KIT.parent / "agent-runtime-kit", provenance["original_files"])
    verify_hashes(
        root, {path: sha for path, sha in provenance["files"].items() if path != TARGET}
    )
    verify_hashes(root, read(root / ".agent/nudge-inputs.json")["files"])
    shutil.copyfile(
        root / ".agent/reference-packet.json", root / ".agent/compat-packet.json"
    )
    shutil.copyfile(
        root / ".agent/nudge-config.json", root / ".agent/compat-config.json"
    )
    reference.qualification.scope.native.run(arm)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("register", "prepare", "run"))
    parser.add_argument("--arm", choices=ARMS, default=ARMS[0])
    args = parser.parse_args()
    configure()
    if args.action == "register":
        register()
    else:
        {"prepare": prepare, "run": run}[args.action](args.arm)
