"""Experimental REPORT DTO; reuse the frozen Reviewer and its semantic/safety gates."""

import argparse
import copy
import importlib.util
import sys
from pathlib import Path

FIELDS = {
    "assessment",
    "findings",
    "contract_review",
    "ordering_review",
    "unverified_claims",
}
PROTOCOL = "reviewer-compact-report-v1"


def compact_tools(tools):
    result = copy.deepcopy(tools)
    for tool in result:
        function = tool.get("function", {})
        if function.get("name") != "REPORT":
            continue
        params = function["parameters"]
        for name in ("verified_contract_ids", "verified_check_ids"):
            params["properties"].pop(name, None)
        params["required"] = sorted(FIELDS)
        params["additionalProperties"] = False
        properties = {
            name: {"type": "string", "minLength": 1}
            for name in ("id", "category", "evidence", "suggested_fix")
        }
        properties.update(
            {
                "severity": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                },
                "path": {"type": ["string", "null"]},
                "line": {"type": ["integer", "null"], "minimum": 1},
                "contract_id": {"type": ["string", "null"]},
            }
        )
        params["properties"]["findings"]["items"] = {
            "type": "object",
            "properties": properties,
            "required": sorted(properties),
            "additionalProperties": False,
        }
    return result


def install(module):
    base = module.ReviewerRuntime

    class CompactReviewer(base):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if self.config.get("reviewer_compact_report") is not True:
                raise module.ReviewError(
                    "compact report experiment must be explicitly enabled"
                )
            if not self.assessment_protocol or not self.evidence_ids_enabled:
                raise module.ReviewError(
                    "compact report requires explicit assessment and evidence IDs"
                )
            if isinstance(getattr(self.client, "native_tools", None), list):
                self.client.native_tools = compact_tools(self.client.native_tools)

        def system_prompt(self):
            text = super().system_prompt()
            text = text.replace(
                "REPORT arguments: assessment, findings, verified_contract_ids, unverified_claims,\nordering_review, contract_review, verified_check_ids.",
                "REPORT arguments: assessment, findings, unverified_claims, ordering_review, contract_review.",
            )
            text = text.replace(
                "all owned contracts and configured\nchecks verified",
                "all owned contracts explicitly verified in contract_review and actual configured\nchecks passed",
            )
            return text + (
                "\nIn this REPORT protocol, explicitly assess every owned contract in contract_review. "
                "The host derives the contract index from those submitted statuses and check IDs "
                "from actual runtime results. Do not submit verified_contract_ids or verified_check_ids. "
                "Findings and semantic judgments remain yours; missing findings are never generated.\n"
            )

        def report_template(self):
            result = super().report_template()
            args = result["arguments"]
            args.pop("verified_contract_ids")
            args.pop("verified_check_ids")
            existing = {row["obligation_id"] for row in args["contract_review"]}
            for obligation in self.review_obligations():
                if obligation["id"] in existing:
                    continue
                args["contract_review"].append(
                    {
                        "obligation_id": obligation["id"],
                        "status": "CHOOSE verified, violated, or uncertain",
                        "evidence_ids": ["REPLACE WITH ACTUALLY DISPLAYED E-ID"],
                        "evidence": "REPLACE WITH CONTRACT-SPECIFIC REASONING",
                    }
                )
            return result

        def validate_report(self, args):
            if not isinstance(args, dict) or set(args) != FIELDS:
                raise module.ReviewError(
                    "compact REPORT requires exactly: " + ", ".join(sorted(FIELDS))
                )
            entries = args["contract_review"]
            if not isinstance(entries, list) or any(
                not isinstance(row, dict) for row in entries
            ):
                raise module.ReviewError(
                    "contract_review must be an array of explicit judgments"
                )
            normalized = copy.deepcopy(args)
            normalized["verified_contract_ids"] = [
                row.get("obligation_id")
                for row in entries
                if row.get("status") == "verified"
                and row.get("obligation_id") in self.packet["owned_contract_ids"]
            ]
            configured = self.validation.get("configured_checks", [])
            if not isinstance(configured, list):
                raise module.ReviewError("runtime configured_checks must be an array")
            normalized["verified_check_ids"] = [
                row["id"] for row in configured if row.get("status") == "passed"
            ]
            result = super().validate_report(normalized)
            result["review_protocol"] = PROTOCOL
            result["derived_field_provenance"] = {
                "verified_contract_ids": "explicit model contract_review statuses; no missing verdict inferred",
                "verified_check_ids": "trusted current validation facts, not model acknowledgement",
            }
            return result

        def report_repair(self, error, args):
            repair = super().report_repair(error, args)
            if error.startswith("verified_contract_ids contradicts"):
                repair["instruction"] = (
                    "Reconcile findings with your explicit contract_review statuses; a contract "
                    "cannot be both verified and defective. Do not submit the host-derived index. "
                    "Do not change a semantic verdict merely to satisfy a field check."
                )
            return repair

    module.ReviewerRuntime = CompactReviewer
    return CompactReviewer


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--runtime-dir", required=True)
    args, remaining = parser.parse_known_args()
    path = Path(args.runtime_dir) / "reviewer-runtime.py"
    spec = importlib.util.spec_from_file_location("compact_reviewer_runtime", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    install(module)
    sys.argv = [str(path), *remaining]
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
