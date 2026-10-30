"""Failing evidence priority must reorder only, never add or omit model facts."""

import copy
import json
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "benchmarks"))
sys.path.insert(0, str(KIT / ".local-agents"))
from bounded import compatibility_profile as C
from bounded import literal_check_feedback as L
from bounded import static_focus_rules as R
from failure_priority_entry import prioritize


@pytest.mark.parametrize("cell", ["message-id-1", "message-id-2"])
@pytest.mark.parametrize("request_index", [1, 2, 3, 4])
def test_all_actual_request_facts_preserved_and_same_size(cell, request_index):
    name = "prepared-slice-live-20261022-1"
    identity = name + "-" + cell
    root = (
        KIT / "benchmarks/work/harness-convergence" / name / "cells" / cell / "isolated"
    )
    path = (
        root
        / ".agent/tasks"
        / identity
        / "runs"
        / identity
        / f"proposal-request-{request_index}.json"
    )
    text = json.loads(path.read_text(encoding="utf-8"))["messages"][1]["content"]
    # Static-focused requests have a bounded JSON diagnostic before the main facts.
    body = text[text.index('{"goal":') :]
    facts = L.restore(body)
    original = copy.deepcopy(facts)
    reordered = prioritize(facts)
    assert reordered == facts == original
    assert next(iter(reordered)) == "validation_failure"
    assert next(iter(reordered["validation_failure"])) == "focused_tests"
    old, new = L.render(facts), L.render(reordered)
    assert L.restore(old) == L.restore(new) == original
    assert len(old) == len(new)
    assert sorted(old) == sorted(new)
    module = C.proposal_rules({"bounded_compatibility_profile": "flat-v1"}, R)
    assert len(module.render(facts)) == len(module.render(reordered))
    assert module.SCHEMA["properties"]["content"]["type"] == "string"


def test_no_failed_check_keeps_original_object():
    value = {"validation_failure": {"status": "passed"}}
    assert prioritize(value) is value
