"""Fixed three clean replays of one frozen slice; no external rework or retuning."""

import argparse
import json
import shutil
import subprocess
from pathlib import Path

import convergence_coder_schema_trial as old

KIT = old.KIT
BASE = KIT / "benchmarks/work/system-convergence/block-only-20261011-1"
PREVIOUS = old.BASE
REPEATS = 3
ORIGINAL_COMMAND = old.command


def current_command(argv, name, *, root=None, python=old.PYTHON):
    # Imported function defaults retain the prior directory, not the new globals.
    return ORIGINAL_COMMAND(argv, name, root=old.ROOT if root is None else root, python=python)


def checkpoint():
    BASE.mkdir(parents=True, exist_ok=False)
    tracked = subprocess.run(
        ["git", "ls-files", "-c", "-o", "--exclude-standard"], cwd=KIT,
        check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    paths = {KIT / p for p in tracked if (KIT / p).is_file()}
    paths.add(KIT / ".local-agents/config.json")
    paths.update(p for p in old.files(BASE.parent) if not p.is_relative_to(BASE))
    for sibling in (KIT.parent / "agent-evaluation-harness", KIT.parent / "agent-runtime-kit"):
        for directory in ("src", "tests", ".agent", ".local-agents", "docs"):
            paths.update(old.files(sibling / directory))
        paths.update(p for p in (sibling / "AGENTS.md", sibling / "pyproject.toml", sibling / "config.json") if p.is_file())
    target = BASE / "preimages/.local-agents/worker-runtime.py"
    target.parent.mkdir(parents=True)
    shutil.copyfile(KIT / ".local-agents/worker-runtime.py", target)
    old.save(BASE / "baseline.json", {str(p): old.sha(p) for p in sorted(paths)})
    old.save(BASE / "authorization.json", {
        "weekly_used_start": 8, "weekly_used_ceiling": 15, "fixed_repeats": REPEATS,
        "candidate_files": [".local-agents/worker-runtime.py"],
        "candidate_flag": {"coder_block_edits_only": True},
        "candidate": "Remove single-line edit from every Coder transport allowlist and its capability description; reject attempted single-line edit before mutation. Existing-file edits use exact/hash-guarded SAFE_REPLACE; scoped SAFE_CREATE remains available.",
        "Reviewer_models_contract_tests_sampling_context_budgets": "unchanged",
        "qualification": "All three clean Coder/Reviewer/independent integration/Primary gates pass, no external rework, no unsafe edit and no advertised or executed single-line action. Preserve all other protocol failures. n=3 is bounded smoke evidence, not broad stability or economic proof.",
        "failure_policy": "Retain each failure and continue fixed batch unless usage ceiling, unsafe state or external blocker; no candidate/packet/test retuning within batch",
        "external_rework": 0, "single_model_residency": True,
        "brothers": "read-only", "commit_push": False,
    })
    print("checkpoint preserved", len(paths), "files", flush=True)


def configure(index):
    assert 1 <= index <= REPEATS
    old.BASE = BASE / f"repeat-{index}"
    old.ROOT = old.BASE / "isolated"
    old.PREVIOUS = PREVIOUS
    old.RUN = f"real-trace-batch-pilot-block-only-r{index}-unit-1-a1"
    old.command = current_command
    return old


def setup(index):
    trial = configure(index)
    trial.BASE.mkdir(exist_ok=False)
    trial.ROOT.mkdir(exist_ok=False)
    dist = trial.BASE / "distribution"
    dist.mkdir(exist_ok=False)
    installer = trial.load("block_only_installer", KIT / "scripts/install_local_agents.py")
    for relative in installer.inventory(KIT):
        target = dist / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(KIT / relative, target)
    trial.save(trial.BASE / "installation.json", installer.install(dist, trial.ROOT, apply=True))
    prior_root = PREVIOUS / "isolated"
    brief = trial.read(prior_root / ".agent/brief.json")
    for relative, digest in brief["source_hashes"].items():
        source = (KIT / "benchmarks/fixtures/real-trace-batch-v1/original" / relative
                  if relative == trial.SOURCE else prior_root / relative)
        assert trial.sha(source) == digest
        target = trial.ROOT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    trial.save(trial.ROOT / ".agent/brief.json", brief)
    shutil.copyfile(prior_root / ".agent/context.json", trial.ROOT / ".agent/context.json")
    config = trial.read(prior_root / ".agent/config.json")
    assert "coder_block_edits_only" not in config
    config["coder_block_edits_only"] = True
    trial.save(trial.ROOT / ".agent/config.json", config)
    trial.save(trial.ROOT / ".agent/accepted-refs.json", {})
    trial.api().BRIEF.validate_brief(brief)
    trial.save(trial.BASE / "registration.json", {
        "runtime_hashes": {p.relative_to(trial.ROOT).as_posix(): trial.sha(p) for p in trial.files(trial.ROOT / ".local-agents")},
        "brief_sha256": trial.sha(trial.ROOT / ".agent/brief.json"),
        "context_sha256": trial.sha(trial.ROOT / ".agent/context.json"),
        "config_sha256": trial.sha(trial.ROOT / ".agent/config.json"),
        "driver_sha256": trial.sha(KIT / "benchmarks/convergence_block_only_trial.py"),
        "prior_driver_sha256": trial.sha(KIT / "benchmarks/convergence_coder_schema_trial.py"),
        "old_source_test_profile_hashes_identical": True,
        "config_only_candidate_flag_added": True,
    })
    print("prepared clean repeat", index, flush=True)


def step(action, index, note):
    trial = configure(index)
    if action == "packet":
        trial.packet()
        return 0
    if action == "integration":
        trial.integration()
        return 0
    extras = {
        "propose": ["--context", trial.ROOT / ".agent/context.json", "--authorize-step"],
        "approve": ["--approval", trial.ROOT / ".agent/approval.json", "--authorize-step", "--note", note],
        "dispatch": ["--approval", trial.ROOT / ".agent/approval.json", "--refs", trial.ROOT / ".agent/accepted-refs.json", "--packet", trial.ROOT / ".agent/unit-1-packet.json", "--authorize-step"],
    }
    names = {"propose": "coordinator-propose.json", "approve": "primary-approve.json", "dispatch": "unit-1-dispatch.json"}
    if action == "propose" and (trial.BASE / names[action]).exists():
        original = trial.read(trial.BASE / names[action])
        assert original["exit"] == 2 and "Coordinator state path must be inside repository .agent" in original["stdout"]
        assert not (trial.ROOT / ".agent/proposal.json").exists()
        names[action] = "coordinator-propose-recovered.json"
    return trial.entry(action, extras[action], names[action])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["checkpoint", "setup", "propose", "approve", "packet", "dispatch", "integration"])
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--note", default="Primary authorizes this one fixed clean block-only replay. Original high-risk contract, protected tests, readable/writable scope, models and budgets unchanged; no automatic acceptance or external rework.")
    args = parser.parse_args()
    if args.action == "checkpoint":
        checkpoint()
    elif args.action == "setup":
        setup(args.repeat)
    else:
        raise SystemExit(step(args.action, args.repeat, args.note))
