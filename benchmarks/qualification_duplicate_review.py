"""Independent high-risk review for optional duplicate-action final-report gate."""

import difflib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import qualification_output_review as previous
from capability_fit import KIT, WORK, freeze, load_worker, write
from inherited_context_recovery import digest, read

BASE = WORK / "qualification-duplicate-recovery-1"
SNAPSHOT = WORK / "qualification-duplicate-recovery-baseline-1"
SOURCE, TESTS = previous.SOURCE, previous.TESTS


def prepare():
    BASE.mkdir(exist_ok=False)
    freeze(SNAPSHOT.name)
    root = BASE / "workspace"
    target = root / "src/runtime"
    target.mkdir(parents=True)
    for file in (previous.SNAPSHOT / ".local-agents").iterdir():
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
    shutil.copyfile(previous.BASE / "workspace/pyproject.toml", root / "pyproject.toml")
    subprocess.run(
        [sys.executable, "-m", "ruff", "format", TESTS[1]], cwd=root, check=True
    )
    config = read(previous.BASE / "workspace/.agent/config.json")
    write(root / ".agent/config.json", config)
    packet = read(previous.BASE / "workspace/.agent/packet.json")
    packet.update(
        task_id="qualification-duplicate-recovery-d11",
        feature_id="qualification-duplicate-recovery-d11",
        unit_id="duplicate-report",
        run_id="qualification-duplicate-recovery-d11-primary-a1",
        goal="Optional one-shot report-only convergence after duplicate read/search with sufficient source/test evidence; no invented success or extra budget.",
    )
    obligations = [
        (
            "opt-in",
            "New duplicate-action recovery defaults false and strictly validates booleans. Existing output-limit behavior and investigate mode are unchanged.",
        ),
        (
            "eligible",
            "Only locate duplicate READ_FILE/SEARCH rejection, with source and test already read and every configured citation path read, a remaining existing model turn and protocol budget, may trigger this recovery. No extra read/search/turn/output/deadline budget.",
        ),
        (
            "shared",
            "Shares the existing finish_repair_used one-shot with malformed-output and output-limit recovery; a later output truncation cannot start another recovery. Never synthesize an accepted report or execute duplicate action again.",
        ),
        (
            "evidence",
            "Native tools become FINISH_SUCCESS only; guard rejects other actions before dispatch. Existing current-source/hash/read/assertion/citation gates remain, invalid final fails closed. Replays only already observed source, never model reasoning.",
        ),
    ]
    packet["owned_contract_ids"] = [key for key, _ in obligations]
    packet["required_behavior"] = [
        {"id": key, "text": text, "risk_floor": "high"} for key, text in obligations
    ]
    packet["edit_targets"] = [{"path": SOURCE, "anchor": "repeated_output"}]
    packet["acceptance_scenarios"] = [
        {
            "id": "duplicate",
            "text": "Valid final citations after rejected duplicate may succeed.",
        },
        {
            "id": "reject",
            "text": "Absent paths/default opt-in, unread citations, read actions and second recovery fail closed.",
        },
    ]
    worker = load_worker(SNAPSHOT)
    worker.validate_packet(packet)
    write(root / ".agent/packet.json", packet)
    runtime = worker.WorkerRuntime(root, packet, config, None)
    before = (root / SOURCE).read_text(encoding="utf-8")
    after = (KIT / ".local-agents/explorer-runtime.py").read_text(encoding="utf-8")
    old, new = before.splitlines(keepends=True), after.splitlines(keepends=True)
    groups = list(
        difflib.SequenceMatcher(a=old, b=new, autojunk=False).get_grouped_opcodes(n=2)
    )
    assert groups
    try:
        runtime.write_lock.acquire()
        runtime._prepare_run_archive()
        for group in reversed(groups):
            start, end = group[0][1], group[-1][2]
            new_start, new_end = group[0][3], group[-1][4]
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
                        "Primary-authored component, synthetic archive, zero Coder credit"
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
            "production_source_sha256": digest(
                KIT / ".local-agents/explorer-runtime.py"
            ),
            "qualification_credit": False,
        },
    )
    print("Prepared and deterministically validated duplicate-action gate component")


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
