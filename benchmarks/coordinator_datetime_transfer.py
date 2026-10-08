"""Registered read-only-source transfer; isolated private helper, not deployment."""

import argparse
import copy
import json
import sys
from pathlib import Path

import coordinator_label_evidence as evidence
import coordinator_label_pilot as pilot
import coordinator_numeric_split as split
from capability_fit import WORK, load_worker, write
from inherited_context_recovery import digest, read

BASE = WORK / "coordinator-datetime-transfer-1"
SNAPSHOT = WORK / "coordinator-report-baseline-2"
SOURCE = Path(
    "F:/ChatGPT/agent-evaluation-harness/src/evaluation_harness/adapters/common.py"
)
HEADER = "from datetime import UTC, datetime\nfrom typing import Any\n\n\n"
INITIAL = (
    HEADER.replace("import UTC,", "import UTC as UTC,")
    + """def _datetime(value: Any, default: datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return default
    return default
"""
)
TESTS = """from datetime import UTC, datetime, timedelta, timezone

import pytest

from product.entry import normalize_time
from product.target import _datetime

DEFAULT = datetime(2000, 1, 1, tzinfo=UTC)


def test_datetime_identity():
    for value in (datetime(2026, 1, 1), datetime(2026, 1, 1, tzinfo=UTC)):
        assert _datetime(value, DEFAULT) is value


def test_utc_suffix():
    assert _datetime("2026-10-07T03:04:05Z", DEFAULT) == datetime(
        2026, 10, 7, 3, 4, 5, tzinfo=UTC
    )


def test_offset_preserved():
    value = _datetime("2026-10-07T03:04:05+05:30", DEFAULT)
    assert value.utcoffset() == timedelta(hours=5, minutes=30)
    assert value.hour == 3 and value.minute == 4
    assert value.tzinfo == timezone(timedelta(hours=5, minutes=30))


def test_naive_string_utc():
    value = _datetime("2026-10-07T03:04:05", DEFAULT)
    assert value == datetime(2026, 10, 7, 3, 4, 5, tzinfo=UTC)
    assert value.tzinfo is UTC


def test_fallback_identity():
    for value in (None, False, 0, 1.5, {}, [], object()):
        assert _datetime(value, DEFAULT) is DEFAULT


def test_invalid_string():
    for value in ("", "not-a-date", "2026-13-07", " "):
        with pytest.raises(ValueError):
            _datetime(value, DEFAULT)


def test_entry_roundtrip():
    text = "2026-10-07T03:04:05"
    assert normalize_time(text, DEFAULT) == datetime(2026, 10, 7, 3, 4, 5, tzinfo=UTC)
    assert text == "2026-10-07T03:04:05"
    assert normalize_time(None, DEFAULT) is DEFAULT
    with pytest.raises(ValueError):
        normalize_time("bad", DEFAULT)
"""
QUESTION = (
    "Locate the existing private _datetime function in src/product/target.py, its "
    "normalize_time caller in src/product/entry.py, and test_naive_string_utc plus "
    "test_invalid_string assertions in tests/test_target.py. One definition/caller/test "
    "localization question only. Read these three actual files and cite small actual "
    "ranges, preferably one reference per path. Do not predict repairs or validation."
)


def case():
    return {
        "case_id": "private-datetime",
        "origin": "read-only real private helper extraction, explicitly injected mutant",
        "goal": "Restore the frozen private timestamp transformation without changing its existing semantics.",
        "feature_risk": "medium",
        "integration_risk": "medium",
        "files": {
            "src/product/target.py": INITIAL,
            "src/product/entry.py": "from product.target import _datetime\n\n\ndef normalize_time(value, default):\n    return _datetime(value, default)\n",
            "tests/test_target.py": TESTS,
        },
        "units": [
            {
                "unit_id": "normalize-unit",
                "risk": "medium",
                "dependencies": [],
                "path": "src/product/target.py",
                "anchor": "_datetime",
                "tests": [
                    f"tests/test_target.py::{name}"
                    for name in (
                        "test_datetime_identity",
                        "test_utc_suffix",
                        "test_offset_preserved",
                        "test_naive_string_utc",
                        "test_fallback_identity",
                        "test_invalid_string",
                        "test_entry_roundtrip",
                    )
                ],
                "contract": (
                    "Restore private _datetime(value, default): existing datetime values are returned "
                    "by identity, including naive datetimes. Strings use datetime.fromisoformat "
                    "after replacing Z with +00:00; parsed aware strings retain their offset and "
                    "wall time, parsed naive strings receive UTC tzinfo without time shifting. "
                    "Invalid strings propagate ValueError, not fallback. All non-string, "
                    "non-datetime values return the supplied default by identity. Input/default "
                    "remain unchanged. The read-only normalize_time caller preserves the same "
                    "results/errors. No wider adapter, public API, dataset identity or policy changes."
                ),
                "acceptance_scenarios": [
                    {
                        "id": "normal",
                        "text": "Preserve aware offsets and datetime identity.",
                        "observables": {"identity": True, "offset_minutes": 330},
                    },
                    {
                        "id": "error",
                        "text": "Invalid strings propagate through the caller.",
                        "observables": {"exception": "ValueError", "fallback": False},
                    },
                    {
                        "id": "boundary",
                        "text": "Naive string gets UTC; non-string keeps default identity.",
                        "observables": {
                            "naive_string_tz": "UTC",
                            "default_identity": True,
                        },
                    },
                ],
            }
        ],
    }


