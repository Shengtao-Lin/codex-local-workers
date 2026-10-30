"""Frozen feedback-presentation repeat, only after the preceding batch closes."""

import argparse
import shutil
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import function_repeat_trial as F

OLD = S.KIT / "benchmarks/work/harness-convergence/supervised-release-20261019-4"
BATCH = S.KIT / "benchmarks/work/harness-convergence/supervised-feedback-20261019-1"
ORDER = ["json-1", "json-2", "ids-1", "raw-1", "raw-2", "ids-2"]


def command(root, mode="unit", replay=None):
    return F.command(root, mode, replay) + ["--literal-check-feedback"]


def checkpoint():
    old = S.read(OLD / "registration.json")
    if not all(
        (OLD / "live-results" / cell / "result.json").exists() for cell in old["order"]
    ):
        raise ValueError("Previous fixed batch must finish before controller changes")
    for name in (
        "consolidated_harness.py",
        "consolidated_entry.py",
        "supervised_tasks.py",
    ):
        source = S.KIT / "benchmarks" / name
        if S.sha(source) != old["pins"][str(source)]:
            raise ValueError("Candidate drift before new checkpoint")
        dest = BATCH / "candidate-preimages" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("xb") as stream:
            stream.write(source.read_bytes())
    print("Prior controller/entry/task driver preserved")


def prepare(
    batch=BATCH,
    build_command=command,
    snapshot_dir=None,
    candidate_description="Only failed check output presentation becomes literal following source; lossless, no new hints/evidence/budget/model",
    configure_cell=None,
    extra_pins=(),
    continue_rule="ordinary failure completes fixed diagnostics; infra/safety/budget stop; no replacement",
    conditional_expansion=None,
    identity_prefix="feedback-",
    dependency_snapshots=(),
    replay_repeats=1,
    reuse_prepared=False,
):
    BATCH = Path(batch).resolve()
    snapshot_dir = Path(snapshot_dir) if snapshot_dir else BATCH / "candidate-preimages"
    old = S.read(OLD / "cells.json")
    rows = S.read(BATCH / "cells.json") if reuse_prepared else {}
    for cell in ORDER:
        if reuse_prepared:
            prepared = rows[cell]
            root = Path(prepared["root"])
            if root != BATCH / "cells" / cell / "isolated" or any(
                S.sha(root / p) != digest for p, digest in prepared["files"].items()
            ):
                raise ValueError("Prepared input drift")
            if (
                cell.endswith("-1")
                and S.read(
                    BATCH / "full-chain-replay" / prepared["topic"] / "process.json"
                )["exit_code"]
            ):
                raise ValueError("Existing no-model proof failed")
            continue
        row = old[cell]
        topic = row["topic"]
        root = BATCH / "cells" / cell / "isolated"
        root.mkdir(parents=True, exist_ok=False)
        for relative, sha in row["files"].items():
            source = Path(row["root"]) / relative
            if relative == row["target"]:
                source = OLD / "templates" / topic / relative
            if S.sha(source) != sha:
                raise ValueError("Frozen start differs")
            dest = root / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
        identity = {k: identity_prefix + cell for k in ("task_id", "unit_id", "run_id")}
        packet = S.read(root / ".agent/packet.json")
        packet.update(identity)
        policy_path = root / "acceptance/capture-policy.json"
        policy = S.read(policy_path)
        policy["identity"] = identity
        config = S.read(root / ".agent/config.json")
        added = configure_cell(root, packet, policy, config) if configure_cell else []
        # Newly copied preparation inputs only; no execution archive exists here.
        import json

        for path, value in (
            (root / ".agent/packet.json", packet),
            (policy_path, policy),
        ):
            path.write_text(json.dumps(value, indent=2), encoding="utf-8")
        config["experimental_capture_policy_sha256"] = S.sha(policy_path)
        (root / ".agent/config.json").write_text(
            json.dumps(config, indent=2), encoding="utf-8"
        )
        # Separate full no-network replay before any live, one per task family.
        if cell.endswith("-1"):
            control = BATCH / "full-chain-replay" / topic / "isolated"
            shutil.copytree(root, control)
            symbol = config["coder_single_function"]["symbol"]
            reference = T.extract(
                OLD / "reference-checks" / topic / row["target"], symbol
            )
            replay = control.parent / "reference.json"
            S.save(replay, [{"replacement": reference}] * replay_repeats)
            result = T.run(build_command(control, replay=replay), control, timeout=180)
            S.save(control.parent / "process.json", result)
            if result["exit_code"]:
                raise ValueError("No-model full chain failed: " + topic)
        rows[cell] = {
            **row,
            "root": str(root),
            "identity": identity,
            "files": {p: S.sha(root / p) for p in [*row["files"], *added]},
        }
    if not reuse_prepared:
        S.save(BATCH / "cells.json", rows)
    old_registration = S.read(OLD / "registration.json")
    pins = dict(old_registration["pins"])
    lineage = {}
    for name in (
        "consolidated_harness.py",
        "consolidated_entry.py",
        "supervised_tasks.py",
    ):
        path = S.KIT / "benchmarks" / name
        snapshot = snapshot_dir / name
        if S.sha(snapshot) != pins[str(path)]:
            raise ValueError("Previous pinned source unavailable")
        lineage[str(path)] = {
            "previous_sha256": S.sha(snapshot),
            "snapshot": str(snapshot),
            "current_sha256": S.sha(path),
        }
        pins[str(snapshot)] = S.sha(snapshot)
        pins[str(path)] = S.sha(path)
    for path in (
        Path(__file__),
        S.KIT / "benchmarks/literal_check_feedback.py",
        S.KIT / "benchmarks/literal_feedback_rules.py",
        S.KIT / "benchmarks/bounded_source_rules.py",
        BATCH / "cells.json",
    ):
        pins[str(path.resolve())] = S.sha(path)
    for path in extra_pins:
        path = Path(path).resolve()
        pins[str(path)] = S.sha(path)
    for source, snapshot in dependency_snapshots:
        source, snapshot = Path(source).resolve(), Path(snapshot).resolve()
        if str(source) not in pins or S.sha(snapshot) != pins[str(source)]:
            raise ValueError("Dependency snapshot differs from frozen ancestor")
        lineage[str(source)] = {
            "previous_sha256": S.sha(snapshot),
            "snapshot": str(snapshot),
            "current_sha256": S.sha(source),
        }
        pins[str(snapshot)] = S.sha(snapshot)
        pins[str(source)] = S.sha(source)
    if any(S.sha(p) != sha for p, sha in pins.items()):
        raise ValueError("Unexpected dependency drift")
    S.save(
        BATCH / "registration.json",
        {
            "pins": pins,
            "lineage": lineage,
            "order": ORDER,
            "weekly_stop": 40,
            "batch_seconds": 14400,
            "registered": 6,
            "candidate": candidate_description,
            "gate": "6/6 supervised independent accept, each family2/2; no assistance or safety drift",
            "continue_rule": continue_rule,
            "conditional_expansion": conditional_expansion,
            "exposure": "All tasks exposed; repeat qualification only; prior failures remain",
            "model": "unchanged Qwen/Muse, single residency",
        },
    )
    print("Feedback candidate frozen after all three complete no-model replays")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["checkpoint", "prepare"])
    args = p.parse_args()
    checkpoint() if args.mode == "checkpoint" else prepare()
