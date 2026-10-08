"""Replay an actual failed draft through validation; zero model/acceptance credit."""

import copy
import hashlib
import json
import shutil
from pathlib import Path

from capability_fit import WORK, load_worker, write

BASE = WORK / "roleq-whitespace-replay-1"
SNAPSHOT = WORK / "roleq-whitespace-candidate-1"
SOURCE = WORK / "roleq-dependent-retention-2/runs/v1/chain1/bounded-report-round-1"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main():
    BASE.mkdir(exist_ok=False)
    final = (SOURCE / "src/product/config.py").read_text(encoding="utf-8")
    worker = load_worker(SNAPSHOT)
    for enabled in (False, True):
        label = "on" if enabled else "off"
        root = BASE / label
        root.mkdir()
        for name in ("src", "tests"):
            shutil.copytree(
                SOURCE / name, root / name, ignore=shutil.ignore_patterns("__pycache__")
            )
        shutil.copyfile(SOURCE / "pyproject.toml", root / "pyproject.toml")
        initial = "def parse_limit(value):\n    return int(value)\n"
        (root / "src/product/config.py").write_text(initial, encoding="utf-8")
        config = read(SOURCE / ".agent/config.json")
        config["autoformat_on_diff_whitespace"] = enabled
        packet = copy.deepcopy(read(SOURCE / ".agent/limit-contract-bound.json"))
        identity = "whitespace-replay-" + label
        packet.update(
            task_id=identity, run_id=identity + "-synthetic", feature_id=identity
        )
        packet.pop("primary_plan_sha256", None)
        write(root / ".agent/config.json", config)
        write(root / ".agent/packet.json", packet)
        runtime = worker.WorkerRuntime(root, packet, config, None)
        runtime.write_lock.acquire()
        try:
            runtime._prepare_run_archive()
            observed = runtime.read_file({"path": "src/product/config.py"})
            runtime.safe_replace(
                {
                    "path": "src/product/config.py",
                    "expected_sha256": observed["sha256"],
                    "find": initial,
                    "replace": final,
                }
            )
            result = runtime.validate(
                {"contract_check": runtime.contract_check_template()}
            )
            write(
                root / "result.json",
                {
                    "synthetic": True,
                    "model_calls": 0,
                    "result": result,
                    "autoformat_used": runtime.autoformat_used,
                    "validation_attempts": runtime.validation_refs,
                    "terminal": runtime._validated_terminal_state(),
                },
            )
            assert result["status"] == "failed"
            assert not runtime._validated_terminal_state()
            if enabled:
                assert runtime.autoformat_used and len(runtime.validation_refs) == 2
                assert runtime.validation.focused_tests["junit"]["failures"] == 2
            else:
                assert not runtime.autoformat_used and len(runtime.validation_refs) == 1
                assert runtime.validation.focused_tests["status"] == "not_run"
        finally:
            runtime.close()
    write(
        BASE / "manifest.json",
        {
            "classification": "deterministic replay, not model improvement",
            "source": str(SOURCE),
            "draft_sha256": hashlib.sha256(final.encode()).hexdigest(),
            "snapshot": str(SNAPSHOT),
            "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "result": "off stops before tests; on retains failed whitespace attempt, formats once, then exposes two semantic test failures; neither terminal",
        },
    )
    print(BASE)


if __name__ == "__main__":
    main()
