"""Independent synthetic component review for opt-in post-edit field guidance."""

import difflib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import qualification_output_review as previous
from capability_fit import KIT, WORK, freeze, load_worker, write
from inherited_context_recovery import digest, read

BASE = WORK / "qualification-validation-hint-2"
SNAPSHOT = WORK / "qualification-validation-hint-baseline-2"
BEFORE = WORK / "qualification-matrix-baseline-5"
SOURCE = "src/runtime/worker-runtime.py"
TEST = "tests/test_coder_post_edit_validation_hint.py"


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
        KIT / ".local-agents/tests/test_worker_runtime.py",
        target / "tests/test_worker_runtime.py",
    )
    (root / "tests").mkdir()
    text = (KIT / TEST).read_text(encoding="utf-8")
    anchor = ' / ".local-agents/worker-runtime.py"'
    assert text.count(anchor) == 1
    (root / TEST).write_text(
        text.replace(anchor, ' / "src/runtime/worker-runtime.py"'), encoding="utf-8"
    )
    shutil.copyfile(previous.BASE / "workspace/pyproject.toml", root / "pyproject.toml")
    subprocess.run([sys.executable, "-m", "ruff", "format", TEST], cwd=root, check=True)
    config = read(previous.BASE / "workspace/.agent/config.json")
    for command in config["validation_profiles"]["output-recovery"]["commands"]:
        command["argv"][-3:] = [
            SOURCE,
            "src/runtime/tests/test_worker_runtime.py",
            TEST,
        ]
    write(root / ".agent/config.json", config)
    packet = read(previous.BASE / "workspace/.agent/packet.json")
    packet.update(
        task_id="qualification-validation-hint-d12-v2",
        feature_id="qualification-validation-hint-d12-v2",
        unit_id="validation-hint",
        run_id="qualification-validation-hint-d12-v2-primary-a1",
        goal="Successful edit returns optional unknown packet-specific validation field shape; never confirms or runs validation automatically.",
        scope={
            "read": ["src", "tests"],
            "modify": [SOURCE],
            "create": [],
            "readonly": [TEST, "src/runtime/tests/test_worker_runtime.py"],
            "forbidden": [".agent", ".git"],
        },
        edit_targets=[{"path": SOURCE, "anchor": "def _record_edit"}],
        focused_tests=[TEST],
    )
    obligations = [
        (
            "opt-in",
            "Strict boolean default false; optional-contract packets retain old edit response and validation behavior.",
        ),
        (
            "shape",
            "Only successful edit with required contract exposes current required behavior and observable scenario IDs. Ordering confirmations are null, never automatically true.",
        ),
        (
            "authority",
            "Field hint never calls validate or records last_contract_check; existing checks reject missing contract, unknown ordering for final submission and stale/missing test evidence.",
        ),
        (
            "scope",
            "No edits, budgets, action permissions or terminal gate expanded. Subsequent authorized edits remain available; failed edits never gain a success hint.",
        ),
    ]
    packet["owned_contract_ids"] = [key for key, _ in obligations]
    packet["required_behavior"] = [
        {"id": key, "text": text, "risk_floor": "high"} for key, text in obligations
    ]
    packet["acceptance_scenarios"] = [
        {"id": "hint", "text": "Unknown fields and current IDs after successful edit"},
        {
            "id": "reject",
            "text": "Missing contract/unknown required ordering still rejected; default and failed edits unchanged",
        },
    ]
    worker = load_worker(SNAPSHOT)
    worker.validate_packet(packet)
    write(root / ".agent/packet.json", packet)
    runtime = worker.WorkerRuntime(root, packet, config, None)
    before = (root / SOURCE).read_text(encoding="utf-8")
    after = (KIT / ".local-agents/worker-runtime.py").read_text(encoding="utf-8")
    old, new = before.splitlines(keepends=True), after.splitlines(keepends=True)
    groups = list(
        difflib.SequenceMatcher(a=old, b=new, autojunk=False).get_grouped_opcodes(n=2)
    )
    assert groups
    try:
        runtime.write_lock.acquire()
        runtime._prepare_run_archive()
        for group in reversed(groups):
            start, end, new_start, new_end = (
                group[0][1],
                group[-1][2],
                group[0][3],
                group[-1][4],
            )
            find = "".join(old[start:end])
            assert before.count(find) == 1
            observed = runtime.read_file(
                {"path": SOURCE, "start_line": start + 1, "end_line": end}
            )
            runtime.safe_replace(
                {
                    "path": SOURCE,
                    "expected_sha256": observed["sha256"],
                    "find": find,
                    "replace": "".join(new[new_start:new_end]),
                }
            )
        assert (root / SOURCE).read_text(encoding="utf-8") == after
        validation = runtime.validate(
            {"phase": "final", "contract_check": runtime.contract_check_template()}
        )
        if validation["status"] != "passed":
            write(BASE / "preflight-failure.json", validation)
            raise ValueError("component preflight failed")
        _, report = runtime.execute(
            {
                "action": "FINISH_SUCCESS",
                "arguments": {
                    "summary": [
                        "Primary-authored synthetic component, zero Coder credit"
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
            "qualification_credit": False,
        },
    )
    print("Prepared post-edit validation hint component with protected tests")


def review():
    manifest = read(BASE / "manifest.json")
    assert digest(Path(__file__)) == manifest["driver_sha256"]
    root = Path(manifest["root"])
    previous.matrix.SCOPE.invoke(
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
