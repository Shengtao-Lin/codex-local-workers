"""Real archived failure inputs, deterministic no-op script; zero new LLM calls."""

import json
import shutil
from pathlib import Path

from capability_fit import WORK, load_worker, write
from inherited_context_recovery import digest, read

BASE = WORK / "noop-primary-replay-3"
ORIGINAL = WORK / "reviewer-real-unit-1/candidate"
TASK = "reviewer-real-unit-1"
RUN = TASK + "-timestamp-unit-a1"
ARCHIVE = ORIGINAL / ".agent/tasks" / TASK / "runs" / RUN
SOURCE = "src/evaluation_harness/adapters/common.py"


class ScriptClient:
    context_length = 24576
    max_tokens = 4096

    def __init__(self):
        self.turns = 0

    def complete(self, messages):
        self.turns += 1
        if self.turns == 1:
            action = {
                "action": "READ_FILE",
                "arguments": {"path": SOURCE, "start_line": 251, "end_line": 257},
            }
        elif self.turns == 2:
            action = {
                "action": "VALIDATE",
                "arguments": {
                    "contract_check": read(ARCHIVE / "validation-attempt-2.json")[
                        "validation"
                    ]["contract_check"]
                },
            }
        else:
            action = {
                "action": "SAFE_REPLACE",
                "arguments": {
                    "path": SOURCE,
                    "find": 'value.strip().replace("Z", "+00:00")',
                    "replace": 'value.strip().replace("Z", "+00:00")',
                },
            }
        assert self.turns <= 6, "Unexpected model turn; bounded script exhausted"
        return json.dumps(action)


def main():
    BASE.mkdir(exist_ok=False)
    original_hashes = {p.name: digest(p) for p in ARCHIVE.iterdir() if p.is_file()}
    rows = []
    for arm in ("baseline", "candidate"):
        snapshot = WORK / f"noop-primary-{arm}-1"
        for path, sha in read(snapshot / "freeze.json")["files"].items():
            assert digest(snapshot / path) == sha
        module = load_worker(snapshot)
        root = BASE / arm
        for path in ("src", "tests"):
            shutil.copytree(ORIGINAL / path, root / path)
        shutil.copy2(ORIGINAL / "pyproject.toml", root / "pyproject.toml")
        packet = read(ARCHIVE / "packet.json")
        packet.update(
            task_id="noop-replay-" + arm,
            feature_id="noop-replay-" + arm,
            run_id="noop-replay-" + arm + "-a1",
        )
        config = read(ORIGINAL / ".agent/config.json")
        before = {
            p.relative_to(root).as_posix(): digest(p)
            for p in root.rglob("*")
            if p.is_file()
        }
        client = ScriptClient()
        runtime = module.WorkerRuntime(root, packet, config, client)
        report = runtime.run()
        assert report["status"] == "failed"
        assert report["validation"]["focused_tests"]["junit"]["failures"] == 2
        assert report["changed_files"] == []
        assert runtime.repairs == 0
        assert runtime.validation_count == 1
        assert all(digest(root / path) == sha for path, sha in before.items())
        expected_turns = 6 if arm == "baseline" else 4
        assert client.turns == expected_turns
        if arm == "candidate":
            assert report["failure_reason"] == "repeated_noop_after_failed_validation"
            assert (
                "Do not assume the test is stale" in report["remaining_uncertainty"][0]
            )
        rows.append(
            {
                "arm": arm,
                "script_turns": client.turns,
                "failure_reason": report["failure_reason"],
                "validation_attempts": runtime.validation_count,
                "repairs": runtime.repairs,
                "source_tests_unchanged": True,
                "archive": str(runtime.archive.run_root),
            }
        )
    assert all(digest(ARCHIVE / path) == sha for path, sha in original_hashes.items())
    write(
        BASE / "results.json",
        {
            "rows": rows,
            "original_archive_unchanged": True,
            "new_model_calls": 0,
            "scripted_not_actual_model_repetition": True,
            "driver_sha256": digest(Path(__file__)),
            "classification": "Historical exact source/tests/contract, scripted no-op tail and real pytest failures; not raw model-output replay or model stability improvement.",
        },
    )
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