def configure():
    pilot.BASE, pilot.SNAPSHOT = BASE, SNAPSHOT
    pilot.fixture = sys.modules[__name__]
    split.BASE, split.SNAPSHOT = BASE, SNAPSHOT
    split.QUESTIONS = {
        "flow": (
            ["src/product/target.py", "src/product/entry.py", "tests/test_target.py"],
            QUESTION,
        )
    }
    return pilot.configure()


def prepare():
    contract = configure()
    pilot.matrix.SCOPE.FA.LAYER.verify_hashes(
        SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"]
    )
    source_text = SOURCE.read_text(encoding="utf-8")
    definition = source_text[source_text.index("def _datetime(") :]
    # Exact extracted body remains separately frozen outside all worker-readable roots.
    reference = HEADER + definition
    BASE.mkdir(exist_ok=False)
    write(
        BASE / "source-provenance.json",
        {
            "source": str(SOURCE),
            "source_sha256": digest(SOURCE),
            "original_definition": definition,
            "extraction": "unchanged final private function plus required imports",
            "fixture_only_caller": True,
            "synthetic_defects": ["naive UTC omitted", "invalid string swallowed"],
            "production_bug_claim": False,
            "whole_project_qualification": False,
            "risk_rationale": "Isolated private pure transform in kit; public adapter compatibility, security, persistence and deployment are excluded, not downgraded.",
            "weekly_used_start": 6,
            "weekly_used_ceiling": 15,
            "primary_active_seconds": None,
            "cloud_tokens": None,
        },
    )
    write(BASE / "corpus.json", {"cases": [case()]})
    write(
        BASE / "primary-oracles.json",
        {
            "private-datetime": {
                "reference": {"src/product/target.py": reference},
                "mutants": [
                    {"src/product/target.py": INITIAL},
                    {
                        "src/product/target.py": reference.replace(
                            "return value\n", "return value.replace(tzinfo=UTC)\n", 1
                        )
                    },
                ],
            }
        },
    )
    config = read(
        WORK
        / "coordinator-numeric-repeat-1/runs/v1/numeric5-control/labelled-receipt-round-1/.agent/config.json"
    )
    cells = []
    for arm in ("control", "coordinator"):
        settings = copy.deepcopy(config)
        settings["coordinator_enabled"] = arm == "coordinator"
        settings["explorer_required_citation_paths"] = split.QUESTIONS["flow"][0]
        path = BASE / f"{arm}-config.json"
        write(path, settings)
        root = Path(
            pilot.matrix.MIXED.prepare("private-datetime", 1, path, "datetime1-" + arm)[
                "root"
            ]
        )
        # This frozen extraction uses the real project's mandatory Ruff rules.
        # It has no package/dependency graph, so whole-project strict Pyright is
        # explicitly not established by this isolated experiment.
        project = root / "pyproject.toml"
        project.write_text(
            project.read_text(encoding="utf-8").replace(
                '["E4", "E7", "E9", "F"]', '["E", "F", "I", "UP", "B", "ASYNC", "RUF"]'
            ),
            encoding="utf-8",
        )
        plan = read(root / ".agent/feature-plan.json")
        packet = read(root / ".agent/normalize-unit-reference.json")
        packet["primary_plan_sha256"] = contract.authority_fingerprint(plan)
        packet = contract.validate_unit_packet(plan, packet)
        load_worker(SNAPSHOT).validate_packet(packet)
        write(root / ".agent/normalize-unit-bound.json", packet)
        paths = [
            *case()["files"],
            "pyproject.toml",
            ".agent/config.json",
            ".agent/feature-plan.json",
            ".agent/normalize-unit-bound.json",
        ]
        cells.append(
            {
                "id": arm + "-r1",
                "arm": arm,
                "case": "private-datetime",
                "root": str(root),
                "units": ["normalize-unit"],
                "hashes": {p: digest(root / p) for p in paths},
            }
        )
    write(
        BASE / "manifest.json",
        {
            "runtime": str(SNAPSHOT),
            "cells": cells,
            "drivers": {
                str(Path(p).resolve()): digest(Path(p))
                for p in (__file__, pilot.__file__, evidence.__file__, split.__file__)
            },
        },
    )
    pilot.matrix.preflight()
    print(json.dumps({"registered": str(BASE), "source_sha256": digest(SOURCE)}))


def run(identity):
    configure()
    root = split.root_for(identity)
    adjudication = read(root / ".agent/flow-explorer-primary.json")
    if (
        not adjudication["success"]
        or digest(root / ".agent/flow-explorer.json") != adjudication["report_sha256"]
    ):
        raise ValueError("actual fresh Explorer acceptance required")
    original = pilot.read

    def selected(path):
        return original(
            root / ".agent/flow-explorer.json"
            if Path(path) == root / ".agent/explorer.json"
            else path
        )

    pilot.read = selected
    pilot.run(identity, "normalize-unit")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "action",
        choices=(
            "prepare",
            "explore",
            "adjudicate",
            "run",
            "check",
            "record",
            "integrate",
        ),
    )
    parser.add_argument("identity", nargs="?")
    parser.add_argument("--summary")
    args = parser.parse_args()
    configure()
    if args.action == "prepare":
        prepare()
    else:
        pilot.matrix.verify()
        if args.action == "explore":
            split.explore(args.identity, "flow")
        elif args.action == "adjudicate":
            split.adjudicate(args.identity, "flow", args.summary)
        elif args.action == "run":
            run(args.identity)
        elif args.action == "check":
            evidence.unit_check(args.identity, "normalize-unit")
        elif args.action == "integrate":
            evidence.integrate(args.identity)
        else:
            import qualification_controls

            qualification_controls.record(
                args.identity, "normalize-unit", "accept", args.summary
            )
