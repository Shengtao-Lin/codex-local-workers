"""Ruff localization candidate with the previous block-only three-repeat protocol."""

import argparse
import shutil
import subprocess

import convergence_block_only_trial as prior
import convergence_coder_schema_trial as trial

KIT = trial.KIT
BASE = KIT / "benchmarks/work/system-convergence/ruff-repair-20261011-1"
PREVIOUS = prior.BASE
REPEATS = 3
ORIGINAL_CONFIGURE = prior.configure
prior.BASE = BASE


def configure(index):
    result = ORIGINAL_CONFIGURE(index)
    result.RUN = f"real-trace-batch-pilot-ruff-repair-r{index}-unit-1-a1"
    return result


prior.configure = configure


def checkpoint():
    BASE.mkdir(exist_ok=False, parents=True)
    listed = subprocess.run(
        ["git", "ls-files", "-c", "-o", "--exclude-standard"],
        cwd=KIT, check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    paths = {KIT / p for p in listed if (KIT / p).is_file()}
    paths.add(KIT / ".local-agents/config.json")
    paths.update(p for p in trial.files(BASE.parent) if not p.is_relative_to(BASE))
    for sibling in (KIT.parent / "agent-evaluation-harness", KIT.parent / "agent-runtime-kit"):
        for directory in ("src", "tests", ".agent", ".local-agents", "docs"):
            paths.update(trial.files(sibling / directory))
        paths.update(p for p in (sibling / "AGENTS.md", sibling / "config.json", sibling / "pyproject.toml") if p.is_file())
    preimage = BASE / "preimages/.local-agents/worker-runtime.py"
    preimage.parent.mkdir(parents=True)
    shutil.copyfile(KIT / ".local-agents/worker-runtime.py", preimage)
    trial.save(BASE / "baseline.json", {str(p): trial.sha(p) for p in sorted(paths)})
    trial.save(BASE / "authorization.json", {
        "weekly_used_start": 9, "weekly_used_ceiling": 15,
        "candidate_files": [".local-agents/worker-runtime.py"],
        "candidate": "Parse Ruff rule/path/line/column and expose bounded current source/hash only for verified unchanged validation inputs and readable scope; require existing SAFE_REPLACE only for authorized current writable source. No lint waiver, added prompt, invented source, semantic confirmation or automatic editing.",
        "fixed_repeats": REPEATS, "external_rework": 0,
        "gate": "All three clean Coder/Reviewer/independent integration/Primary gates pass; no unsafe edit, no single-line capability; retain every other failure and do not retune within batch. n=3 only qualifies this frozen slice.",
        "block_only_Reviewer_models_contract_tests_config_budgets": "unchanged",
        "failure_policy": "Run fixed three unless weekly ceiling, unsafe state or external blocker. No external repair/retry or changed packet between cases.",
        "brothers": "read-only", "commit_push": False, "single_model_residency": True,
    })
    print("checkpoint preserved", len(paths), "files", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["checkpoint", "setup", "propose", "approve", "packet", "dispatch", "integration"])
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--note", default="Primary authorizes one frozen Ruff-localization clean replay. Same high-risk contract, block-only actions, models, protected tests, scope, sampling and budgets. No external rework or automatic acceptance.")
    args = parser.parse_args()
    if args.action == "checkpoint":
        checkpoint()
    elif args.action == "setup":
        prior.setup(args.repeat)
    else:
        raise SystemExit(prior.step(args.action, args.repeat, args.note))
