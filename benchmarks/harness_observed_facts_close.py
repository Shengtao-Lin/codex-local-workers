"""Close factual-input stage, preserving output-limit failures as quality data."""

import argparse

import harness_observed_facts as H
import harness_reviewer_stage_close as C


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--used", type=int, required=True)
    args = parser.parse_args()
    C.close(
        H,
        {
            "sample-05-candidate": (
                "source_proof_declined",
                "Model acknowledges correct dict.get/no mutation source, but declines verification because present-empty/None/mutation scenarios lack explicit tests. No explicit extra-test requirement exists; correct source suffices under frozen criterion, so escalate is incorrect. This is not missing configured-check status or a type-ownership conflict.",
            ),
            "sample-17-candidate": (
                "model_output_budget_exhausted",
                "5627 prompt tokens and 4096 completion cap entirely in reasoning, no action. Actual observed values were supplied but no semantic report completed; no partial-analysis credit.",
            ),
            "sample-20-candidate": (
                "model_output_budget_exhausted",
                "Repeated bad-source call also exhausted 4096 completion cap, no action; preserve raw output-limit report, not an infrastructure retry or hidden success.",
            ),
        },
        args.used,
        "observations",
        "Keep candidate closed. Extend fixed Primary observations to all four approved pure fixture families, and add at most one output-limit recovery inside original shared 16-turn/4-error/deadline limits; record first-shot and recovered outcomes separately. No new model execution authority or budget increase.",
    )
