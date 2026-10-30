"""One repair-state context candidate, with unchanged frozen normal-entry cases."""

import argparse
import importlib.util
import json
import subprocess
from pathlib import Path

import single_function_terminal_trial as previous

prior = previous.prior
OLD = previous.BASE
BASE = prior.KIT / "benchmarks/work/system-convergence/single-function-repair-state-20261012-1"
previous.BASE = BASE
previous.PREVIOUS = OLD
prior.BASE = BASE


def audit_module():
    spec = importlib.util.spec_from_file_location("previous_terminal_audit", OLD / "audit.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.BASE = BASE
    return module


def finish():
    frozen = prior.common.read(BASE / "freeze.json")
    for path, digest in frozen["candidate"].items():
        assert prior.common.sha(prior.KIT / path) == digest, path
    assert prior.common.sha(Path(__file__)) == prior.common.read(BASE / "candidate.json")["driver"]
    before = prior.common.read(BASE / "baseline.json")
    changed = [p for p, digest in before.items()
               if not Path(p).is_file() or prior.common.sha(Path(p)) != digest]
    allowed = {str(prior.KIT / ".local-agents/single-function-context.py")}
    assert all(p in allowed for p in changed if Path(p).is_relative_to(prior.KIT)), changed
    rows = [prior.common.read(BASE / name / "independent-result.json") for name in prior.ORDER]
    result = {"rows": rows, "full_chain_passed": sum(r["full_chain_pass"] for r in rows),
              "total": len(rows), "decision": "FROZEN_CORPUS_ONLY" if all(r["full_chain_pass"] for r in rows) else "NO_GENERAL_RELEASE",
              "pinned_files_checked": len(before), "changed_pinned_files": changed,
              "candidate_unchanged_after_live": True, "cross_file": "Primary only",
              "commit_push": False, "reviewer_unchanged": True}
    prior.common.save(BASE / "stage-conclusion.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["checkpoint", "setup", "run", "audit", "finish"])
    parser.add_argument("--case")
    args = parser.parse_args()
    if args.action == "checkpoint":
        prior.checkpoint()
        prior.common.save(BASE / "repair-state-authorization.json", {
            "weekly_used_start": 22, "weekly_used_ceiling": 30,
            "supersedes_checkpoint_candidate_description_only": True,
            "candidate": "Single-function context only: retain runtime-owned pending validation repair focus after action failures; stop replaying stale assistant proposals. No prompt, edit API, validation, terminal, Reviewer, model or budget changes.",
            "order": prior.ORDER, "gate": "6/6 normal entry + independent checks + Reviewer pass; unchanged corpus and all historical failures retained",
            "brothers_readonly": True, "commit_push": False})
    elif args.action == "setup":
        previous.setup()
        prior.common.save(BASE / "candidate.json", {"driver": prior.common.sha(Path(__file__)),
            "run_identity": "same run labels in distinct isolated repositories; no canonical archive is reused or overwritten"})
    elif args.action == "run":
        prior.run(args.case)
    elif args.action == "audit":
        audit_module().case(args.case)
    else:
        finish()
