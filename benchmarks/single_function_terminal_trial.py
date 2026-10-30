"""One state-transition candidate; unchanged single-function live corpus."""
import argparse
import copy
import shutil
from pathlib import Path

import single_function_entry_trial as prior

BASE = prior.KIT / "benchmarks/work/system-convergence/single-function-terminal-20261012-1"
PREVIOUS = prior.BASE / "live"
prior.BASE = BASE


def setup():
    old = prior.common.read(PREVIOUS / "freeze.json")
    frozen = {}
    for name in prior.ORDER:
        source = PREVIOUS / name / "isolated"
        root = BASE / name / "isolated"
        root.mkdir(parents=True, exist_ok=False)
        for folder in ["src", "tests"]:
            shutil.copytree(source / folder, root / folder, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copyfile(source / "pyproject.toml", root / "pyproject.toml")
        shutil.copytree(prior.KIT / ".local-agents", root / ".local-agents", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests"))
        packet = copy.deepcopy(prior.common.read(source / ".agent/packet.json"))
        run = source / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
        manifest = prior.common.read(run / "preimages.json")
        for item in manifest:
            if item["path"] in packet["scope"]["modify"]:
                # Archive preimages preserve the original failed/legacy starting point.
                shutil.copyfile(source / item["archive_path"], root / item["path"])
        for path, digest in old["cases"][name].items():
            if path.startswith(("src/", "tests/")) or path == "pyproject.toml":
                assert prior.common.sha(root / path) == digest, (name, path)
        packet["run_id"] = "single-terminal-" + name
        prior.common.save(root / ".agent/packet.json", packet)
        prior.common.save(root / ".agent/config.json", prior.common.read(source / ".agent/config.json"))
        frozen[name] = {p.relative_to(root).as_posix(): prior.common.sha(p) for p in prior.common.files(root)}
    prior.common.save(BASE / "freeze.json", {"cases": frozen, "order": prior.ORDER,
        "candidate": {p: prior.common.sha(prior.KIT / p) for p in prior.CANDIDATE},
        "driver": prior.common.sha(Path(prior.__file__)), "terminal_driver": prior.common.sha(Path(__file__))})
    print("frozen six unchanged inputs", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["checkpoint", "setup", "run"])
    parser.add_argument("--case")
    args = parser.parse_args()
    if args.action == "checkpoint":
        prior.checkpoint()
        prior.common.save(BASE / "terminal-authorization.json", {
            "weekly_used_start": 19, "weekly_used_ceiling": 30,
            "supersedes_checkpoint_candidate_description_only": True,
            "candidate": "Only single-function mode: after actual edit and all checks pass, verify existing submitted contract_check strictly, then promote to final gate before archiving. No acknowledgement synthesis, no prompt/context/model/acceptance changes.",
            "order": prior.ORDER, "gate": "6/6 normal entry + independent checks + Reviewer pass; old failures unchanged",
            "brothers_readonly": True, "commit_push": False})
    elif args.action == "setup": setup()
    else: prior.run(args.case)
