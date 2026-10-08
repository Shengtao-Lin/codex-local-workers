"""Independent high-risk review of Explorer cache evidence-contract identity."""

import json
import shutil
import sys
from pathlib import Path

import qualification_matrix as MATRIX
from capability_fit import KIT, WORK, freeze, load_worker, write
from inherited_context_recovery import digest, read

BASE = WORK / "qualification-cache-contract-1"
SNAPSHOT = WORK / "qualification-cache-contract-baseline-1"
BEFORE = WORK / "qualification-exact-cli-baseline-2"


def prepare():
    BASE.mkdir(exist_ok=False)
    freeze(SNAPSHOT.name)
    root = BASE / "workspace"
    target = root / "src/runtime"
    target.mkdir(parents=True, exist_ok=False)
    for source in (BEFORE / ".local-agents").iterdir():
        if source.is_file() and source.suffix in (".py", ".json", ".toml"):
            shutil.copyfile(source, target / source.name)
    tests = target / "tests"
    tests.mkdir()
    shutil.copyfile(
        KIT / ".local-agents/tests/test_explorer_runtime.py",
        tests / "test_explorer_runtime.py",
    )
    (root / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\npythonpath=["src"]\n[tool.ruff]\nline-length=100\n[tool.ruff.lint]\nselect=["E4","E7","E9","F"]\n',
        encoding="utf-8",
    )
    source_path = "src/runtime/explorer-runtime.py"
    test_path = "src/runtime/tests/test_explorer_runtime.py"
    config = read(SNAPSHOT / ".local-agents/config.json")
    config["python"] = sys.executable
    config["validation_profiles"] = {
        "cache-contract": {
            "python": sys.executable,
            "compile": True,
            "pytest_argv": ["-B", "-m", "pytest"],
            "commands": [
                {
                    "id": "ruff-check",
                    "argv": ["{python}", "-m", "ruff", "check", source_path, test_path],
                },
                {
                    "id": "ruff-format",
                    "argv": [
                        "{python}",
                        "-m",
                        "ruff",
                        "format",
                        "--check",
                        source_path,
                        test_path,
                    ],
                },
            ],
        }
    }
    write(root / ".agent/config.json", config)
    packet = {
        "schema_version": 2,
        "task_id": "qualification-cache-contract-d9",
        "feature_id": "qualification-cache-contract-d9",
        "unit_id": "cache-proof",
        "run_id": "qualification-cache-contract-d9-primary-a1",
        "attempt": 1,
        "plan_revision": 1,
        "packet_revision": 1,
        "goal": "Prevent a cached Explorer success from bypassing newly required source citations, TRACE or regex SEARCH. Preserve old history, valid unchanged-contract cache hits and read-only permissions.",
        "risk": {
            "feature": "high",
            "unit": "high",
            "integration": "high",
            "reasons": [
                "Cached evidence is an authority boundary; changed obligations must not obtain stale success."
            ],
        },
        "dependencies": [],
        "owned_contract_ids": ["current-evidence-contract"],
        "scope": {
            "read": ["src"],
            "modify": [source_path],
            "create": [],
            "readonly": [test_path],
            "forbidden": [".agent", ".git"],
        },
        "edit_targets": [
            {"path": source_path, "anchor": "self.cache_task", "line_hint": 705}
        ],
        "focused_tests": [test_path],
        "supplemental_tests": [],
        "required_behavior": [
            {
                "id": "current-evidence-contract",
                "risk_floor": "high",
                "text": "Cache identity includes mode, task, required citation paths, required TRACE symbol and required regex SEARCH. Same unchanged contract still reuses exact cached success. Each changed obligation must miss old success and run a new investigation. Old entries remain intact under previous namespace. No permission, evidence, protocol-error, read/search, citation or model budget relaxation.",
            }
        ],
        "required_order": [],
        "forbidden_orderings": [],
        "contract_check_required": True,
        "acceptance_criteria": [
            {
                "id": "protected",
                "text": "Full protected Explorer tests and static checks pass; three real weak-cache/strong-contract counterexamples no longer hit stale success.",
            }
        ],
        "acceptance_scenarios": [
            {
                "id": "changed",
                "text": "Adding required citation path, TRACE or regex requirement misses old success; no new success is granted from failure.",
                "observables": {"old_success_reused": False},
            },
            {
                "id": "unchanged",
                "text": "Identical evidence contract retains cache hit and old entries are not deleted.",
                "observables": {
                    "same_contract_hit": True,
                    "old_history_retained": True,
                },
            },
        ],
        "validation_profile": "cache-contract",
        "implementation_guidance": [],
        "review_feedback": [],
    }
    worker = load_worker(SNAPSHOT)
    worker.validate_packet(packet)
    write(root / ".agent/packet.json", packet)
    runtime = worker.WorkerRuntime(root, packet, config, None)
    before = (root / source_path).read_text(encoding="utf-8")
    after = (KIT / ".local-agents/explorer-runtime.py").read_text(encoding="utf-8")
    start = before.index("        # Reports produced before final-channel enforcement")
    end = before.index('        if self.mode == "locate"', start)
    after_start = after.index("        # Cached research must satisfy")
    after_end = after.index('        if self.mode == "locate"', after_start)
    if before[:start] + after[after_start:after_end] + before[end:] != after:
        raise ValueError("candidate contains unrelated source changes")
    try:
        runtime.write_lock.acquire()
        runtime._prepare_run_archive()
        observation = runtime.read_file(
            {"path": source_path, "start_line": 690, "end_line": 735}
        )
        runtime.safe_replace(
            {
                "path": source_path,
                "expected_sha256": observation["sha256"],
                "find": before[start:end],
                "replace": after[after_start:after_end],
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
                        "Primary-authored cache-contract component; synthetic archive, zero Coder credit"
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
            "candidate_source_sha256": digest(
                KIT / ".local-agents/explorer-runtime.py"
            ),
            "protected_test_sha256": digest(
                KIT / ".local-agents/tests/test_explorer_runtime.py"
            ),
            "criterion": "High-risk independent Reviewer and Primary source/diff/full-regression acceptance; no capability credit",
        },
    )
    print("prepared and validated cache-contract component", flush=True)


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
