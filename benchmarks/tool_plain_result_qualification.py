"""Freeze an observed plain-result regression into prospective qualification."""

import argparse
import shutil

import tool_context_reference_trial as reference
from capability_fit import KIT, WORK, freeze, load_worker, write
from inherited_context_recovery import digest, read
from layer_isolation import command, verify_hashes
from tool_awaitable_trial import PYTHON, TARGET
from tool_primary_verification import junit_counts

BASE = WORK / "tool-plain-result-2"
FROZEN = KIT / "benchmarks/fixtures/tool-awaitable-v12"
SNAPSHOT = WORK / "tool-plain-result-runtime-13"
TEST = "tests/unit/test_plain_result.py"


def configure():
    reference.BASE, reference.SNAPSHOT = BASE, SNAPSHOT
    reference.qualification.FROZEN = FROZEN
    reference.configure()


def register():
    previous = KIT / "benchmarks/fixtures/tool-awaitable-v10"
    provenance = read(previous / "provenance.json")
    verify_hashes(previous, provenance["files"])
    if FROZEN.exists():
        raise ValueError("do not overwrite frozen fixture")
    shutil.copytree(previous, FROZEN)
    shutil.copyfile(
        KIT / "benchmarks/fixtures/tool-awaitable-extra/test_plain_result.py",
        FROZEN / TEST,
    )
    for args in (["check", "--fix"], ["format"]):
        normalized = command(FROZEN, [str(PYTHON), "-B", "-m", "ruff", *args, TEST])
        if normalized["exit"] != 0:
            raise ValueError("new acceptance test target-project normalization failed")
    provenance["files"][TEST] = digest(FROZEN / TEST)
    provenance["previous_fixture"] = str(previous)
    # Only the newly copied provenance pointer is replaced, never prior history.
    (FROZEN / "provenance.json").unlink()
    write(FROZEN / "provenance.json", provenance)
    positive = BASE / "positive"
    shutil.copytree(FROZEN, positive)
    actual = WORK / "tool-context-reference-1/fresh-2" / TARGET
    source_facts = read(
        WORK / "tool-context-reference-1/fresh-2/.agent/primary-reference-a1-1.json"
    )
    if (
        digest(actual) != source_facts["source_sha256"]
        or source_facts["passed"] is not True
    ):
        raise ValueError("actual accepted control drift")
    shutil.copyfile(actual, positive / TARGET)
    invocations = [
        command(positive, [str(PYTHON), "-B", "-m", "ruff", *args, TARGET, TEST])
        for args in (["format", "--check"], ["check"])
    ]
    tests = command(
        positive,
        [
            str(PYTHON),
            "-B",
            "-m",
            "pytest",
            "-o",
            "pythonpath=src",
            "tests",
            "-q",
            "-p",
            "no:cacheprovider",
            "--basetemp=.agent/preflight-temp",
            "--junitxml=.agent/preflight.xml",
        ],
    )
    counts = junit_counts(positive / ".agent/preflight.xml")
    passed = all(item["exit"] == 0 for item in [*invocations, tests]) and counts == {
        "tests": 19,
        "failure": 0,
        "error": 0,
        "skipped": 0,
    }
    write(
        BASE / "fixture-preflight.json",
        {
            "passed": passed,
            "invocations": invocations,
            "tests": tests,
            "junit": counts,
            "model_credit": False,
        },
    )
    if not passed:
        raise ValueError("own-project fixture preflight failed")
    freeze(SNAPSHOT.name)
    reference.register()
    write(
        BASE / "plain-registration.json",
        {
            "driver_sha256": digest(
                KIT / "benchmarks/tool_plain_result_qualification.py"
            ),
            "fixture_version": 12,
            "tests": 19,
            "risk": "same high atomic unit",
            "change": "one observed plain sync compatibility edge case; no oracle in fresh roots",
            "credit": "Prospective regression coverage, not historical causal comparison or cloud efficiency proof",
            "weekly_ceiling": 23,
            "operator_preflight": "Earlier v11/plain-result-1 retained: 19 tests passed but target project Ruff style differed from kit formatting. No model invoked; normalize only the new test under the real target config before freezing this new fixture.",
        },
    )


def prepare(arm):
    reference.prepare(arm)
    root = BASE / arm
    packet = read(root / ".agent/reference-packet.json")
    packet["packet_revision"] = 6
    packet["focused_tests"].append(TEST)
    packet["scope"]["readonly"].append(TEST)
    packet["acceptance_scenarios"].append(
        {
            "id": "plain-sync-json-result",
            "text": "A synchronous handler's ordinary JSON mapping result is preserved even if its type explicitly disables await; attribute presence alone is not awaitability.",
        }
    )
    load_worker(SNAPSHOT).validate_packet(packet)
    config = read(root / ".agent/reference-config.json")
    for check in config["validation_profiles"]["project-strict"]["commands"][:2]:
        check["argv"].append(TEST)
    write(root / ".agent/plain-packet.json", packet)
    write(root / ".agent/plain-config.json", config)
    write(
        root / ".agent/plain-inputs.json",
        {
            "files": {
                p: digest(root / p)
                for p in (
                    ".agent/plain-packet.json",
                    ".agent/plain-config.json",
                    TARGET,
                )
            }
        },
    )


def run(arm):
    configure()
    root = BASE / arm
    registration = read(BASE / "registration.json")
    verify_hashes(
        KIT / "benchmarks",
        {
            "tool_plain_result_qualification.py": read(
                BASE / "plain-registration.json"
            )["driver_sha256"],
            "tool_context_reference_trial.py": registration["driver_sha256"],
            **registration["adapter_sha256"],
        },
    )
    verify_hashes(root, read(root / ".agent/plain-inputs.json")["files"])
    verify_hashes(root / "reference", registration["reference_files"])
    provenance = read(FROZEN / "provenance.json")
    verify_hashes(KIT.parent / "agent-runtime-kit", provenance["original_files"])
    verify_hashes(
        root, {p: sha for p, sha in provenance["files"].items() if p != TARGET}
    )
    shutil.copyfile(
        root / ".agent/plain-packet.json", root / ".agent/compat-packet.json"
    )
    shutil.copyfile(
        root / ".agent/plain-config.json", root / ".agent/compat-config.json"
    )
    reference.qualification.scope.native.run(arm)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("register", "prepare", "run"))
    parser.add_argument("--arm", choices=reference.ARMS, default=reference.ARMS[0])
    args = parser.parse_args()
    configure()
    if args.action == "register":
        register()
    else:
        {"prepare": prepare, "run": run}[args.action](args.arm)
