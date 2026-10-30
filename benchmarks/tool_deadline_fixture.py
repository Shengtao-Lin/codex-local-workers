"""Freeze a twentieth protected test for the observed extra-timer blind spot."""

import argparse
import shutil

from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read
from layer_isolation import command, verify_hashes
from tool_awaitable_trial import PYTHON, TARGET
from tool_primary_verification import junit_counts

BASE = WORK / "tool-deadline-fixture-2"
FROZEN = KIT / "benchmarks/fixtures/tool-awaitable-v14"
TEST = "tests/unit/test_deadline_registration.py"


def register():
    previous = KIT / "benchmarks/fixtures/tool-awaitable-v12"
    provenance = read(previous / "provenance.json")
    verify_hashes(previous, provenance["files"])
    FROZEN.mkdir(parents=True, exist_ok=False)
    for name in provenance["files"]:
        destination = FROZEN / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(previous / name, destination)
    shutil.copyfile(
        KIT / "benchmarks/fixtures/tool-awaitable-extra/test_deadline_registration.py",
        FROZEN / TEST,
    )
    for args in (["check", "--fix"], ["format"]):
        result = command(FROZEN, [str(PYTHON), "-B", "-m", "ruff", *args, TEST])
        write(BASE / ("prepare-" + args[0] + ".json"), result)
        if result["exit"] != 0:
            raise ValueError("new protected test target-project formatting failed")
    provenance["files"][TEST] = digest(FROZEN / TEST)
    provenance["previous_fixture"] = str(previous)
    provenance["coverage"] = (
        "Prior nineteen protected tests unchanged; actual CPython 3.12 asyncio.Timeout registrations distinguish one existing execution deadline from an extra inner timer. Not a duration-extension assertion or arbitrary interpreter guarantee."
    )
    write(FROZEN / "provenance.json", provenance)
    actual = {
        "positive": WORK / "tool-plain-result-3/fresh-1",
        "hidden": WORK / "tool-native-nudge-1/fresh-2",
    }
    expected_sha = {
        "positive": "fb7f6b645a665e05eb2e73c6462f9c234a3e63a0b4f4032a1269489b9e6d32d7",
        "hidden": "fa9b5ffbfdf258f760f58e574cb45e6df06e4d0daa81c8442c90bab9108e6e03",
    }
    facts = {}
    for kind, source in actual.items():
        if digest(source / TARGET) != expected_sha[kind]:
            raise ValueError("actual immutable comparison source drift")
        root = BASE / kind
        shutil.copytree(FROZEN, root)
        shutil.copyfile(source / TARGET, root / TARGET)
        write(
            root / ".agent/pyright.json",
            read(actual["positive"] / ".agent/pyright.json"),
        )
        checks = [
            command(root, [str(PYTHON), "-B", "-m", "ruff", *args, TARGET, TEST])
            for args in (["format", "--check"], ["check"])
        ]
        if kind == "positive":
            checks.append(
                command(
                    root,
                    [
                        str(PYTHON),
                        "-B",
                        "-m",
                        "pyright",
                        "--project",
                        ".agent/pyright.json",
                        "--pythonpath",
                        str(PYTHON),
                    ],
                )
            )
        tests = command(
            root,
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
        counts = junit_counts(root / ".agent/preflight.xml")
        expected = {
            "tests": 20,
            "failure": 0 if kind == "positive" else 2,
            "error": 0,
            "skipped": 0,
        }
        valid = (
            counts == expected
            and all(check["exit"] == 0 for check in checks)
            and (tests["exit"] == 0 if kind == "positive" else tests["exit"] != 0)
        )
        verify_hashes(
            root,
            {name: sha for name, sha in provenance["files"].items() if name != TARGET},
        )
        if digest(root / TARGET) != expected_sha[kind]:
            raise ValueError("source changed in preflight")
        facts[kind] = {
            "passed_preflight": valid,
            "checks": checks,
            "test_invocation": tests,
            "junit": counts,
            "source_sha256": expected_sha[kind],
            "primary_only": True,
        }
        write(root / ".agent/preflight.json", facts[kind])
        if not valid:
            raise ValueError(
                "actual positive/negative fixture preflight failed: " + kind
            )
    write(
        BASE / "registration.json",
        {
            "fixture_version": 14,
            "tests": 20,
            "facts": facts,
            "files": provenance["files"],
            "driver_sha256": digest(KIT / "benchmarks/tool_deadline_fixture.py"),
            "credit": "Primary-authored protection coverage, not new Coder/Reviewer/Explorer/Coordinator or savings",
            "weekly_ceiling": 30,
        },
    )
    print(
        {
            "frozen": str(FROZEN),
            "positive": facts["positive"]["junit"],
            "hidden": facts["hidden"]["junit"],
            "model_credit": False,
        }
    )


if __name__ == "__main__":
    argparse.ArgumentParser(allow_abbrev=False).parse_args()
    register()
