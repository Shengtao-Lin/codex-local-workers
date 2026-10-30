"""Two frozen real-source transfer units using the qualified narrow controller."""

import argparse
import os
import shutil
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import capture_fixture_support as F
import limited_family_trial as L
import normal_task_trial as N
import reasoning_wire_candidate as W

BATCH = S.KIT / "benchmarks/work/harness-convergence/limited-time-transfer-20261020-2"
UP = Path(
    "F:/ChatGPT/agent-evaluation-harness/src/evaluation_harness/adapters/common.py"
)
ORDER = ["time-1", "time-2"]
HEADER = "from __future__ import annotations\nfrom datetime import UTC, datetime\nfrom typing import Any\n"
CONTRACT = "Keep _datetime(value: Any, default: datetime) signature. For datetime input or a string accepted by the existing fromisoformat(value.replace('Z', '+00:00')) parser, return a timezone-aware UTC datetime for the same instant: naive accepted values are interpreted as UTC; aware accepted values convert their offset to UTC, including date rollover. Do not mutate input or default. For all other value types return the original default object unchanged, even if that default is naive or non-UTC. Invalid strings still propagate ValueError; do not silently replace them with default or broaden the parser's accepted syntax. Preserve existing UTC values and fractional seconds. This is a real copied source slice, not permission to edit its upstream repository."
REFERENCE = """def _datetime(value: Any, default: datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        return default
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
"""
PUBLIC = """from datetime import UTC, datetime, timedelta, timezone
import pytest
from product.code import _datetime

@pytest.mark.parametrize(("value", "hour"), [(datetime(2026, 1, 1, 0, 0), 0), (datetime(2026, 1, 1, 0, 0, tzinfo=timezone(timedelta(hours=-3))), 3), ("2026-01-01T00:00:00-03:00", 3), ("2026-01-01T00:00:00Z", 0)])
def test_utc(value, hour):
    default = datetime(2000, 1, 1)
    result = _datetime(value, default)
    assert result.tzinfo is UTC
    assert result.hour == hour

def test_fallback_and_invalid_string():
    default = datetime(2000, 1, 1)
    for value in [None, False, 0, [], {}]:
        assert _datetime(value, default) is default
    with pytest.raises(ValueError):
        _datetime("not-a-time", default)
"""
PRIVATE = """from datetime import UTC, datetime, timedelta, timezone
import pytest
from product.code import _datetime

@pytest.mark.parametrize("value", ["2026-01-01T00:15:00.123456+01:00", datetime(2026, 1, 1, 0, 15, 0, 123456, tzinfo=timezone(timedelta(hours=1)))])
def test_rollover_and_microseconds(value):
    default = datetime(2001, 1, 1)
    expected = datetime(2025, 12, 31, 23, 15, 0, 123456, tzinfo=UTC)
    assert _datetime(value, default) == expected
    assert _datetime(value, default).tzinfo is UTC

def test_non_utc_fallback_and_inputs():
    default = datetime(2000, 1, 1, tzinfo=timezone(timedelta(hours=5)))
    value = {"timestamp": "2026-01-01"}
    assert _datetime(value, default) is default
    assert value == {"timestamp": "2026-01-01"}
    assert default.utcoffset() == timedelta(hours=5)
    naive = datetime(2026, 1, 1, 0, 0, 0, 555)
    assert _datetime(naive, default) == naive.replace(tzinfo=UTC)
    assert naive.tzinfo is None
    for text in ["", "invalid", "2026-13-01"]:
        with pytest.raises(ValueError):
            _datetime(text, default)
"""
PROBE = """def observe(value: str | None, default_iso: str) -> str:
    return _datetime(value, datetime.fromisoformat(default_iso)).isoformat()
"""


