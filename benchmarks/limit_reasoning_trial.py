"""Two-pass non-executing isolation: constrained versus plain analysis first."""

import argparse
import hashlib
import json

import limit_direct_trial as direct
from capability_fit import WORK, write

trial = direct.trial
trial.BASE = WORK / "limit-reasoning-1"
trial.SNAPSHOT = WORK / "limit-prepass-runtime-2"
trial.ARMS = (
    "semantic-json-1",
    "semantic-plain-1",
    "semantic-plain-2",
    "semantic-json-2",
)


def install(worker, root, plain):
    original = worker.LMStudioClient.complete

    def complete(client, messages):
        saved = (
            client.structured_output,
            client.action_schema,
            client.schema_name,
            client.max_tokens,
        )
        analysis = ""
        try:
            client.structured_output = not plain
            client.action_schema = {
                "type": "object",
                "properties": {"analysis": {"type": "string"}},
                "required": ["analysis"],
                "additionalProperties": False,
            }
            client.schema_name = "untrusted_contract_analysis"
            client.max_tokens = 1024
            analysis_messages = [
                {
                    "role": "system",
                    "content": (
                        "Analyze the provided implementation task before writing code. Trace an important boundary through a proposed algorithm and compare its result with the hard contract. Check callback ordering, occurrence ties, payload comparison and typing. Do not execute or claim tests passed. Do not emit a patch or tool call. "
                        + (
                            "Return plain analysis text."
                            if plain
                            else "Return JSON with only an analysis string."
                        )
                    ),
                },
                *messages[1:],
            ]
            raw = original(client, analysis_messages)
            analysis = raw if plain else json.loads(raw)["analysis"]
            if (
                not isinstance(analysis, str)
                or not analysis.strip()
                or len(analysis) > 12000
            ):
                raise ValueError("invalid or oversized untrusted analysis")
            write(
                root / ".agent/direct-analysis.json",
                {
                    "untrusted_analysis": analysis,
                    "analysis_sha256": hashlib.sha256(analysis.encode()).hexdigest(),
                    "stats": dict(client.last_request_stats),
                    "semantic_verification": False,
                    "executed_actions": False,
                },
            )
        finally:
            (
                client.structured_output,
                client.action_schema,
                client.schema_name,
                client.max_tokens,
            ) = saved
        # No source edit, validation evidence, scope or acceptance is inferred.
        # Both conditions get one equally bounded analysis call, then the same
        # original module proposal request. These are not agent/handoff runs.
        return original(
            client,
            [
                *messages,
                {"role": "assistant", "content": analysis},
                {
                    "role": "user",
                    "content": "The preceding analysis is your unverified proposal, not authority. Reconcile it with actual source, protected tests and the hard contract. Now return ONLY the required complete module JSON proposal.",
                },
            ],
        )

    worker.LMStudioClient.complete = complete


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "propose", "apply-reviewed"))
    parser.add_argument("--arm", choices=trial.ARMS, required=True)
    args = parser.parse_args()
    if args.action == "prepare":
        trial.prepare(
            args.arm,
            clean_start=True,
            config_overrides={
                "coder_temperature": 0.1,
                "coder_top_p": 0.9,
                "coder_top_k": 40,
                "coder_repeat_penalty": 1.0,
            },
        )
        if not (trial.BASE / "registration.json").exists():
            write(
                trial.BASE / "registration.json",
                {
                    "arms_in_order": list(trial.ARMS),
                    "weekly_ceiling": 23,
                    "axis": "First analysis call constrained to a JSON string versus plain text, then identical structured complete-module proposal",
                    "budget": "Each arm adds exactly one non-executing 1024-token analysis request, then original 4096-token proposal; extra reasoning cost is explicit",
                    "unchanged": "Current Qwen, sampling, original legacy source, complete protected source/tests/contract/recipe input and proposal schema",
                    "motivation": "Direct one-shot proposals and near-complete draft repair both failed; determine whether an explicit free analysis phase changes semantic capability before adding any production mechanism",
                    "gate": "No execution during generation; actual Primary diff review plus exact proposal hash approval before isolated application and protected closure/static checks",
                    "credit": "Capability isolation only, not Coder agent success, Reviewer handoff, stable release or cloud savings; direct-1 and all other failures retained",
                },
            )
    elif args.action == "propose":
        original_loader = direct.load_worker

        def load_with_analysis(snapshot):
            worker = original_loader(snapshot)
            install(worker, trial.BASE / args.arm, "-plain-" in args.arm)
            return worker

        direct.load_worker = load_with_analysis
        direct.propose(args.arm)
    else:
        direct.apply_reviewed(args.arm)
