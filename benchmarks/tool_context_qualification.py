"""New frozen fresh qualification: loop ownership and original caller context."""

import argparse
import shutil

import tool_contract_scope_trial as scope
from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read
from layer_isolation import command, verify_hashes
from tool_awaitable_trial import PYTHON, TARGET
from tool_primary_verification import junit_counts

BASE = WORK / "tool-context-scope-1"
FROZEN = KIT / "benchmarks/fixtures/tool-awaitable-v10"
CONTEXT = "tests/unit/test_caller_context.py"


def configure():
    scope.BASE, scope.FROZEN, scope.SNAPSHOT = (
        BASE,
        FROZEN,
        WORK / "tool-evidence-runtime-8",
    )
    scope.configure()


def freeze():
    previous = KIT / "benchmarks/fixtures/tool-awaitable-v9"
    provenance = read(previous / "provenance.json")
    verify_hashes(previous, provenance["files"])
    shutil.copytree(previous, FROZEN)
    shutil.copyfile(
        KIT / "benchmarks/fixtures/tool-awaitable-extra/test_caller_context.py",
        FROZEN / CONTEXT,
    )
    provenance["files"][CONTEXT] = digest(FROZEN / CONTEXT)
    provenance["previous_fixture"] = str(previous)
    (FROZEN / "provenance.json").unlink()
    write(FROZEN / "provenance.json", provenance)
    test_paths = [
        "tests/unit/test_awaitable.py",
        "tests/unit/test_async_preservation.py",
        "tests/unit/test_async_generality.py",
        CONTEXT,
    ]
    checks = [
        command(FROZEN, [str(PYTHON), "-B", "-m", "ruff", *args, TARGET, *test_paths])
        for args in (["format", "--check"], ["check"])
    ]
    positive = BASE / "positive"
    shutil.copytree(FROZEN, positive)
    actual = WORK / "tool-native-history-3/candidate-1" / TARGET
    if (
        digest(actual)
        != "161a615035080b9cbbceb881a0a417735e1e778a8fd1966b461fda96bffcf14a"
    ):
        raise ValueError("positive actual artifact drift")
    shutil.copyfile(actual, positive / TARGET)
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
            "--basetemp=.agent/positive-temp",
            "--junitxml=.agent/positive.xml",
        ],
    )
    counts = junit_counts(positive / ".agent/positive.xml")
    passed = all(c["exit"] == 0 for c in [*checks, tests]) and counts == {
        "tests": 18,
        "failure": 0,
        "error": 0,
        "skipped": 0,
    }
    write(
        BASE / "preflight.json",
        {
            "checks": checks,
            "positive": tests,
            "junit": counts,
            "passed": passed,
            "model_credit": False,
        },
    )
    if not passed:
        raise ValueError("own-project fixture preflight failed")
    write(
        BASE / "registration.json",
        {
            "arms": list(scope.ARMS),
            "weekly_ceiling": 23,
            "risk": "High, same atomic invocation/deadline/cancellation/public result unit",
            "coverage": "Prior sixteen tests unchanged; two caller ContextVar values and no mutation leak",
            "contracts": "Existing async final identity; sync invocation off-thread with caller context; returned-awaitable completion on caller loop under the original single deadline",
            "guidance": "Externally observable per-path scenario matrix, no code patch or API implementation prescription",
            "adapter_sha256": {
                p: digest(KIT / "benchmarks" / p) for p in scope.ADAPTERS
            },
            "credit": "Fresh qualification, not comparison with differently specified historical cohorts; no Explorer or Coordinator credit",
        },
    )


def prepare(arm):
    configure()
    scope.prepare(arm)
    root = BASE / arm
    packet = read(root / ".agent/compat-packet.json")
    packet["packet_revision"] = 5
    packet["focused_tests"].append(CONTEXT)
    packet["owned_contract_ids"].append("caller-context")
    packet["required_behavior"].append(
        {
            "id": "caller-context",
            "risk_floor": "high",
            "text": "Preserve original caller ContextVar values inside each off-thread synchronous handler. The handler's local ContextVar mutation must not leak back to its caller; different caller requests retain their own values. Preserve this existing plain-sync behavior when adding factory support.",
        }
    )
    for item in packet["required_behavior"]:
        if item["id"] == "resolved-output":
            item["text"] += (
                " Returned-awaitable completion belongs to the existing caller event loop, including caller-loop-owned Futures; do not transfer completion to a new unrelated event loop."
            )
    packet["acceptance_scenarios"].extend(
        [
            {
                "id": "sync-path-ownership",
                "text": "Synchronous invocation and returned-awaitable completion are different operations.",
                "observables": {
                    "handler_invocation": "worker thread, once, caller context visible",
                    "returned_awaitable_completion": "caller event loop, once",
                    "final_result": "resolved value",
                },
            },
            {
                "id": "async-path-ownership",
                "text": "A direct async handler has one invocation await, not recursive consumption of its final value.",
                "observables": {
                    "handler_invocation": "caller loop, once",
                    "invocation_completion": "await once",
                    "final_result": "exact returned object, no second consumption",
                },
            },
            {
                "id": "context-roundtrip",
                "text": "Two caller context values pass through normal sync handlers while handler-local mutation is isolated.",
                "observables": {
                    "handler_observed": "corresponding caller value",
                    "caller_after": "unchanged",
                },
            },
        ]
    )
    config = read(root / ".agent/compat-config.json")
    for check in config["validation_profiles"]["project-strict"]["commands"][:2]:
        check["argv"].append(CONTEXT)
    write(root / ".agent/context-packet.json", packet)
    write(root / ".agent/context-config.json", config)
    shutil.copyfile(
        root / ".agent/context-packet.json", root / ".agent/compat-packet.json"
    )
    shutil.copyfile(
        root / ".agent/context-config.json", root / ".agent/compat-config.json"
    )
    write(
        root / ".agent/context-freeze.json",
        {
            "packet": digest(root / ".agent/compat-packet.json"),
            "config": digest(root / ".agent/compat-config.json"),
            "source": digest(root / TARGET),
        },
    )


def run(arm):
    configure()
    root = BASE / arm
    frozen = read(root / ".agent/context-freeze.json")
    verify_hashes(
        root,
        {
            ".agent/compat-packet.json": frozen["packet"],
            ".agent/compat-config.json": frozen["config"],
            TARGET: frozen["source"],
        },
    )
    verify_hashes(
        KIT / "benchmarks", read(BASE / "registration.json")["adapter_sha256"]
    )
    scope.native.run(arm)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("freeze", "prepare", "run"))
    parser.add_argument("--arm", choices=scope.ARMS, default=scope.ARMS[0])
    args = parser.parse_args()
    if args.action == "freeze":
        freeze()
    else:
        {"prepare": prepare, "run": run}[args.action](args.arm)
