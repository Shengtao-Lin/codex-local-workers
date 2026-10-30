"""Fresh qualification with path-specific contracts, not a retrospective rescue."""

import argparse
import shutil

import tool_compatibility_trial as compat
import tool_native_history_trial as native
from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read
from layer_isolation import command, verify_hashes
from tool_awaitable_trial import PYTHON, TARGET
from tool_primary_verification import junit_counts

BASE = WORK / "tool-contract-scope-1"
FROZEN = KIT / "benchmarks/fixtures/tool-awaitable-v9"
GENERAL = "tests/unit/test_async_generality.py"
ARMS = ("fresh-1", "fresh-2")
SNAPSHOT = WORK / "tool-reviewer-runtime-7"
ADAPTERS = (
    "native_coder_adapter.py",
    "coder_native_block_adapter.py",
    "coder_native_history_adapter.py",
    "coder_native_repair_history_adapter.py",
)


def freeze():
    previous = KIT / "benchmarks/fixtures/tool-awaitable-v8"
    provenance = read(previous / "provenance.json")
    verify_hashes(previous, provenance["files"])
    shutil.copytree(previous, FROZEN)
    shutil.copyfile(
        KIT / "benchmarks/fixtures/tool-awaitable-extra/test_async_generality.py",
        FROZEN / GENERAL,
    )
    provenance["files"][GENERAL] = digest(FROZEN / GENERAL)
    provenance["previous_fixture"] = str(previous)
    (FROZEN / "provenance.json").unlink()
    write(FROZEN / "provenance.json", provenance)
    argv = [str(PYTHON), "-B", "-m", "ruff"]
    checks = [
        command(FROZEN, argv + ["format", "--check", TARGET, GENERAL]),
        command(FROZEN, argv + ["check", TARGET, GENERAL]),
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
        "tests": 16,
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
            "positive_model_credit": False,
        },
    )
    if not passed:
        raise ValueError("fixture own-project preflight failed")
    write(
        BASE / "registration.json",
        {
            "arms": list(ARMS),
            "weekly_ceiling": 23,
            "contracts": "Resolve returned awaitables only for sync factories. Await direct async invocation once, preserve its final object without another consumption. Factory-only JSON and pending-output restrictions are scoped explicitly.",
            "risk": "unchanged high atomic deadline/cancellation/public-result boundary",
            "transport": "Native BLOCK, correlated actions and actual VALIDATE repair observations; no semantic autofill",
            "tests": "Original thirteen unchanged plus three protected async final-object cases",
            "models": "unchanged Qwen/Muse, contexts and budgets, single residency",
            "adapter_sha256": {p: digest(KIT / "benchmarks" / p) for p in ADAPTERS},
            "credit": "Two fresh calls; no causal comparison with differently specified historical contracts, no Explorer or Coordinator credit",
        },
    )


def configure():
    compat.BASE, compat.FROZEN, compat.SNAPSHOT, compat.ARMS = (
        BASE,
        FROZEN,
        SNAPSHOT,
        ARMS,
    )
    native.BASE, native.ARMS = BASE, ARMS
    native.TRANSPORTS = {arm: "coder_native_repair_history_adapter.py" for arm in ARMS}


def prepare(arm):
    if not read(BASE / "preflight.json")["passed"]:
        raise ValueError("fixture preflight required")
    configure()
    compat.prepare(arm)
    root = BASE / arm
    packet = read(root / ".agent/compat-packet.json")
    packet["packet_revision"] = 4
    packet["focused_tests"].append(GENERAL)
    text = {
        "resolved-output": "Invoke every handler exactly once. A synchronous callable (including the factory itself) runs off the event-loop thread; if its return is awaitable, resolve it exactly once, supporting coroutine, Future and custom awaitable. For a direct async handler, await its invocation exactly once and preserve the final returned value, including object identity when that value is itself awaitable; do not consume that final value again. Preserve plain sync results.",
        "hook-result-roundtrip": "before_tool precedes the handler and successful result construction precedes after_tool. For the new synchronous factory path, its returned awaitable must complete before success and after_tool; the resolved factory value is the final JSON-roundtrippable output, never a pending factory awaitable. Direct async final return objects retain existing behavior and are not subject to an additional await or new serialization restriction.",
    }
    for item in packet["required_behavior"]:
        if item["id"] in text:
            item["text"] = text[item["id"]]
    packet["required_order"] = [
        "before_tool then handler invocation then completion of that invocation (including one returned-awaitable resolution for a synchronous factory only) then result construction then after_tool"
    ]
    packet["forbidden_orderings"] = [
        "No success result or after_tool before handler invocation completes or, for synchronous factories only, before their returned awaitable completes; no success result or after_tool on timeout, deferred error or cancellation"
    ]
    packet["acceptance_scenarios"].append(
        {
            "id": "async-final-generality",
            "text": "A direct async handler may return a Future, custom awaitable or coroutine as its final value. Preserve the exact object and do not consume it, as in the original behavior.",
            "observables": {
                "output_identity": "unchanged",
                "inner_consumptions": "zero",
                "handler_calls": "one",
            },
        }
    )
    config = read(root / ".agent/compat-config.json")
    for check in config["validation_profiles"]["project-strict"]["commands"][:2]:
        check["argv"].append(GENERAL)
    write(root / ".agent/scope-packet.json", packet)
    write(root / ".agent/scope-config.json", config)
    # The common runner selects these convenience paths, never the archived inputs.
    shutil.copyfile(
        root / ".agent/scope-packet.json", root / ".agent/compat-packet.json"
    )
    shutil.copyfile(
        root / ".agent/scope-config.json", root / ".agent/compat-config.json"
    )
    if digest(root / TARGET) != digest(FROZEN / TARGET) or packet["review_feedback"]:
        raise ValueError(
            "fresh qualification must start at original source without inherited repair"
        )
    write(
        root / ".agent/scope-freeze.json",
        {
            "packet": digest(root / ".agent/compat-packet.json"),
            "config": digest(root / ".agent/compat-config.json"),
            "source": digest(root / TARGET),
        },
    )


def run(arm):
    configure()
    verify_hashes(
        KIT / "benchmarks", read(BASE / "registration.json")["adapter_sha256"]
    )
    root = BASE / arm
    frozen = read(root / ".agent/scope-freeze.json")
    verify_hashes(
        root,
        {
            ".agent/compat-packet.json": frozen["packet"],
            ".agent/compat-config.json": frozen["config"],
            TARGET: frozen["source"],
        },
    )
    native.run(arm)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("freeze", "prepare", "run"))
    parser.add_argument("--arm", choices=ARMS, default=ARMS[0])
    args = parser.parse_args()
    if args.action == "freeze":
        freeze()
    else:
        {"prepare": prepare, "run": run}[args.action](args.arm)
