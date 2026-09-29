from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "install_local_agents.py"
)
SPEC = importlib.util.spec_from_file_location(
    "install_local_agents_under_test", MODULE_PATH
)
assert SPEC is not None and SPEC.loader is not None
INSTALL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = INSTALL
SPEC.loader.exec_module(INSTALL)


class InstallLocalAgentsTests(unittest.TestCase):
    def fixtures(self, root: Path) -> tuple[Path, Path]:
        source = root / "source"
        target = root / "target"
        (source / ".local-agents" / "tests").mkdir(parents=True)
        (source / ".local-agents" / ".agent").mkdir()
        (target / ".local-agents").mkdir(parents=True)
        (source / "AGENTS.md").write_text("kit rules", encoding="utf-8")
        (source / ".local-agents" / "worker-runtime.py").write_text(
            "print(1)", encoding="utf-8"
        )
        (source / ".local-agents" / "config.example.json").write_text(
            "{}", encoding="utf-8"
        )
        (source / ".local-agents" / "config.json").write_text(
            "secret source", encoding="utf-8"
        )
        (source / ".local-agents" / ".agent" / "run.json").write_text(
            "secret log", encoding="utf-8"
        )
        (source / ".local-agents" / "tests" / "test_worker.py").write_text(
            "pass", encoding="utf-8"
        )
        (target / ".local-agents" / "config.json").write_text(
            "target config", encoding="utf-8"
        )
        return source, target

    def test_preview_is_read_only_and_apply_preserves_configuration(self) -> None:
        with TemporaryDirectory() as directory:
            source, target = self.fixtures(Path(directory))
            preview = INSTALL.install(source, target)
            self.assertFalse(preview["applied"])
            self.assertIn("AGENTS.md", preview["copy"])
            self.assertFalse((target / "AGENTS.md").exists())
            applied = INSTALL.install(source, target, apply=True)
            self.assertTrue(applied["applied"])
            self.assertEqual((target / "AGENTS.md").read_text(), "kit rules")
            self.assertEqual(
                (target / ".local-agents" / "config.json").read_text(), "target config"
            )
            self.assertFalse((target / ".local-agents" / ".agent").exists())
            self.assertTrue(
                (target / ".local-agents" / "tests" / "test_worker.py").exists()
            )
            self.assertIn(
                str(Path(".local-agents") / "worker-runtime.py"),
                INSTALL.install(source, target)["identical"],
            )

    def test_conflict_blocks_all_writes(self) -> None:
        with TemporaryDirectory() as directory:
            source, target = self.fixtures(Path(directory))
            (target / "AGENTS.md").write_text("project rules", encoding="utf-8")
            with self.assertRaisesRegex(INSTALL.InstallError, "manual review"):
                INSTALL.install(source, target, apply=True)
            self.assertFalse((target / ".local-agents" / "worker-runtime.py").exists())
            self.assertEqual((target / "AGENTS.md").read_text(), "project rules")

    def test_legacy_kit_tests_are_reported_but_never_removed(self) -> None:
        with TemporaryDirectory() as directory:
            source, target = self.fixtures(Path(directory))
            old_test = target / ".local-agents" / "tests" / "test_real_task_eval.py"
            old_test.parent.mkdir(parents=True)
            old_test.write_text("old test", encoding="utf-8")
            relative = str(Path(".local-agents") / "tests" / old_test.name)
            self.assertIn(relative, INSTALL.plan(source, target)["legacy_kit_tests"])
            INSTALL.install(source, target, apply=True)
            self.assertEqual(old_test.read_text(encoding="utf-8"), "old test")

    def test_nested_or_same_target_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            source, _target = self.fixtures(Path(directory))
            with self.assertRaisesRegex(INSTALL.InstallError, "separate directories"):
                INSTALL.plan(source, source)
            nested = source / "nested"
            nested.mkdir()
            with self.assertRaisesRegex(INSTALL.InstallError, "separate directories"):
                INSTALL.plan(source, nested)

    def test_actual_kit_runs_from_disposable_install(self) -> None:
        source = MODULE_PATH.parents[1]
        with TemporaryDirectory() as directory:
            target = Path(directory)
            preview = INSTALL.install(source, target)
            self.assertGreater(len(preview["copy"]), 10)
            self.assertFalse((target / "AGENTS.md").exists())
            INSTALL.install(source, target, apply=True)
            self.assertTrue((target / "AGENTS.md").is_file())
            self.assertFalse((target / ".local-agents" / "config.json").exists())
            self.assertTrue((target / ".local-agents" / "tests").exists())
            self.assertTrue((target / ".local-agents" / "ruff.toml").is_file())
            self.assertFalse((target / ".agent").exists())
            (target / "pyproject.toml").write_text(
                '[tool.ruff]\nline-length = 100\ntarget-version = "py311"\n'
                '[tool.ruff.lint]\nselect = ["E", "F", "I", "UP", "B", "ASYNC", "RUF"]\n',
                encoding="utf-8",
            )
            for entrypoint in ("local-explore.py", "local-code.py", "local-review.py"):
                completed = subprocess.run(
                    [
                        sys.executable,
                        str(target / ".local-agents" / entrypoint),
                        "--help",
                    ],
                    cwd=target,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(
                    completed.returncode, 0, (entrypoint, completed.stderr)
                )
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "unittest",
                    "discover",
                    "-s",
                    ".local-agents/tests",
                    "-p",
                    "test_*.py",
                    "-q",
                ],
                cwd=target,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            self.assertEqual(
                completed.returncode, 0, completed.stdout + completed.stderr
            )
            for ruff_args in (("check", "."), ("format", "--check", ".")):
                completed = subprocess.run(
                    [sys.executable, "-m", "ruff", *ruff_args],
                    cwd=target,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )
                self.assertEqual(
                    completed.returncode, 0, completed.stdout + completed.stderr
                )


if __name__ == "__main__":
    unittest.main()
