"""Real failed pytest plus Ruff, without a model or implementation credit."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from capability_fit import load_worker, write
from v13_scoped_audit import WORK, checked_snapshot


def run(snapshot_label: str) -> None:
    snapshot = checked_snapshot(snapshot_label)
    worker = load_worker(snapshot)
    for enabled in (False, True):
        identity = f"v13-diag-real-{snapshot_label}-{'opted' if enabled else 'default'}"
        root = WORK / identity
        root.mkdir(exist_ok=False)
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "src/example.py").write_text(
            "VALUE = 1\n\n\ndef optional():\n    return missing_name\n",
            encoding="utf-8",
        )
        (root / "tests/test_example.py").write_text(
            "from src.example import VALUE\n\n\ndef test_value():\n    assert VALUE == 2\n",
            encoding="utf-8",
        )
        (root / "pyproject.toml").write_text(
            '[tool.pytest.ini_options]\npythonpath = ["."]\n', encoding="utf-8"
        )
        commands = [
            {
                "id": "ruff-format",
                "argv": ["{python}", "-m", "ruff", "format", "--check", "src", "tests"],
            },
            {
                "id": "ruff-check",
                "argv": ["{python}", "-m", "ruff", "check", "src", "tests"],
            },
        ]
        if enabled:
            for command in commands:
                command["run_on_test_failure"] = True
        config = {
            "python": sys.executable,
            "validation_profiles": {
                "python-focused": {"python": sys.executable, "commands": commands}
            },
        }
        packet = {
            "schema_version": 1,
            "task_id": identity,
            "run_id": identity + "-synthetic",
            "goal": "Keep actual failed tests failed while collecting explicitly trusted static diagnostics.",
            "scope": {
                "modify": ["src/example.py"],
                "create": [],
                "read": ["src", "tests"],
                "readonly": ["tests"],
                "forbidden": [],
            },
            "required_behavior": ["VALUE is 2"],
            "acceptance_criteria": ["Focused tests pass"],
            "focused_tests": ["tests/test_example.py"],
        }
        protected = [
            root / p
            for p in ("src/example.py", "tests/test_example.py", "pyproject.toml")
        ]
        before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in protected]
        runtime = worker.WorkerRuntime(root, packet, config, None)
        runtime.write_lock.acquire()
        try:
            runtime._prepare_run_archive()
            result = runtime.validate({})
            assert result["status"] == "failed"
            assert runtime.validation.focused_tests["junit"]["executed"] == 1
            assert len(runtime.validation.configured_checks) == (2 if enabled else 0)
            assert before == [
                hashlib.sha256(p.read_bytes()).hexdigest() for p in protected
            ]
            assert runtime.edit_revision == runtime.repairs == 0
            assert not runtime._validated_terminal_state()
            if enabled:
                assert "F821" in str(
                    runtime._configured_check_repair_hint(
                        runtime.validation.configured_checks
                    )
                )
            report = runtime.report(
                "failed",
                ["Intentional deterministic fixture; no model called."],
                "intentional_fixture_failure",
                [],
            )
            report["synthetic_benchmark_archive"] = True
            runtime._complete_run(report)
            write(
                root / "result.json",
                {
                    "snapshot": snapshot_label,
                    "driver_sha256": hashlib.sha256(
                        Path(__file__).read_bytes()
                    ).hexdigest(),
                    "diagnostic_opt_in": enabled,
                    "coder_calls": 0,
                    "protected_unchanged": True,
                    "validation": result,
                },
            )
        finally:
            runtime.close()
        print(
            identity
            + ": verified failed tests, unchanged files and diagnostic execution policy"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True)
    run(parser.parse_args().snapshot)
