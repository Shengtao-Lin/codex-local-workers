"""Real subprocess controls for the optional Primary import diagnostic."""

import json
import os
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools/check_python_import.py"


def run_tool(
    project: Path, env: dict[str, str], *extra: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-B",
            str(TOOL),
            "--python",
            sys.executable,
            "--project",
            str(project),
            "--module",
            "demo_package",
            *extra,
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_wrong_editable_path_fails_and_explicit_project_source_wins(
    tmp_path: Path,
) -> None:
    project, sibling = tmp_path / "project", tmp_path / "sibling"
    for root in (project / "src", sibling):
        (root / "demo_package").mkdir(parents=True)
        (root / "demo_package/__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": str(sibling)}
    wrong = run_tool(project, env)
    assert wrong.returncode == 1
    assert json.loads(wrong.stdout)["status"] == "outside_project"
    correct = run_tool(project, env, "--source-root", "src")
    assert correct.returncode == 0
    assert Path(json.loads(correct.stdout)["origin"]).is_relative_to(project)


def test_rejects_source_root_outside_project(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    result = run_tool(project, dict(os.environ), "--source-root", "..")
    assert result.returncode == 2
    assert "not inside project" in json.loads(result.stdout)["reason"]


def test_missing_module_fails_closed(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    result = run_tool(project, {**os.environ, "PYTHONPATH": str(project)})
    assert result.returncode == 2
    assert json.loads(result.stdout)["reason"] == "import failed"


def test_namespace_without_single_file_does_not_claim_binding(tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / "src/demo_package").mkdir(parents=True)
    result = run_tool(project, dict(os.environ), "--source-root", "src")
    assert result.returncode == 2
    assert json.loads(result.stdout)["reason"] == "module origin unavailable"