def prepare():
    assert S.read(L.BATCH / "decision.json")["accepted"] == 6
    template = BATCH / "template"
    for path, text in {
        "src/product/__init__.py": "",
        "src/product/code.py": HEADER
        + "\n\n"
        + T.extract(UP, "_datetime")
        + "\n\n"
        + PROBE,
        "tests/test_contract.py": PUBLIC,
    }.items():
        T.write(template / path, text)
    shutil.copyfile(L.SEED / "pyproject.toml", template / "pyproject.toml")
    private = BATCH / "private/test_independent.py"
    T.write(private, PRIVATE)
    proof = BATCH / "reference-checks"
    shutil.copytree(template, proof)
    (proof / "src/product/code.py").write_text(
        HEADER + "\n\n" + REFERENCE + "\n\n" + PROBE, encoding="utf-8"
    )
    for root in (template, proof):
        for args in (("check", "--select", "I", "--fix"), ("format",)):
            assert (
                T.run([S.PYTHON, "-m", "ruff", *args, "src", "tests"], root)[
                    "exit_code"
                ]
                == 0
            )
    baseline = T.run([S.PYTHON, "-B", "-m", "pytest", "-q", "tests"], template)
    checks = L.checks(proof, private)
    S.save(
        BATCH / "task-controls.json",
        {
            "baseline": baseline,
            "reference": checks,
            "upstream": str(UP),
            "upstream_sha256": S.sha(UP),
            "starting_function_sha256": S.sha(template / "src/product/code.py"),
        },
    )
    assert baseline["exit_code"] == 1 and all(c["exit_code"] == 0 for c in checks)
    rows = {}
    for cell in ORDER:
        root = BATCH / "cells" / cell / "isolated"
        shutil.copytree(template, root)
        shutil.copytree(
            S.KIT / ".local-agents",
            root / ".local-agents",
            ignore=shutil.ignore_patterns("tests", "__pycache__", ".ruff_cache"),
        )
        W.patch_client(root / ".local-agents/worker-runtime.py", root)
        identity = {
            k: "time-transfer-20261020-1-" + cell
            for k in ("task_id", "unit_id", "run_id")
        }
        packet = S.read(L.SEED / ".agent/packet.json")
        packet.update(
            identity,
            feature_id="time-utc-transfer",
            goal=CONTRACT,
            primary_plan_sha256=S.sha(__file__),
        )
        target = "src/product/code.py"
        sources = [
            "src/product/__init__.py",
            target,
            "tests/test_contract.py",
            "pyproject.toml",
        ]
        packet["scope"]["readonly"] = [p for p in sources if p != target] + [
            F.POLICY_PATH,
            F.PRODUCER,
            F.HELPER,
        ]
        packet["owned_contract_ids"] = ["utc"]
        packet["edit_targets"] = [{"path": target, "anchor": "def _datetime("}]
        packet["required_behavior"] = [
            {
                "id": "utc",
                "text": CONTRACT,
                "risk_floor": "high",
                "implementation_ref": {"path": target, "symbol": "_datetime"},
            }
        ]
        packet["acceptance_criteria"] = [
            {"id": "utc", "text": "Contract, full profile and protected input identity"}
        ]
        packet["review_feedback"] = []
        config = S.read(L.SEED / ".agent/config.json")
        config["coder_single_function"] = {
            "path": target,
            "symbol": "_datetime",
            "dependencies": HEADER,
        }
        _, digest = F.install_material(
            root,
            identity,
            source_paths=sources,
            target={
                "path": target,
                "module": "product.code",
                "symbol": "observe",
            },
            family="json-call-model-dump-v1",
            cases=[
                {"args": [value, "2000-01-01T00:00:00"], "kwargs": {}}
                for value in ["2026-01-01T00:00:00-03:00", None, "invalid"]
            ],
            writable=[target],
            python=S.PYTHON,
        )
        config["experimental_capture_policy_sha256"] = digest
        S.save(root / ".agent/packet.json", packet)
        S.save(root / ".agent/config.json", config)
        control = T.run(L.command(root, "preflight"), root)
        S.save(BATCH / "preflight" / (cell + ".json"), control)
        assert control["exit_code"] == 0
        if cell == ORDER[0]:
            replay_root = BATCH / "full-chain-replay/isolated"
            shutil.copytree(root, replay_root)
            replay = replay_root.parent / "reference.json"
            S.save(replay, [{"replacement": T.extract(proof / target, "_datetime")}])
            result = T.run(
                L.command(replay_root, replay=replay), replay_root, timeout=180
            )
            S.save(replay_root.parent / "process.json", result)
            assert result["exit_code"] == 0
        rows[cell] = {
            "root": str(root),
            "topic": "utc",
            "identity": identity,
            "target": target,
            "private_tests": str(private),
            "files": {
                p.relative_to(root).as_posix(): S.sha(p)
                for p in root.rglob("*")
                if p.is_file()
                and not any(
                    v in p.parts
                    for v in ("__pycache__", ".pytest_cache", ".ruff_cache")
                )
            },
        }
    S.save(BATCH / "cells.json", rows)
    S.save(
        BATCH / "registration.json",
        {
            "order": ORDER,
            "registered": 2,
            "weekly_stop": 50,
            "batch_seconds": 5400,
            "pins": {
                str(p): S.sha(p)
                for p in [
                    Path(__file__),
                    *list((S.KIT / "benchmarks").glob("*.py")),
                    private,
                    BATCH / "cells.json",
                ]
            },
            "gate": "2/2 independent accepted complete chains, no hints/takeover or scope drift; ordinary failure HOLD and complete fixed second cell; infrastructure/safety/time/weekly50 stop",
            "candidate": "Unchanged qualified narrow bounded-source/focused-repair/static-focus + original contract-first Reviewer",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "owned_contract_ids": ["utc"],
            "risk_rationale": "Public datetime compatibility, timezone/invalid-input and fallback identity invariants",
            "budget": "Same12requests/3edits/3postchecks/900s/4096output; Reviewer16requests/4errors/600s/4096output",
            "roles": "Coder Qwen, Reviewer Muse; Explorer unnecessary for already-located source; Coordinator NOT_RUN",
            "exposure": "First Worker exposure to this new UTC contract on actual unchanged sibling function; same known single-function family, not general benchmark proof",
            "Primary_preparation": "Hard outcomes, protected tests and separate reference proof only; no algorithm guidance",
        },
    )
    print("Two real-source UTC transfer cells frozen; no live calls")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=("prepare", "run"))
    p.add_argument("--cell", choices=ORDER)
    p.add_argument("--weekly-used", type=int)
    p.add_argument("--observed-at", type=float)
    args = p.parse_args()
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if args.mode == "prepare":
        prepare()
    else:
        N.run(
            args.cell,
            args.weekly_used,
            args.observed_at,
            batch=BATCH,
            order=ORDER,
            build_command=L.command,
            usage_limit=50,
            batch_seconds=5400,
        )
