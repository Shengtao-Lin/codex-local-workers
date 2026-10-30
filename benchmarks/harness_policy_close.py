"""Primary closeout: correct rework labels with false causes do not get credit."""

import argparse

import harness_reviewer_stage_close as C
import harness_semantic_policy as H

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--used", type=int, required=True)
    args = parser.parse_args()
    C.close(
        H,
        {
            "sample-17-candidate": (
                "incorrect_causal_finding",
                "Rework fix happens to remove the real guard, but model falsely claims is not None excludes False/0/empty-string and that the passing False test fails. Does not identify None/requested counterexample. No causal detection credit.",
            ),
            "sample-19-candidate": (
                "model_output_budget_exhausted",
                "Correct reference received no final action: 3862 actual prompt tokens and 4096 completion tokens used in reasoning, finish length. Original raw infra_failure retained; classify as model output-budget quality failure, not HTTP/context overflow.",
            ),
            "sample-20-candidate": (
                "incorrect_causal_finding",
                "Rework cites False/0/empty string/list being excluded by is not None and falsely predicts protected False test failure. These values are not None; no actual None update/status counterexample. Correct patch alone is not valid review reasoning.",
            ),
        },
        args.used,
        "canonical-policy",
        "Do not promote or tune more prompts/decoding values. Build a no-model, data-only approved-counterexample observation prototype and a concrete scope/authority proposal. Remaining static reasoning errors need grounding; output recovery alone cannot repair incorrect causes.",
    )
