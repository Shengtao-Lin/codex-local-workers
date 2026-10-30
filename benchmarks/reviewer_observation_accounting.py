"""Require explicit model judgments for all facts, without a host semantic oracle."""

import argparse
import copy
import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import reviewer_conditional_recovery as BASE
import reviewer_semantic_entry as V1

PROTOCOL = "complete-observation-accounting-v1"
TOOLS = copy.deepcopy(V1.TOOLS)
PARAMS = TOOLS[0]["function"]["parameters"]
PARAMS["required"].append("observation_assessments")
PARAMS["properties"]["observation_assessments"] = {
    "type": "array",
    "description": "One explicit semantic judgment for EVERY supplied approved observation, in profile/example order. Actual outcomes are not expected results. Explain the relation to the owned contract; observations are not newly added project tests.",
    "items": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "profile_id": {"type": "string"},
            "case_index": {"type": "integer", "minimum": 0},
            "contract_id": {"type": "string"},
            "verdict": {
                "type": "string",
                "enum": ["consistent", "violation", "outside_contract", "uncertain"],
            },
            "explanation": {"type": "string", "minLength": 1},
        },
        "required": [
            "profile_id",
            "case_index",
            "contract_id",
            "verdict",
            "explanation",
        ],
    },
}


def validate_accounting(rows, expected, contract_review, error):
    if not isinstance(rows, list) or len(rows) != len(expected):
        raise error(
            "observation_assessments must account for every supplied profile/example exactly once in input order"
        )
    statuses = {r["obligation_id"]: r["status"] for r in contract_review}
    for item, identity in zip(rows, expected, strict=True):
        if not isinstance(item, dict) or set(item) != {
            "profile_id",
            "case_index",
            "contract_id",
            "verdict",
            "explanation",
        }:
            raise error(
                "observation assessment requires exact profile_id/case_index/contract_id/verdict/explanation fields"
            )
        if (
            type(item["case_index"]) is not int
            or (item["profile_id"], item["case_index"]) != identity
        ):
            raise error(
                "observation identity missing, duplicated or out of order: "
                + str(identity)
            )
        if (
            item["contract_id"] not in statuses
            or item["verdict"]
            not in {"consistent", "violation", "outside_contract", "uncertain"}
            or not isinstance(item["explanation"], str)
            or not item["explanation"].strip()
        ):
            raise error("invalid observation contract/verdict/explanation")
        if (
            item["verdict"] in {"violation", "uncertain"}
            and statuses[item["contract_id"]] == "verified"
        ):
            raise error(
                "verified obligation contradicts model's own "
                + item["verdict"]
                + " observation judgment; reconcile explicit judgments using unchanged evidence"
            )
    # No comparison against expected values, prose inference, auto-pass or auto-defect.
    return copy.deepcopy(rows)


def install(module):
    base = BASE.install(module)

    class AccountingReviewer(base):
        def bundle(self):
            result = super().bundle()
            self.expected_observations = [
                (profile["profile_id"], i)
                for profile in result["approved_observations"]
                for i, _ in enumerate(profile["examples"])
            ]
            return result

        def validate_report(self, args):
            report = super().validate_report(args)
            report["observation_assessments"] = validate_accounting(
                self.pending_observation_assessments,
                self.expected_observations,
                report["contract_review"],
                module.ReviewError,
            )
            report["observation_accounting_protocol"] = PROTOCOL
            return report

        def run(self):
            original = self.client.complete
            self.accounting_responses = 0
            self.pending_observation_assessments = None

            def complete(messages):
                raw = original(messages)
                self.accounting_responses += 1
                module.RUN_STATE.write_json_once(
                    self.review_root
                    / f"observation-response-{self.accounting_responses}.json",
                    {"raw": raw, "request_stats": self.client.last_request_stats},
                )
                self.pending_observation_assessments = None
                try:
                    parsed = json.loads(raw)
                except (ValueError, TypeError):
                    return raw
                if (
                    isinstance(parsed, dict)
                    and parsed.get("action") == "REPORT"
                    and isinstance(parsed.get("arguments"), dict)
                ):
                    self.pending_observation_assessments = parsed["arguments"].pop(
                        "observation_assessments", None
                    )
                    return json.dumps(parsed, ensure_ascii=False)
                return raw

            with (
                patch.object(self.client, "complete", complete),
                patch.object(V1, "TOOLS", TOOLS),
            ):
                return super().run()

    module.ReviewerRuntime = AccountingReviewer
    return AccountingReviewer


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--runtime-dir", required=True)
    args, remaining = parser.parse_known_args()
    path = Path(args.runtime_dir) / "reviewer-runtime.py"
    spec = importlib.util.spec_from_file_location("accounting_reviewer_runtime", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    install(module)
    sys.argv = [str(path), *remaining]
    raise SystemExit(module.main())
