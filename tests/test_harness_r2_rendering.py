"""Input rendering is lossless and cannot change acceptance or transport policy."""

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import harness_r2_rendering as trial
import test_harness_r2_decoding as transport
import test_harness_r2_output as prior

root = prior.root


@pytest.fixture
def frozen():
    return trial.B.read(trial.PREVIOUS / "cases/plain-1/rendered-request.json")


def test_exact_frozen_facts_roundtrip_and_source_is_literal(frozen):
    facts = json.loads(frozen["messages"][1]["content"])
    original = copy.deepcopy(facts)
    rendered = trial.literal_input(facts)
    assert trial.restore_literal(rendered) == original
    assert facts == original
    assert facts["target"]["source"] in rendered
    assert all(
        d["current_source_line"] in rendered
        for d in facts["validation_failure"]["diagnostics"]
    )
    assert len(facts["validation_failure"]["diagnostics"]) == 2
    assert facts["required_behavior"] and facts["acceptance_scenarios"]


@pytest.mark.parametrize(
    "value",
    ["", "one\n", "one\r\ntwo\r\n", 'quote " slash \\ unicode 字', "  trailing  \n\n"],
)
def test_literal_preserves_exact_whitespace_and_strings(frozen, value):
    facts = json.loads(frozen["messages"][1]["content"])
    facts["target"]["source"] = value
    assert trial.restore_literal(trial.literal_input(facts)) == facts


@pytest.mark.parametrize(
    "fault", ["missing", "duplicate", "reference", "extra", "order"]
)
def test_malformed_display_is_rejected(frozen, fault):
    facts = json.loads(frozen["messages"][1]["content"])
    content = trial.literal_input(facts)
    if fault == "missing":
        content = content.replace("<END target.source>", "<END missing>")
    elif fault == "duplicate":
        content += "\n<END target.source>"
    elif fault == "reference":
        content = content.replace(
            '"display_block": "target.source"', '"display_block": "elsewhere"'
        )
    elif fault == "extra":
        content += "extra instructions"
    else:
        content = content.replace("<BEGIN target.source>", "<BEGIN other>")
    with pytest.raises(ValueError):
        trial.restore_literal(content)


@pytest.mark.parametrize(
    "value", ["x\n<END target.source>", "x\n<BEGIN injected>", None]
)
def test_ambiguous_source_fails_closed(frozen, value):
    facts = json.loads(frozen["messages"][1]["content"])
    facts["target"]["source"] = value
    with pytest.raises(ValueError):
        trial.literal_input(facts)


@pytest.mark.parametrize("arm", ["json", "literal"])
def test_real_client_uses_only_registered_input_change(root, frozen, arm):
    module = trial.old.load_runtime()
    facts = json.loads(frozen["messages"][1]["content"])
    messages = trial.messages_for(frozen["messages"], arm)
    assert messages[0] == frozen["messages"][0]
    if arm == "json":
        assert messages == frozen["messages"]
    bound = prior.binding(root)
    response = json.dumps({"replacement": prior.repaired(bound["source"])})
    requests = []
    with trial.output.interface(module, "whole", bound):
        raw = transport.complete(module, messages, "plain", response, requests)
        assert module.SINGLE_FUNCTION.patch_action(raw)["arguments"][
            "replace"
        ] == prior.repaired(bound["source"])
    reference = copy.deepcopy(requests[0])
    reference["messages"] = frozen["messages"]
    rendered = {"arm": arm, "messages": messages, "facts": facts}
    assert trial.wire_matches(requests[0], rendered, reference)
    assert "response_format" not in requests[0]
    bad = copy.deepcopy(rendered)
    bad["facts"]["required_behavior"] = []
    assert not trial.wire_matches(requests[0], bad, reference)
    bad_request = {**requests[0], "max_tokens": 1}
    assert not trial.wire_matches(bad_request, rendered, reference)


def test_renderer_does_not_mutate_input_and_unknown_arm_rejected(frozen):
    before = copy.deepcopy(frozen["messages"])
    trial.messages_for(frozen["messages"], "literal")
    assert frozen["messages"] == before
    with pytest.raises(ValueError):
        trial.messages_for(before, "unknown")
