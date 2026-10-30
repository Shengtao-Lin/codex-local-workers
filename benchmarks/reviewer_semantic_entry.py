"""Experimental task-local review; explicit per-obligation verdicts drive disposition."""

import argparse
import ast
import copy
import importlib.util
import json
import sys
import time
from pathlib import Path

import reviewer_experiment_entry as ENTRY

PROTOCOL = "reviewer-semantic-disposition-v1"
VERDICTS = {
    "satisfied",
    "implementation_defect",
    "required_test_gap",
    "contract_conflict",
    "uncertain",
}
SYSTEM = """Review the supplied implementation against every complete hard obligation.
Use REPORT. For each obligation choose satisfied, implementation_defect,
required_test_gap, contract_conflict, or uncertain. Explain your source-backed
judgment, including a concrete failing input/outcome when reporting a defect.
Required tests are obligations; optional test suggestions are advice only.
Select 1 to 3 actually displayed evidence IDs for each obligation. For a defect,
line must locate the defect within the first selected evidence ID; give severity
and a bounded fix. For other verdicts line may be null and fix may be empty.
Put unresolved owned-contract concerns in uncertainties with the contract_id;
use null only for optional advice or concerns outside this unit's ownership.
The host aggregates these explicit verdicts. There is no separate overall pass
label. Passing tests do not establish untested behavior. Never edit or execute
commands. If readable context is insufficient, report uncertain.
Reasoning strength: medium.
"""
FIELDS = {"obligations", "uncertainties"}
ITEM_FIELDS = {
    "id",
    "verdict",
    "evidence_ids",
    "explanation",
    "line",
    "fix",
    "severity",
}
PARAMS = {
    "type": "object",
    "properties": {
        "obligations": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string"},
                    "verdict": {"type": "string", "enum": sorted(VERDICTS)},
                    "evidence_ids": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 3,
                        "items": {"type": "string"},
                    },
                    "explanation": {"type": "string", "minLength": 1},
                    "line": {"type": ["integer", "null"], "minimum": 1},
                    "fix": {"type": "string"},
                    "severity": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                    },
                },
                "required": sorted(ITEM_FIELDS),
            },
        },
        "uncertainties": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "contract_id": {"type": ["string", "null"]},
                    "text": {"type": "string", "minLength": 1},
                },
                "required": ["contract_id", "text"],
            },
        },
    },
    "required": sorted(FIELDS),
    "additionalProperties": False,
}
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "REPORT",
            "description": "Submit independent per-obligation semantic judgments.",
            "parameters": PARAMS,
        },
    }
]


