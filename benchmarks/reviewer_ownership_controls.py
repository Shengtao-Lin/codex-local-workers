"""Synthetic Reviewer controls: pending caller versus actual falsy-value loss."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

from capability_fit import WORK, load_worker, write
from inherited_context_recovery import read

BASE = WORK / "reviewer-ownership-controls-1"
SNAPSHOT = WORK / "coordinator-unit-ownership-baseline-1"
TESTS = """import asyncio

import pytest

from product.collector import collect_values


def test_collect_order():
    calls = []

    async def fetch(key):
        calls.append(key)
        return key + 1

    assert asyncio.run(collect_values(fetch, [1, 2])) == [2, 3]
    assert calls == [1, 2]


def test_collect_error():
    error = RuntimeError("same")

    async def fetch(key):
        raise error

    with pytest.raises(RuntimeError) as caught:
        asyncio.run(collect_values(fetch, [1]))
    assert caught.value is error
"""


def main():
    BASE.mkdir(exist_ok=False)
    manifest = read(WORK / "coordinator-limited-retention-1/manifest.json")
    source = Path(manifest["cells"][0]["root"])
    worker = load_worker(SNAPSHOT)
    rows = []
    for variant in ("hidden", "clean"):
        root = BASE / variant
        shutil.copytree(source / "src", root / "src")
        (root / "tests").mkdir()
        (root / "tests/test_target.py").write_text(TESTS, encoding="utf-8")
        shutil.copyfile(source / "pyproject.toml", root / "pyproject.toml")
        (root / "src/product/collector.py").write_text(
            "async def collect_values(fetch, keys):\n    return []\n",
            encoding="utf-8",
        )
        config = read(source / ".agent/config.json")
        config["python"] = sys.executable
        write(root / ".agent/config.json", config)
        packet = read(source / ".agent/collect-unit-bound.json")
        packet.update(
            task_id="ownership-control-" + variant,
            feature_id="ownership-control-" + variant,
            run_id="ownership-control-" + variant + "-a1",
        )
        packet.pop("primary_plan_sha256", None)
        packet["dependencies"] = []
        packet = worker.validate_packet(packet)
        write(root / ".agent/packet.json", packet)
        runtime = worker.WorkerRuntime(root, packet, config, None)
        after = (
            "async def collect_values(fetch, keys):\n    values = []\n    for key in keys:\n"
            "        value = await fetch(key)\n"
            + (
                "        if value:\n            values.append(value)\n"
                if variant == "hidden"
                else "        values.append(value)\n"
            )
            + "    return values\n"
        )
        try:
            runtime.write_lock.acquire()
            runtime._prepare_run_archive()
            observation = runtime.read_file({"path": "src/product/collector.py"})
            runtime.safe_replace(
                {
                    "path": "src/product/collector.py",
                    "expected_sha256": observation["sha256"],
                    "find": (root / "src/product/collector.py").read_text(),
                    "replace": after,
                }
            )
            validation = runtime.validate(
                {"phase": "final", "contract_check": runtime.contract_check_template()}
            )
            if validation["status"] != "passed":
                raise ValueError("synthetic control validation failed")
            _, handoff = runtime.execute(
                {
                    "action": "FINISH_SUCCESS",
                    "arguments": {
                        "summary": [
                            "Primary-authored synthetic Reviewer control; no Coder model invocation"
                        ]
                    },
                }
            )
            handoff["synthetic_benchmark_archive"] = True
            runtime._complete_run(handoff)
        finally:
            runtime.close()
        request = {
            "schema_version": 1,
            "task_id": packet["task_id"],
            "unit_id": packet["unit_id"],
            "run_id": packet["run_id"],
            "review_id": "ownership-control-review-1",
        }
        write(root / ".agent/request.json", request)
        invocation = subprocess.run(
            [
                sys.executable,
                "-B",
                str(SNAPSHOT / ".local-agents/local-review.py"),
                "--request",
                str(root / ".agent/request.json"),
                "--config",
                str(root / ".agent/config.json"),
                "--report",
                str(root / ".agent/reviewer.json"),
            ],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        report = read(root / ".agent/reviewer.json")
        rows.append(
            {
                "variant": variant,
                "exit": invocation.returncode,
                "decision": report["decision"],
                "findings": report["findings"],
                "synthetic_archive": True,
                "coder_model_invocations": 0,
                "protected_test_coverage": "Positive order/error only; intentionally lacks falsy result assertion",
                "primary_adjudication_required": True,
            }
        )
        print(json.dumps(rows[-1]))
    write(
        BASE / "observations-1.json",
        {
            "rows": rows,
            "primary_accepted": False,
            "classification": "Reviewer diagnostic controls, not Coder successes or high-risk qualification",
        },
    )


if __name__ == "__main__":
    main()
