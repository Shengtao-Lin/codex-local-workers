"""Resume after pre-model typed-transport startup correction; old freeze stays immutable."""

import argparse
import importlib.util
import shutil
from pathlib import Path

import single_function_patch_phase_trial as trial

STAGE = trial.BASE
trial.BASE = STAGE / "live"
trial.prior.BASE = trial.BASE

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["setup", "run", "audit", "finish"])
    parser.add_argument("--case")
    args = parser.parse_args()
    if args.action == "setup":
        trial.setup()
        shutil.copyfile(STAGE / "baseline.json", trial.BASE / "baseline.json")
        trial.prior.common.save(trial.BASE / "transport-correction.json", {
            "old_attempt": "../repair-1/entry-result.json", "model_requests_in_old_attempt": 0,
            "reason": "Existing frozen config uses typed actions. Temporarily suspend action typing only for patch schema and restore it before subsequent calls, including transport failure. Config and all other frozen factors unchanged.",
            "wrapper_sha256": trial.prior.common.sha(Path(__file__)),
            "no_model_result_based_tuning": True})
    elif args.action == "run": trial.prior.run(args.case)
    elif args.action == "audit":
        spec = importlib.util.spec_from_file_location(
            "terminal_audit", STAGE.parent / "single-function-terminal-20261012-1/audit.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.BASE = trial.BASE
        module.case(args.case)
    else: trial.finish()