def assemble(runtime, args, error):
    """Only transform explicit model states; never inspect prose for semantic keywords."""
    if not isinstance(args, dict) or set(args) != FIELDS:
        raise error("REPORT requires exactly obligations and uncertainties")
    expected = {o["id"]: o for o in runtime.review_obligations()}
    rows, concerns = args["obligations"], args["uncertainties"]
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
        raise error("obligations must be an array of judgments")
    if len(rows) != len(expected) or {r.get("id") for r in rows} != set(expected):
        raise error(
            "exactly one judgment required for each obligation: " + ", ".join(expected)
        )
    if not isinstance(concerns, list):
        raise error("uncertainties must be an array")
    owned = set(runtime.packet["owned_contract_ids"])
    unresolved = set()
    for item in concerns:
        if not isinstance(item, dict) or set(item) != {"contract_id", "text"}:
            raise error("uncertainty requires contract_id and text")
        if not isinstance(item["text"], str) or not item["text"].strip():
            raise error("uncertainty text must be nonempty")
        if item["contract_id"] is not None:
            if item["contract_id"] not in owned:
                raise error("uncertainty contract_id must be owned or null")
            unresolved.add(item["contract_id"])
    contracts, findings, kinds = [], [], set()
    for row in rows:
        if set(row) != ITEM_FIELDS or row["verdict"] not in VERDICTS:
            raise error("invalid obligation fields or verdict")
        if not isinstance(row["explanation"], str) or not row["explanation"].strip():
            raise error("explanation must be nonempty")
        if not isinstance(row["fix"], str) or row["severity"] not in {
            "low",
            "medium",
            "high",
            "critical",
        }:
            raise error("fix/severity has invalid shape")
        ids = row["evidence_ids"]
        if (
            not isinstance(ids, list)
            or not 1 <= len(ids) <= 3
            or len(set(ids)) != len(ids)
            or any(
                not isinstance(key, str) or key not in runtime.evidence_catalog
                for key in ids
            )
        ):
            raise error("evidence_ids must select 1 to 3 distinct displayed IDs")
        nature = row["verdict"]
        if row["id"] in unresolved and nature == "satisfied":
            raise error(
                "satisfied contradicts explicitly unresolved owned contract: "
                + row["id"]
            )
        kinds.add(nature)
        status = (
            "verified"
            if nature == "satisfied"
            else "uncertain"
            if nature in {"uncertain", "contract_conflict"}
            else "violated"
        )
        contracts.append(
            {
                "obligation_id": row["id"],
                "status": status,
                "evidence_ids": ids,
                "evidence": row["explanation"],
            }
        )
        if nature in {"implementation_defect", "required_test_gap"}:
            ref = runtime.evidence_catalog[ids[0]]
            if (
                type(row["line"]) is not int
                or not ref["start_line"] <= row["line"] <= ref["end_line"]
            ):
                raise error("defect line must be inside first selected evidence ID")
            if not row["fix"].strip() or row["id"] not in owned:
                raise error("defect requires a bounded fix and owned contract id")
            findings.append(
                {
                    "id": "F" + str(len(findings) + 1),
                    "severity": row["severity"],
                    "category": nature,
                    "path": ref["path"],
                    "line": row["line"],
                    "contract_id": row["id"],
                    "evidence": row["explanation"],
                    "suggested_fix": row["fix"],
                }
            )
        elif row["line"] is not None and (
            type(row["line"]) is not int or row["line"] < 1
        ):
            raise error("line must be positive or null")
    assessment = (
        "contract_conflict"
        if "contract_conflict" in kinds
        else "insufficient_evidence"
        if "uncertain" in kinds or unresolved
        else "implementation_defect"
        if "implementation_defect" in kinds
        else "required_test_gap"
        if "required_test_gap" in kinds
        else "consistent"
    )
    return {
        "assessment": assessment,
        "findings": findings,
        "contract_review": contracts,
        "ordering_review": [],
        "unverified_claims": [r["text"] for r in concerns],
    }


