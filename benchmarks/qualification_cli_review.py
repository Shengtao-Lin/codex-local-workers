"""Canonical high-risk review of the four exact-CLI edits, no Coder credit."""

import json
import shutil
import sys
from pathlib import Path

import qualification_matrix as MATRIX
from capability_fit import KIT, WORK, freeze, load_worker, write
from inherited_context_recovery import digest, read

BASE = WORK / "qualification-exact-cli-2"
SNAPSHOT = WORK / "qualification-exact-cli-baseline-2"
FILES = (
    "explorer-runtime.py",
    "worker-runtime.py",
    "reviewer-runtime.py",
    "local-unit.py",
)


def prepare():
    BASE.mkdir(exist_ok=False)
    freeze(SNAPSHOT.name)
    root = BASE / "workspace"
    runtime_dir = root / "src/runtime"
    runtime_dir.mkdir(parents=True, exist_ok=False)
    for source in (MATRIX.SNAPSHOT / ".local-agents").iterdir():
        if source.is_file() and source.suffix in (".py", ".json", ".toml"):
            shutil.copyfile(source, runtime_dir / source.name)
    for name in FILES:
        before = (runtime_dir / name).read_text(encoding="utf-8")
        after = (KIT / ".local-agents" / name).read_text(encoding="utf-8")
        if (
            before.replace(
                "parser = argparse.ArgumentParser()",
                "parser = argparse.ArgumentParser(allow_abbrev=False)",
            )
            != after
        ):
            raise ValueError("unexpected candidate source change: " + name)
    tests = (KIT / "tests/test_worker_cli_exact_options.py").read_text(encoding="utf-8")
    if tests.count('KIT / ".local-agents" / name') != 1:
        raise ValueError("test relocation anchor")
    (root / "tests").mkdir()
    (root / "tests/test_cli.py").write_text(
        tests.replace('KIT / ".local-agents" / name', 'KIT / "src/runtime" / name'),
        encoding="utf-8",
    )
    (root / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\npythonpath=["src"]\n[tool.ruff]\nline-length=100\n[tool.ruff.lint]\nselect=["E4","E7","E9","F"]\n',
        encoding="utf-8",
    )
    paths = ["src/runtime/" + name for name in FILES]
    config = read(SNAPSHOT / ".local-agents/config.json")
    config["python"] = sys.executable
    config["validation_profiles"] = {
        "exact-cli": {
            "python": sys.executable,
            "compile": True,
            "pytest_argv": ["-B", "-m", "pytest"],
            "commands": [
                {
                    "id": "ruff-check",
                    "argv": [
                        "{python}",
                        "-m",
                        "ruff",
                        "check",
                        *paths,
                        "tests/test_cli.py",
                    ],
                },
                {
                    "id": "ruff-format",
                    "argv": [
                        "{python}",
                        "-m",
                        "ruff",
                        "format",
                        "--check",
                        *paths,
                        "tests/test_cli.py",
                    ],
                },
            ],
        }
    }
    write(root / ".agent/config.json", config)
    packet = {
        "schema_version": 2,
        "task_id": "qualification-exact-cli-d8",
        "feature_id": "qualification-exact-cli-d8",
        "unit_id": "cli-authority",
        "run_id": "qualification-exact-cli-d8-primary-a1",
        "attempt": 1,
        "plan_revision": 1,
        "packet_revision": 1,
        "goal": "Reject abbreviated/unknown CLI options before config reads or model/worker dispatch, preserving documented full options and help. No cwd support is added.",
        "risk": {
            "feature": "high",
            "unit": "high",
            "integration": "high",
            "reasons": [
                "Worker entry authority and CLI compatibility; incorrect prefixes can reinterpret report paths and launch the wrong repository."
            ],
        },
        "dependencies": [],
        "owned_contract_ids": ["exact-cli-" + str(n) for n in range(4)],
        "scope": {
            "read": ["src", "tests"],
            "modify": paths,
            "create": [],
            "readonly": ["tests/test_cli.py"],
            "forbidden": [".agent", ".git"],
        },
        "edit_targets": [
            {
                "path": path,
                "anchor": "def main",
                "line_hint": next(
                    i
                    for i, line in enumerate(
                        (root / path).read_text(encoding="utf-8").splitlines(), 1
                    )
                    if line.startswith("def main(")
                ),
            }
            for path in paths
        ],
        "focused_tests": ["tests/test_cli.py"],
        "supplemental_tests": [],
        "required_behavior": [
            {
                "id": "exact-cli-" + str(n),
                "risk_floor": "high",
                "text": f"{name}: main uses argparse with abbreviation disabled. Invalid prefixes/unknown flags exit 2 before config or worker invocation; --help exits 0. Documented full options remain usable.",
            }
            for n, name in enumerate(FILES)
        ],
        "required_order": [],
        "forbidden_orderings": [],
        "contract_check_required": True,
        "acceptance_criteria": [
            {
                "id": "protected",
                "text": "16 protected option/help checks and configured static checks pass; no downstream call for invalid arguments.",
            }
        ],
        "acceptance_scenarios": [
            {
                "id": "invalid",
                "text": "--repo/--conf and shortened coder-report are rejected before downstream actions.",
                "observables": {"exit": 2, "worker_called": False},
            },
            {
                "id": "help",
                "text": "Full --help retains documented required option without config/model calls.",
                "observables": {"exit": 0},
            },
        ],
        "validation_profile": "exact-cli",
        "implementation_guidance": [],
        "review_feedback": [],
    }
    worker = load_worker(SNAPSHOT)
    worker.validate_packet(packet)
    write(root / ".agent/packet.json", packet)
    runtime = worker.WorkerRuntime(root, packet, config, None)
    try:
        runtime.write_lock.acquire()
        runtime._prepare_run_archive()
        for name, path in zip(FILES, paths, strict=True):
            observation = runtime.read_file({"path": path})
            runtime.safe_replace(
                {
                    "path": path,
                    "expected_sha256": observation["sha256"],
                    "find": "parser = argparse.ArgumentParser()",
                    "replace": "parser = argparse.ArgumentParser(allow_abbrev=False)",
                }
            )
        validation = runtime.validate(
            {"phase": "final", "contract_check": runtime.contract_check_template()}
        )
        if validation["status"] != "passed":
            write(BASE / "preflight-failure.json", validation)
            raise ValueError("component validation failed")
        _, report = runtime.execute(
            {
                "action": "FINISH_SUCCESS",
                "arguments": {
                    "summary": [
                        "Primary-authored exact-CLI component, synthetic archive; no Coder credit"
                    ]
                },
            }
        )
        report["synthetic_benchmark_archive"] = True
        runtime._complete_run(report)
    finally:
        runtime.close()
    write(
        root / ".agent/review-request.json",
        {
            "schema_version": 1,
            "task_id": packet["task_id"],
            "unit_id": packet["unit_id"],
            "run_id": packet["run_id"],
            "review_id": "independent-1",
        },
    )
    write(
        BASE / "manifest.json",
        {
            "runtime": str(SNAPSHOT),
            "root": str(root),
            "driver_sha256": digest(Path(__file__)),
            "protected_test_source_sha256": digest(
                KIT / "tests/test_worker_cli_exact_options.py"
            ),
            "scope_changed": False,
            "model_changed": False,
            "synthetic_coder_credit": False,
            "criterion": "High-risk independent source-backed Reviewer and full Primary review; no semantic capability credit",
        },
    )
    print("prepared and validated synthetic CLI component", flush=True)


def review():
    manifest = read(BASE / "manifest.json")
    if digest(Path(__file__)) != manifest["driver_sha256"]:
        raise ValueError("driver drift")
    root = Path(manifest["root"])
    MATRIX.SCOPE.invoke(
        root,
        "reviewer",
        [
            sys.executable,
            str(SNAPSHOT / ".local-agents/local-review.py"),
            "--request",
            str(root / ".agent/review-request.json"),
            "--config",
            str(root / ".agent/config.json"),
            "--report",
            str(root / ".agent/reviewer.json"),
        ],
    )
    print(json.dumps(read(root / ".agent/reviewer.json")))


if __name__ == "__main__":
    if sys.argv[1] == "prepare":
        prepare()
    elif sys.argv[1] == "review":
        review()
    else:
        raise ValueError("unknown action")
