"""Experimental provisional one-obligation reports; canonical final gates unchanged."""

import argparse
import copy
import importlib.util
import json
import sys
from pathlib import Path

from reviewer_required_tool_adapter import install as install_required
from reviewer_sampling_probe_adapter import install as install_probe


def install(reviewer):
    original_init = reviewer.ReviewerRuntime.__init__
    original_validate = reviewer.ReviewerRuntime.validate_report
    original_challenge = reviewer.ReviewerRuntime._prepass_challenge
    original_prompt = reviewer.ReviewerRuntime.system_prompt
    original_template = reviewer.ReviewerRuntime.report_template
    original_payload = reviewer.ReviewerRuntime.initial_payload
    original_repair = reviewer.ReviewerRuntime.report_repair
    original_run = reviewer.ReviewerRuntime.run
    original_finalize = reviewer.ReviewerRuntime.finalize
    native = copy.deepcopy(reviewer.REVIEW_NATIVE_TOOLS)
    report_tool = next(tool for tool in native if tool["function"]["name"] == "REPORT")
    params = report_tool["function"]["parameters"]
    final_fields = set(params["properties"]) - {"contract_review"}
    assessment_schema = params["properties"].pop("contract_review")["items"]
    params["properties"].update(
        {
            "stage": {"type": "string", "enum": ["assessment", "final"]},
            "assessment": assessment_schema,
            "assessment_ids": {
                "type": "array",
                "uniqueItems": True,
                "items": {"type": "string"},
            },
        }
    )
    params["required"] = ["stage"]
    reviewer.REVIEW_NATIVE_TOOLS = native

    def init(runtime, *args, **kwargs):
        original_init(runtime, *args, **kwargs)
        runtime.staged_assessments = {}

    def state(runtime):
        obligations = runtime.review_obligations()
        return {
            "provisional_only": True,
            "required_before_pass": [item["id"] for item in obligations],
            "next_obligation": next(
                (
                    item
                    for item in obligations
                    if item["id"] not in runtime.staged_assessments
                ),
                None,
            ),
            "assessments": [
                {
                    "id": key,
                    "status": value["entry"]["status"],
                    "evidence": value["entry"]["evidence"],
                    "findings": value["findings"],
                }
                for key, value in runtime.staged_assessments.items()
            ],
            "instruction": "Citations are mechanically checked, semantic claims remain unreviewed. Assess one pending obligation, or submit a final rework/escalate for source-grounded defects. Passing requires all obligations and original final gates.",
        }

    def validate(runtime, args):
        stage = args.get("stage")
        if stage == "assessment":
            if set(args) - {"stage", "assessment", "findings"}:
                raise reviewer.ReviewError(
                    "assessment stage accepts only stage, assessment, findings"
                )
            entry = args.get("assessment")
            if not isinstance(entry, dict):
                raise reviewer.ReviewError(
                    "assessment stage requires one assessment object"
                )
            obligation_id = entry.get("obligation_id")
            if (
                isinstance(obligation_id, str)
                and obligation_id in runtime.staged_assessments
            ):
                raise reviewer.ReviewError(
                    "assessment obligation already recorded; do not replay it"
                )
            verified = (
                [obligation_id]
                if entry.get("status") == "verified"
                and obligation_id in runtime.packet["owned_contract_ids"]
                else []
            )
            package = {
                "decision": "escalate",
                "findings": args.get("findings", []),
                "verified_contract_ids": verified,
                "unverified_claims": [],
                "contract_review": [copy.deepcopy(entry)],
            }
            checked = original_validate(runtime, package)
            index = len(runtime.staged_assessments) + 1
            reviewer.RUN_STATE.write_json_once(
                runtime.review_root / f"assessment-{index}.json",
                {
                    "provisional_only": True,
                    "model_claim": entry,
                    "validated_citations_and_structure": checked,
                    "semantic_acceptance": False,
                },
            )
            runtime.staged_assessments[obligation_id] = {
                "entry": copy.deepcopy(entry),
                "findings": copy.deepcopy(checked["findings"]),
            }
            checked["staged_assessment_id"] = obligation_id
            return checked
        if stage != "final":
            raise reviewer.ReviewError("REPORT stage must be assessment or final")
        if set(args) - (final_fields | {"stage", "assessment_ids"}):
            raise reviewer.ReviewError(
                "final stage uses assessment_ids, not assessment or contract_review"
            )
        ids = args.get("assessment_ids")
        if (
            not isinstance(ids, list)
            or any(not isinstance(item, str) for item in ids)
            or len(set(ids)) != len(ids)
            or any(item not in runtime.staged_assessments for item in ids)
        ):
            raise reviewer.ReviewError(
                "assessment_ids must be distinct recorded obligation IDs"
            )
        expected = {item["id"] for item in runtime.review_obligations()}
        if args.get("decision") == "pass_to_primary" and set(ids) != expected:
            raise reviewer.ReviewError(
                "staged pass requires every recorded obligation ID"
            )
        canonical = copy.deepcopy(args)
        canonical.pop("stage")
        canonical.pop("assessment_ids")
        canonical["contract_review"] = [
            copy.deepcopy(runtime.staged_assessments[item]["entry"]) for item in ids
        ]
        checked = original_validate(runtime, canonical)
        retained = checked["findings"]
        if any(
            finding not in retained
            for value in runtime.staged_assessments.values()
            for finding in value["findings"]
        ):
            raise reviewer.ReviewError(
                "final report must retain every recorded provisional finding unchanged"
            )
        return checked

    def challenge(runtime, report):
        if "staged_assessment_id" in report:
            runtime.event(
                "provisional_assessment_recorded",
                {
                    "obligation_id": report["staged_assessment_id"],
                    "semantic_acceptance": False,
                },
            )
            return {"status": "assessment_recorded", **state(runtime)}
        return original_challenge(runtime, report)

    def prompt(runtime):
        return (
            original_prompt(runtime)
            + "\nSTAGED_REVIEW: Keep the entire canonical packet and atomic unit intact. REPORT stage=assessment supplies exactly one assessment (obligation_id,status,source_ref or source_refs,evidence) and optional findings. Read evidence first. This is provisional, not acceptance. Inspect one obligation at a time; the trusted next_obligation is a navigation hint, not a verdict. REPORT stage=final supplies decision, findings, verified_contract_ids, unverified_claims, verified_check_ids, ordering_review and assessment_ids selecting your recorded entries; do not resend contract_review. Retain every recorded provisional finding unchanged in final findings. Every pass still requires all canonical contracts, original source/read/version/ordering/check gates. You may report final rework/escalate early with actual findings and selected recorded IDs. Do not mark entries verified just to complete the sequence."
        )

    def template(runtime):
        result = original_template(runtime)
        result["arguments"].pop("contract_review")
        result["arguments"].update(stage="final", assessment_ids=[])
        return result

    def payload(runtime):
        result = original_payload(runtime)
        result["staged_review"] = state(runtime)
        return result

    def repair(runtime, error, args):
        if args.get("stage") == "assessment":
            args = {
                "contract_review": [args.get("assessment", {})],
                "findings": args.get("findings", []),
            }
        result = original_repair(runtime, error, args)
        result["staged_review"] = state(runtime)
        result["stage_instruction"] = (
            "Assessment: stage=assessment, one assessment object, optional findings only. Final: stage=final, assessment_ids, original report fields except contract_review. No automatic semantic confirmation."
        )
        return result

    def run(runtime):
        complete = runtime.client.complete

        def with_state(messages):
            return complete(
                [
                    *messages,
                    {
                        "role": "user",
                        "content": "STAGED_REVIEW_STATE\n"
                        + json.dumps(state(runtime), ensure_ascii=False),
                    },
                ]
            )

        runtime.client.complete = with_state
        try:
            return original_run(runtime)
        finally:
            runtime.client.complete = complete

    def finalize(runtime, report):
        if "staged_assessment_id" in report:
            raise reviewer.ReviewError(
                "provisional assessment cannot finalize a review"
            )
        return original_finalize(runtime, report)

    reviewer.ReviewerRuntime.__init__ = init
    reviewer.ReviewerRuntime.validate_report = validate
    reviewer.ReviewerRuntime._prepass_challenge = challenge
    reviewer.ReviewerRuntime.system_prompt = prompt
    reviewer.ReviewerRuntime.report_template = template
    reviewer.ReviewerRuntime.initial_payload = payload
    reviewer.ReviewerRuntime.report_repair = repair
    reviewer.ReviewerRuntime.run = run
    reviewer.ReviewerRuntime.finalize = finalize


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--snapshot", type=Path, required=True)
    args, remaining = parser.parse_known_args()
    spec = importlib.util.spec_from_file_location(
        "staged_reviewer", args.snapshot / ".local-agents/reviewer-runtime.py"
    )
    reviewer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = reviewer
    spec.loader.exec_module(reviewer)
    install(reviewer)
    install_required(reviewer)
    install_probe(reviewer)
    sys.argv = ["reviewer-runtime.py", *remaining]
    raise SystemExit(reviewer.main())
