"""Independent synthetic review of opt-in bounded output-limit report recovery."""

import difflib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import qualification_matrix as matrix
from capability_fit import KIT, WORK, freeze, load_worker, write
from inherited_context_recovery import digest, read

BASE = WORK / "qualification-output-recovery-6"
SNAPSHOT = WORK / "qualification-output-recovery-baseline-6"
BEFORE = WORK / "qualification-matrix-baseline-3"
SOURCE = "src/runtime/explorer-runtime.py"
TESTS = [
    "src/runtime/tests/test_explorer_runtime.py",
    "tests/test_explorer_output_recovery.py",
]


def prepare():
    BASE.mkdir(exist_ok=False)
    freeze(SNAPSHOT.name)
    root = BASE / "workspace"
    target = root / "src/runtime"
    target.mkdir(parents=True)
    for file in (BEFORE / ".local-agents").iterdir():
        if file.is_file() and file.suffix in (".py", ".json", ".toml"):
            shutil.copyfile(file, target / file.name)
    (target / "tests").mkdir()
    shutil.copyfile(
        KIT / ".local-agents/tests/test_explorer_runtime.py", root / TESTS[0]
    )
    (root / "tests").mkdir()
    test = (KIT / TESTS[1]).read_text(encoding="utf-8")
    anchor = ' / ".local-agents/explorer-runtime.py"'
    assert test.count(anchor) == 1
    (root / TESTS[1]).write_text(
        test.replace(anchor, ' / "src/runtime/explorer-runtime.py"'), encoding="utf-8"
    )
    (root / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\npythonpath=["src"]\n[tool.ruff]\nline-length=100\n[tool.ruff.lint]\nselect=["E4","E7","E9","F"]\n',
        encoding="utf-8",
    )
    # Normalize only the relocated copy before it becomes protected evidence.
    subprocess.run(
        [sys.executable, "-m", "ruff", "format", TESTS[1]], cwd=root, check=True
    )
    config = read(SNAPSHOT / ".local-agents/config.json")
    config["python"] = sys.executable
    config["validation_profiles"] = {
        "output-recovery": {
            "python": sys.executable,
            "compile": True,
            "pytest_argv": ["-B", "-m", "pytest", "--basetemp=validation-temp"],
            "commands": [
                {
                    "id": "ruff-" + action,
                    "argv": [
                        "{python}",
                        "-m",
                        "ruff",
                        action,
                        *(["--check"] if action == "format" else []),
                        SOURCE,
                        *TESTS,
                    ],
                }
                for action in ("check", "format")
            ],
        }
    }
    write(root / ".agent/config.json", config)
    obligations = [
        (
            "opt-in",
            "Default false and strict boolean configuration; no recovery for investigate mode or non-output-limit infrastructure errors.",
        ),
        (
            "bounded",
            "Recovery requires read source AND test, every configured required citation path read, unused shared one-shot report recovery, and a remaining existing model turn. No budget or deadline increase.",
        ),
        (
            "discard",
            "Never execute, parse, retain or echo the truncated reply as an action. Record request diagnostics and recovery event without raw source/model text in event metadata.",
        ),
        (
            "report-only",
            "On recovery only FINISH_SUCCESS is allowed before dispatch. Native tools temporarily restricted then restored; ordinary source-read, hash, citation and assertion requirements still apply. Repeat truncation or invalid report fails closed, never synthetic success.",
        ),
    ]
    packet = {
        "schema_version": 2,
        "task_id": "qualification-output-recovery-d10-focused",
        "feature_id": "qualification-output-recovery-d10-focused",
        "unit_id": "report-recovery",
        "run_id": "qualification-output-recovery-d10-focused-primary-a1",
        "attempt": 1,
        "plan_revision": 1,
        "packet_revision": 1,
        "goal": "Optional one-shot, report-only recovery after output-token truncation, without accepting any partial action or relaxing evidence.",
        "risk": {
            "feature": "high",
            "unit": "high",
            "integration": "high",
            "reasons": ["Model action channel and source evidence authority."],
        },
        "dependencies": [],
        "owned_contract_ids": [key for key, _ in obligations],
        "scope": {
            "read": ["src", "tests"],
            "modify": [SOURCE],
            "create": [],
            "readonly": TESTS,
            "forbidden": [".agent", ".git"],
        },
        "edit_targets": [
            {"path": SOURCE, "anchor": "except ExplorerModelRequestError"}
        ],
        "focused_tests": [TESTS[1]],
        "supplemental_tests": [],
        "required_behavior": [
            {"id": key, "text": text, "risk_floor": "high"} for key, text in obligations
        ],
        "required_order": [],
        "forbidden_orderings": [],
        "contract_check_required": True,
        "acceptance_criteria": [
            {
                "id": "protected",
                "text": "All recovery tests plus Ruff pass; Primary also runs the full Explorer suite and kit regression independently. Other protected tests remain readable and immutable.",
            }
        ],
        "acceptance_scenarios": [
            {
                "id": "success",
                "text": "Valid citations after discarded response may succeed.",
            },
            {
                "id": "reject",
                "text": "Read action, unread citation, repeated truncation, missing evidence or remaining budget never pass.",
            },
        ],
        "validation_profile": "output-recovery",
        "implementation_guidance": [],
        "review_feedback": [],
    }
    worker = load_worker(SNAPSHOT)
    worker.validate_packet(packet)
    write(root / ".agent/packet.json", packet)
    runtime = worker.WorkerRuntime(root, packet, config, None)
    before = (root / SOURCE).read_text(encoding="utf-8")
    after = (KIT / ".local-agents/explorer-runtime.py").read_text(encoding="utf-8")
    old_lines, new_lines = (
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
    )
    edits = [
        opcode
        for opcode in difflib.SequenceMatcher(
            a=old_lines, b=new_lines, autojunk=False
        ).get_opcodes()
        if opcode[0] != "equal"
    ]
    assert len(edits) == 2 and all(code == "insert" for code, *_ in edits)
    try:
        runtime.write_lock.acquire()
        runtime._prepare_run_archive()
        for _, start, end, new_start, new_end in reversed(edits):
            assert start == end and start > 0
            observed = runtime.read_file(
                {"path": SOURCE, "start_line": max(1, start - 7), "end_line": start}
            )
            anchor_line = "".join(old_lines[max(0, start - 8) : start])
            assert before.count(anchor_line) == 1
            runtime.safe_replace(
                {
                    "path": SOURCE,
                    "expected_sha256": observed["sha256"],
                    "find": anchor_line,
                    "replace": anchor_line + "".join(new_lines[new_start:new_end]),
                }
            )
        assert (root / SOURCE).read_text(encoding="utf-8") == after
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
                        "Primary-authored candidate; synthetic archive, zero Coder credit"
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
            **{key: packet[key] for key in ("task_id", "unit_id", "run_id")},
            "review_id": "independent-1",
        },
    )
    write(
        BASE / "manifest.json",
        {
            "root": str(root),
            "driver_sha256": digest(Path(__file__)),
            "source_sha256": digest(KIT / ".local-agents/explorer-runtime.py"),
            "qualification_credit": False,
        },
    )
    print("Prepared and validated optional recovery component")


def review():
    manifest = read(BASE / "manifest.json")
    assert digest(Path(__file__)) == manifest["driver_sha256"]
    root = Path(manifest["root"])
    matrix.SCOPE.invoke(
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
    {"prepare": prepare, "review": review}[sys.argv[1]]()
