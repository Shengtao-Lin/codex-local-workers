from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[1] / "run-state.py"
SPEC = importlib.util.spec_from_file_location("run_state_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
RUN_STATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUN_STATE
SPEC.loader.exec_module(RUN_STATE)


class RunStateTests(unittest.TestCase):
    def test_git_commands_use_containing_repo_as_process_local_safe_directory(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / ".git").mkdir()
            nested = root / "nested" / "work"
            nested.mkdir(parents=True)
            completed = subprocess.CompletedProcess([], 0, stdout="abc\n", stderr="")
            with patch.object(RUN_STATE.subprocess, "run", return_value=completed) as called:
                result = RUN_STATE._run_git(nested, ["rev-parse", "HEAD"])
            argv = called.call_args.args[0]
            self.assertEqual(
                argv[:3], ["git", "-c", f"safe.directory={root.as_posix()}"]
            )
            self.assertEqual(argv[3:5], ["-C", str(nested)])
            self.assertTrue(result["available"])


if __name__ == "__main__":
    unittest.main()
