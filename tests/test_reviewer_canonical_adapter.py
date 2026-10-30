import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from reviewer_canonical_adapter import install


def test_canonical_adapter_never_changes_claims_or_bypasses_original_gate():
    class Runtime:
        def report_template(self):
            return {
                "arguments": {
                    "contract_review": [
                        {
                            "status": "uncertain",
                            "source_ref": {
                                "path": "source",
                                "start_line": 1,
                                "end_line": 1,
                            },
                        }
                    ]
                }
            }

        def system_prompt(self):
            return "Original authority and safety contract"

        def validate_report(self, args):
            raise RuntimeError(
                "Original unread, freshness and semantic gates still ran"
            )

    reviewer = SimpleNamespace(
        ReviewerRuntime=Runtime,
        REVIEW_NATIVE_TOOLS=[],
        canonical_citation_tools=lambda tools: tools,
        ReviewError=ValueError,
    )
    install(reviewer)
    runtime = Runtime()
    entry = runtime.report_template()["arguments"]["contract_review"][0]
    assert entry["status"] == "uncertain"
    assert entry["source_refs"] == [{"path": "source", "start_line": 1, "end_line": 1}]
    assert "source_ref" not in entry
    assert runtime.system_prompt().startswith("Original authority and safety contract")
    with pytest.raises(ValueError, match="only obligation_id"):
        runtime.validate_report({"contract_review": [{"source_ref": {}}]})
    with pytest.raises(RuntimeError, match="Original unread"):
        runtime.validate_report(
            {
                "contract_review": [
                    {
                        "obligation_id": "id",
                        "status": "uncertain",
                        "source_refs": [
                            {"path": "unread", "start_line": 1, "end_line": 1}
                        ],
                        "evidence": "unverified claim",
                    }
                ]
            }
        )
