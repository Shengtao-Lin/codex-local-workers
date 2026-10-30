"""Matched current versus model-author sampling profile; no model change."""

import argparse

import limit_recipe_trial as recipe
from capability_fit import WORK, write

trial = recipe.trial
trial.BASE = WORK / "limit-sampling-1"
trial.SNAPSHOT = WORK / "limit-prepass-runtime-2"
trial.ARMS = (
    "semantic-control-1",
    "semantic-author-1",
    "semantic-author-2",
    "semantic-control-2",
)
AUTHOR_PROFILE = {
    "coder_temperature": 0.7,
    "coder_top_p": 0.8,
    "coder_top_k": 20,
    "coder_repeat_penalty": 1.05,
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--arm", choices=trial.ARMS, required=True)
    args = parser.parse_args()
    if args.action == "prepare":
        config = {
            "autoformat_on_diff_whitespace": True,
            "coder_diverse_failure_examples": False,
            "coder_typed_action_arguments": False,
            "coder_reset_failed_repair_context": False,
            "coder_repair_focus_retention": "latest",
            "coder_post_edit_source_echo": False,
            "coder_require_implementation_plan": False,
            "reviewer_native_history": False,
            "reviewer_prepass_challenge": False,
        }
        if "-author-" in args.arm:
            config.update(AUTHOR_PROFILE)
        trial.prepare(args.arm, clean_start=True, config_overrides=config)
        if not (trial.BASE / "registration.json").exists():
            write(
                trial.BASE / "registration.json",
                {
                    "arms_in_order": list(trial.ARMS),
                    "weekly_ceiling": 23,
                    "source": "https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct#best-practices",
                    "source_checked_date": "2026-10-08",
                    "changed_axis": "Sampling profile as a bundle; not attributing results to an individual parameter",
                    "control": {"temperature": 0.1, "top_p": 0.9, "top_k": 40, "repeat_penalty": 1},
                    "candidate": AUTHOR_PROFILE,
                    "unchanged": "Same model/quantization, residency, 24576 context, 4096 output budget, source/contract/recipe/protected tests/runtime and validation",
                    "hypothesis": "Low-temperature repeated wrong semantic patterns may improve with the author's profile; recommendations are not proof for this constrained task",
                    "credit": "Guided mechanism comparison, not unaided or general release; global user config unchanged",
                },
            )
    else:
        trial.run(args.arm)
