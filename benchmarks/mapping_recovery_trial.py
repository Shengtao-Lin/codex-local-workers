"""Can the fixed Coder loop repair a newly exposed real semantic counterexample?"""

import argparse
import json
import os
import shutil
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import evidence_loop_trial as E
import normal_task_trial as N
import supervised_repair_phase as P

BATCH = S.KIT / "benchmarks/work/harness-convergence/mapping-recovery-20261020-1"
ORDER = ["for-1", "all-1", "all-2", "for-2"]
COUNTEREXAMPLE = """

class FalseMap(dict):
    def __bool__(self):
        return False

def test_all_mapping_keys_even_when_mapping_is_false():
    data = FalseMap({1: "value"})
    before = dict(data)
    with pytest.raises(TypeError, match="Provider event keys must be strings"):
        mapping(data, "event")
    assert dict(data) == before
"""


def command(root, mode="coder", replay=None):
    argv = P.command(root, mode, replay) + ["--static-focus"]
    if mode == "coder":
        argv[argv.index("--report") + 1] = str(root / ".agent/unit-report.json")
        argv += ["--summary", str(root / ".agent/unit-summary.json")]
    return argv


def prepare():
    old_rows = S.read(E.BATCH / "cells.json")
    old_results = S.read(E.BATCH / "posthoc-primary-mapping.json")["cells"]
    if not (E.BATCH / "decision.json").exists():
        raise ValueError("Previous batch must close")
    rows = {}
    for cell in ORDER:
        old_cell = "mapping-A-1" if cell.startswith("for") else "mapping-A-2"
        old = old_rows[old_cell]
        old_root = Path(old["root"])
        source_hash = old_results[old_cell]["source_sha256"]
        if (
            old_results[old_cell]["correct_rejection"]
            or S.sha(old_root / old["target"]) != source_hash
        ):
            raise ValueError("Frozen failing starter not intact")
        root = BATCH / "cells" / cell / "isolated"
        root.mkdir(parents=True, exist_ok=False)
        for name, digest in old["files"].items():
            origin = old_root / name
            if S.sha(origin) != (source_hash if name == old["target"] else digest):
                raise ValueError("Inherited input changed")
            dest = root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(origin, dest)
        test_path = root / "tests/test_contract.py"
        test_path.write_text(
            test_path.read_text(encoding="utf-8") + COUNTEREXAMPLE, encoding="utf-8"
        )
        result = T.run([S.PYTHON, "-B", "-m", "ruff", "format", "tests"], root)
        if result["exit_code"]:
            raise ValueError("Protected test formatting failed")
        identity = {
            k: BATCH.name + "-" + cell for k in ("task_id", "unit_id", "run_id")
        }
        packet = S.read(root / ".agent/packet.json")
        packet.update(identity)
        # Original hard contract unchanged. No suggested implementation or new semantics.
        policy = S.read(root / "acceptance/capture-policy.json")
        policy["identity"] = identity
        policy["readonly_hashes"]["tests/test_contract.py"] = S.sha(test_path)
        config = S.read(root / ".agent/config.json")
        for path, value in (
            (root / ".agent/packet.json", packet),
            (root / "acceptance/capture-policy.json", policy),
        ):
            path.write_text(json.dumps(value, indent=2), encoding="utf-8")
        config["experimental_capture_policy_sha256"] = S.sha(
            root / "acceptance/capture-policy.json"
        )
        (root / ".agent/config.json").write_text(
            json.dumps(config, indent=2), encoding="utf-8"
        )
        if cell.endswith("-1"):
            baseline = T.run(
                [S.PYTHON, "-B", "-m", "pytest", "-q", "tests", old["private_tests"]],
                root,
            )
            S.save(BATCH / "baseline" / (cell + ".json"), baseline)
            if (
                baseline["exit_code"] != 1
                or "test_all_mapping_keys_even_when_mapping_is_false"
                not in baseline["stdout"]
            ):
                raise ValueError("New counterexample must reject each actual starter")
            control = BATCH / "offline" / cell / "isolated"
            shutil.copytree(
                root,
                control,
                ignore=shutil.ignore_patterns(
                    ".ruff_cache", ".pytest_cache", "__pycache__"
                ),
            )
            replay = control.parent / "replay.json"
            reference = T.extract(
                E.BATCH / "reference-checks/mapping/src/product/code.py", "mapping"
            )
            S.save(replay, [{"replacement": reference}])
            proof = T.run(command(control, "unit", replay), control, timeout=180)
            S.save(control.parent / "process.json", proof)
            if proof["exit_code"]:
                raise ValueError("Same-contract reference/full-chain replay failed")
        rows[cell] = {
            **old,
            "root": str(root),
            "identity": identity,
            "starter_origin": old_cell,
            "starter_sha256": source_hash,
            "files": {p: S.sha(root / p) for p in old["files"]},
        }
    S.save(BATCH / "cells.json", rows)
    pins = {
        name: S.sha(name) for name in S.read(E.BATCH / "candidate-freeze.json")["pins"]
    }
    for path in (Path(__file__), BATCH / "cells.json"):
        pins[str(path.resolve())] = S.sha(path)
    S.save(
        BATCH / "registration.json",
        {
            "order": ORDER,
            "registered": 4,
            "pins": pins,
            "weekly_stop": 50,
            "batch_seconds": 7200,
            "candidate": "Unchanged no-memory/no-evidence-loop static-focused host repair. No model or permission changes.",
            "task": "Two frozen actually failing Mapping drafts, each twice. Add only original-contract FalseMap counterexample as protected public test; preserve original private tests and semantics.",
            "budget": {
                "requests": 12,
                "edits": 3,
                "post_edit_checks": 3,
                "initial_checks": 1,
                "seconds": 900,
            },
            "gate": "4/4 actual edits followed by complete current checks, independent fixed public/private checks and Primary source inspection; Coder recovery only, no Reviewer/product qualification.",
            "continue_rule": "Complete ordinary failures. Stop infra/safety/drift/deadline/weekly50; no resampling, task-specific Primary repair hints or expanding scope.",
            "cost": "One-time counterexample preparation separate from per-task execution. No Primary implementation during live; time/cloud tokens unknown.",
        },
    )
    print(
        "Four same-contract semantic recovery cells frozen after two negative/reference controls"
    )


def run(cell, used, observed):
    os.environ["PYTHONIOENCODING"] = "utf-8"
    N.run(
        cell,
        used,
        observed,
        batch=BATCH,
        order=ORDER,
        build_command=command,
        usage_limit=50,
        batch_seconds=7200,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["prepare"])
    p.parse_args()
    prepare()
