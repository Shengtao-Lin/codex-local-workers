"""Two focused read-only investigations through the actual Explorer runtime."""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

import bounded_evidence_support as S
import project_caller_trial as J

BATCH = S.KIT / "benchmarks/work/harness-convergence/strata-explorer-20261023-1"
ENTRY = Path(__file__).resolve()
TASKS = {
    "trace": "How does a supplied message ID reach CanonicalSample output through GenericOtelAdapter? Trace actual calls starting at src/evaluation_harness/adapters/generic_otel.py and common.py; cite read source lines and one actual test you read. One focused investigation, no changes.",
    "hash": "Does the submit_job payload hash path call stable_message_id? Locate its actual hashing helper and dependencies using src/evaluation_harness/jobs/queue.py and canonical/fingerprint.py. Reconcile positive calls with scoped absence claims; cite actual read lines. No changes.",
}


def prepare(used):
    assert used < 40 and not BATCH.exists()
    seed = (
        S.KIT
        / "benchmarks/work/harness-convergence/strata-project-20261023-2/cells/hash-1/isolated"
    )
    rows = {}
    for name, task in TASKS.items():
        root = BATCH / name / "isolated"
        J.copy_project(J.TASKS.SNAPSHOT, root)
        shutil.copytree(seed / ".local-agents", root / ".local-agents")
        config = S.read(seed / ".agent/config.json")
        config.update(
            explorer_context_length=65536,
            explorer_reasoning_effort="medium",
            explorer_temperature=1.0,
            explorer_max_tokens=12288,
            explorer_required_tool_max_tokens=12288,
        )
        S.save(root / ".agent/config.json", config)
        (root / ".agent/strata-wire").mkdir()
        rows[name] = {
            "root": str(root),
            "task": task,
            "task_id": BATCH.name + "-" + name,
            "source_hashes": {
                p.relative_to(root).as_posix(): S.sha(p)
                for p in root.rglob("*")
                if p.is_file()
            },
            "expected": "Primary independently checks cited files/quotes, call path and test existence",
        }
    S.save(
        BATCH / "registration.json",
        {
            "registered": 2,
            "order": list(TASKS),
            "rows": rows,
            "model": "Same resident IQ3_S, medium thinking/4096 allowance, max12288 output,64K client, temperature1; Explorer retains its existing native-tools wire and remaining sampling defaults",
            "budget": "Existing16 turns/8 reads/10 searches/6 protocol errors/600s invocation; single resident; no Coder or edits",
            "gate": "2/2 focused evidence-backed reports, actual source/test references, no unsupported whole-repo absence, Primary verification",
            "continue": "Ordinary failure finish remaining independent cell; infrastructure/residency/safety/usage stops; no replay or query narrowing in this batch",
            "qualification": "Two exposed-domain navigation probes, not general Explorer release or Coordinator qualification",
            "weekly_used": used,
            "weekly_stop": 40,
            "pins": {
                str(p): S.sha(p)
                for p in (
                    ENTRY,
                    Path(__file__).with_name("strata_entry.py"),
                    Path(__file__).with_name("strata_model_entry.py"),
                )
            },
        },
    )
    print("Two read-only Explorer investigations registered")


def worker(args):
    config = S.read(Path.cwd() / ".agent/config.json")
    sys.path.insert(0, str(Path.cwd() / ".local-agents"))
    from bounded import capture_fixture_support as F
    from strata_model_entry import patch

    module = F.load(
        Path.cwd() / ".local-agents/explorer-runtime.py", "strata_explorer_runtime"
    )
    patch(module, config)
    reg = S.read(BATCH / "registration.json")
    row = reg["rows"][args.cell]
    sys.argv = [
        str(module.__file__),
        "--task",
        row["task"],
        "--task-id",
        row["task_id"],
        "--config",
        str(Path.cwd() / ".agent/config.json"),
        "--report",
        str(Path.cwd() / ".agent/explorer-report.json"),
        "--full-report",
    ]
    return module.main()


def run(cell, used):
    assert used < 40
    reg = S.read(BATCH / "registration.json")
    assert all(S.sha(p) == h for p, h in reg["pins"].items())
    row = reg["rows"][cell]
    root = Path(row["root"])
    assert all(S.sha(root / p) == h for p, h in row["source_hashes"].items())
    result = J.T.run(
        [S.PYTHON, "-B", ENTRY, "worker", "--cell", cell, "--weekly-used", str(used)],
        root,
        timeout=720,
    )
    S.save(BATCH / cell / "process.json", result)
    drift = [p for p, h in row["source_hashes"].items() if S.sha(root / p) != h]
    S.save(BATCH / cell / "protected-check.json", {"drift": drift})
    print(
        json.dumps({"cell": cell, "exit_code": result["exit_code"], "drift": drift}),
        flush=True,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["prepare", "run", "worker"])
    p.add_argument("--cell", choices=TASKS)
    p.add_argument("--weekly-used", type=int, required=True)
    a = p.parse_args()
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    if a.mode == "prepare":
        prepare(a.weekly_used)
    elif a.mode == "worker":
        raise SystemExit(worker(a))
    else:
        run(a.cell, a.weekly_used)
