"""Action-specific required argument transport after non-executing preflight."""

import argparse

import limit_recipe_trial as recipe
from capability_fit import WORK, write
from inherited_context_recovery import read

trial = recipe.trial
trial.BASE = WORK / "limit-tagged-1"
trial.SNAPSHOT = WORK / "coder-tagged-runtime-1"
trial.ARMS = (
    "semantic-control-1",
    "semantic-tagged-1",
    "semantic-tagged-2",
    "semantic-control-2",
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--arm", choices=trial.ARMS, required=True)
    args = parser.parse_args()
    if args.action == "prepare":
        if not read(WORK / "coder-tagged-preflight-1/facts.json")["passed"]:
            raise ValueError("actual transport compatibility preflight required")
        trial.prepare(
            args.arm,
            clean_start=True,
            config_overrides={
                "coder_typed_action_arguments": "-tagged-" in args.arm,
                "coder_repair_focus_retention": "latest",
                "coder_post_edit_source_echo": False,
                "coder_diverse_failure_examples": False,
                "coder_require_implementation_plan": False,
                "reviewer_native_history": False,
            },
        )
        if not (trial.BASE / "registration.json").exists():
            write(
                trial.BASE / "registration.json",
                {
                    "arms_in_order": list(trial.ARMS),
                    "weekly_ceiling": 23,
                    "changed_axis": "Default-off action-specific required argument schema on/off",
                    "unchanged": "Nonterminal baseline, runtime dispatcher/gates, models, source/tests, contract/recipe, latest retention, budgets",
                    "credit": "Assisted paired diagnostic; no preflight/correct-format credit as semantic success",
                },
            )
    else:
        trial.run(args.arm)