def install(module):
    base = ENTRY.install(module)

    class SemanticReviewer(base):
        def bundle(self):
            self._assert_inputs_current()
            displayed = self.initial_payload()
            if displayed["diff_truncated"]:
                raise module.ReviewError(
                    "task-local cumulative diff exceeds original display bound"
                )
            if (
                self.ordering_constraints()
                or self.config.get("reviewer_require_search", False)
                or self.config.get("reviewer_require_approved_execution", False)
            ):
                raise module.ReviewError(
                    "semantic candidate does not support additional execution/search/ordering obligations"
                )
            paths = list(
                dict.fromkeys([*self.diff_paths(), *self.focused_test_paths()])
            )
            observations = []
            binding = self.config.get("coder_single_function", {})
            for path in paths:
                _, resolved = self._assert_read_allowed(path)
                lines = resolved.read_text(encoding="utf-8-sig").splitlines()
                start, end = 1, len(lines)
                if path == binding.get("path"):
                    tree = ast.parse("\n".join(lines))
                    node = next(
                        n
                        for n in tree.body
                        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and n.name == binding["symbol"]
                    )
                    start, end = node.lineno, node.end_lineno
                for first in range(start, end + 1, 20):
                    observation = self.read_file(
                        {
                            "path": path,
                            "start_line": first,
                            "end_line": min(first + 19, end),
                        }
                    )
                    if observation.get("truncated"):
                        raise module.ReviewError("task-local evidence truncated")
                    # Keep original displayed content and issued IDs, omit navigation state.
                    observations.append(
                        {
                            key: observation[key]
                            for key in (
                                "path",
                                "start_line",
                                "end_line",
                                "content",
                                "citation_evidence",
                            )
                        }
                    )
            if not self.required_reads_complete():
                raise module.ReviewError(
                    "task-local evidence does not satisfy original display gate"
                )
            return {
                "risk": self.packet["risk"],
                "owned_contract_ids": self.packet["owned_contract_ids"],
                "obligations": self.review_obligations(),
                "acceptance_criteria": self.packet["acceptance_criteria"],
                "acceptance_scenarios": self.packet["acceptance_scenarios"],
                "dependencies": binding.get("dependencies", ""),
                "dependency_provenance": "Archived trusted context, not independently executed evidence or source citations.",
                "actual_cumulative_diff": displayed["cumulative_diff"],
                "displayed_source_and_tests": observations,
                "scope": self.packet["scope"],
            }

        def run(self):
            if self.config.get("reviewer_preload_model") is True:
                self.client.ensure_loaded(
                    timeout_seconds=int(
                        self.config.get("reviewer_model_load_timeout_seconds", 360)
                    )
                )
            self.client.preflight()
            self.client.probe_structured_output()
            self.prepare()
            deadline = time.monotonic() + self.invocation_timeout
            bundle = self.bundle()
            module.RUN_STATE.write_json_once(
                self.review_root / "semantic-input.json", bundle
            )
            messages = [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": json.dumps(bundle, ensure_ascii=False)},
            ]
            self.client.native_tools = copy.deepcopy(TOOLS)
            # The same invocation budget covers judgment and deterministic assembly.
            for turn in range(1, self.max_turns + 1):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise module.ReviewError(
                        "shared semantic/assembly deadline exhausted"
                    )
                self._assert_inputs_current()
                original_timeout = self.client.timeout
                self.client.timeout = min(original_timeout, remaining)
                try:
                    raw = self.client.complete(messages)
                finally:
                    self.client.timeout = original_timeout
                module.RUN_STATE.write_json_once(
                    self.review_root / f"semantic-response-{turn}.json",
                    {"raw": raw, "request_stats": self.client.last_request_stats},
                )
                try:
                    action = module.WORKER.parse_action(raw)
                    if action["action"] != "REPORT":
                        raise module.ReviewError("only REPORT is available")
                    args = action["arguments"]
                    normalized = assemble(self, args, module.ReviewError)
                    report = self.validate_report(normalized)
                    report["semantic_review_protocol"] = PROTOCOL
                    report["semantic_verdicts"] = args
                    report["disposition_provenance"] = (
                        "Deterministic aggregation of explicit model per-obligation verdicts; no prose keyword inference."
                    )
                    report["reviewer_model_calls"] = turn
                    # Restore actual validation facts in final archive; they were not semantic assertions.
                    module.RUN_STATE.write_json_once(
                        self.review_root / "runtime-validation.json", self.validation
                    )
                    self._assert_inputs_current()
                    if time.monotonic() >= deadline:
                        raise module.ReviewError(
                            "shared semantic/assembly deadline exhausted"
                        )
                    return self.finalize(report)
                except (
                    module.ReviewError,
                    module.WORKER.WorkerError,
                    ValueError,
                    TypeError,
                    KeyError,
                ) as exc:
                    self.protocol_errors += 1
                    self.event(
                        "semantic_report_rejected", {"turn": turn, "error": str(exc)}
                    )
                    if self.protocol_errors >= self.max_protocol_errors:
                        raise module.ReviewError(
                            "semantic report protocol budget exhausted: " + str(exc)
                        ) from exc
                    # Corrections are field/evidence errors, no oracle or invalid-report example.
                    messages[1]["content"] = json.dumps(bundle, ensure_ascii=False) + (
                        "\nREPORT_SHAPE_CORRECTION\nReport rejected: "
                        + str(exc)
                        + ". Submit a corrected REPORT using the same evidence."
                    )
            raise module.ReviewError("shared semantic/assembly turn budget exhausted")

    module.ReviewerRuntime = SemanticReviewer
    return SemanticReviewer


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--runtime-dir", required=True)
    args, remaining = parser.parse_known_args()
    path = Path(args.runtime_dir) / "reviewer-runtime.py"
    spec = importlib.util.spec_from_file_location("semantic_reviewer_runtime", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    install(module)
    sys.argv = [str(path), *remaining]
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
