"""No network: exact receipt delta, immutable failures and unchanged stop cap."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import feedback_receipt_candidate as C
from test_bounded_evidence_candidate import (
    build as receipt_build,  # noqa: F401 - fixture reuse
)
from test_evidence_budget_preparation import setup_runtime  # noqa: F401 - fixture reuse


@pytest.mark.parametrize("enabled", [False, True])
def test_receipt_and_stop(request, enabled):
    observed = []

    def noop(messages, _w, host):
        facts = host.INTERFACE.restore_literal(messages[1]["content"])
        observed.append(facts)
        return json.dumps({"replacement": facts["target"]["source"]})

    runtime, _worker, host = request.getfixturevalue("receipt_build")([noop, noop], "A")
    runtime.config["experimental_explicit_noop_receipt"] = enabled
    runtime.__class__ = C.wrap(type(runtime), host)
    report = runtime.run()
    assert "Two unchanged" in report["failure_reason"]
    assert runtime.ledger["requests"] == runtime.ledger["noops"] == 2
    assert runtime.ledger["effective_edits"] == runtime.ledger["post_edit_checks"] == 0
    assert runtime.validation_count == 1
    first, second = observed
    assert first["target"] == second["target"]
    assert first["validation_failure"] == second["validation_failure"]
    receipt = {"status": "no_op", "source_sha256": second["target"]["sha256"]}
    assert (receipt in second["host_receipt"]["recent"]) is enabled
    runtime.noop_streak = 0
    messages, _ = runtime.proposal_context()
    assert (
        receipt
        not in host.INTERFACE.restore_literal(messages[1]["content"])["host_receipt"][
            "recent"
        ]
    )
