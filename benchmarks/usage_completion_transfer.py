"""A new real-source behavior with protected exact upstream dependency bodies."""

import argparse
from pathlib import Path

import prepared_task_matrix as M

S, T, P = M.S, M.T, M.P
BATCH = P.I.BASE / "usage-completion-transfer-20261022-1"
ORDER = ["usage-1", "usage-2"]
UPSTREAM = Path("F:/ChatGPT/agent-runtime-kit/src/agent_runtime")
CONTRACT = (
    "Extend token_usage(raw, input_key, output_key) to derive exactly one unknown directional "
    "count from raw['total_tokens'] when possible. Continue using token_count for supplied "
    "directional values, preserving its exact validation/errors. If both input/output counts "
    "are known, preserve them and ignore total_tokens even when inconsistent or invalid. "
    "If both are unknown, return None without using total_tokens. If exactly one is unknown "
    "(absent or None), validate total_tokens through token_count; an absent/None total leaves "
    "the result unknown (None). Otherwise derive unknown=total-known; negative derived counts "
    "raise ProviderError('Model returned invalid usage', retryable=False), not clamping/coercion. "
    "Zero is a known count. Return Usage only when both nonnegative counts are known. "
    "Keep arbitrary input_key/output_key behavior, raw None -> None, non-Mapping rejection, "
    "and validation of supplied invalid directional counts even when the other side is missing. "
    "Do not mutate or normalize raw or its values. Preserve signature/imports, token_count, "
    "Usage/StrictModel/error classes and tests; no external effects."
)
REFERENCE = '''def token_usage(raw: object, input_key: str, output_key: str) -> Usage | None:
    """Complete one unknown directional count when a valid total is supplied."""
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise ProviderError("Model returned invalid usage", retryable=False)
    counts = cast(Mapping[str, object], raw)
    input_tokens = token_count(counts.get(input_key))
    output_tokens = token_count(counts.get(output_key))
    if input_tokens is None:
        if output_tokens is None:
            return None
        total = token_count(counts.get("total_tokens"))
        if total is None:
            return None
        input_tokens = total - output_tokens
    elif output_tokens is None:
        total = token_count(counts.get("total_tokens"))
        if total is None:
            return None
        output_tokens = total - input_tokens
    if input_tokens < 0 or output_tokens < 0:
        raise ProviderError("Model returned invalid usage", retryable=False)
    return Usage(input_tokens=input_tokens, output_tokens=output_tokens)
'''
PUBLIC = """import pytest
from product.code import ProviderError, token_usage

@pytest.mark.parametrize(("raw", "expected"), [
    ({"in": 3, "total_tokens": 10}, (3, 7)),
    ({"out": 4, "total_tokens": 10}, (6, 4)),
    ({"in": 0, "out": None, "total_tokens": 0}, (0, 0)),
    ({"in": None, "out": 0, "total_tokens": 3}, (3, 0)),
    ({"in": 2, "out": 5, "total_tokens": False}, (2, 5)),
])
def test_completion(raw, expected):
    usage = token_usage(raw, "in", "out")
    assert usage is not None
    assert (usage.input_tokens, usage.output_tokens) == expected

@pytest.mark.parametrize("raw", [None, {}, {"total_tokens": 9}, {"in": 3}, {"in": 3, "total_tokens": None}])
def test_remains_unknown(raw):
    assert token_usage(raw, "in", "out") is None

@pytest.mark.parametrize("raw", [{"in": 6, "total_tokens": 4}, {"out": 0, "total_tokens": False}, {"in": False}, []])
def test_invalid(raw):
    with pytest.raises(ProviderError) as caught:
        token_usage(raw, "in", "out")
    assert str(caught.value) == "Model returned invalid usage"
    assert caught.value.retryable is False
"""
PRIVATE = """import copy
from types import MappingProxyType
import pytest
from product.code import ProviderError, token_usage

@pytest.mark.parametrize("known_side", ["prompt", "completion"])
def test_custom_keys_zero_and_nonmutation(known_side):
    for known in [0, 1, 7, 10000]:
        for extra in [0, 2, 10000]:
            raw = {known_side: known, "total_tokens": known + extra, "extra": {"kept": [1]}}
            before = copy.deepcopy(raw)
            usage = token_usage(MappingProxyType(raw), "prompt", "completion")
            expected = (known, extra) if known_side == "prompt" else (extra, known)
            assert usage is not None
            assert (usage.input_tokens, usage.output_tokens) == expected
            assert raw == before

@pytest.mark.parametrize("raw", [{"in": 0, "out": 0}, {"in": 1, "out": 2}, {"in": None, "out": None}, {}])
def test_unused_total_is_not_validated(raw):
    for ignored in [False, -1, 1.5, "9", [], {}]:
        source = {**raw, "total_tokens": ignored}
        usage = token_usage(source, "in", "out")
        if raw.get("in") is None:
            assert usage is None
        else:
            assert usage is not None
            assert (usage.input_tokens, usage.output_tokens) == (raw["in"], raw["out"])

@pytest.mark.parametrize("side", ["in", "out"])
def test_invalid_directional_values_still_raise(side):
    for bad in [False, -1, 1.0, "1", [], {}]:
        with pytest.raises(ProviderError) as caught:
            token_usage({side: bad, "total_tokens": 10}, "in", "out")
        assert str(caught.value) == "Model returned invalid usage"
        assert caught.value.retryable is False

@pytest.mark.parametrize("side", ["in", "out"])
def test_invalid_total_only_when_needed(side):
    for bad in [False, -1, 1.0, "1", [], {}]:
        with pytest.raises(ProviderError) as caught:
            token_usage({side: 0, "total_tokens": bad}, "in", "out")
        assert caught.value.retryable is False
    with pytest.raises(ProviderError):
        token_usage({side: 10, "total_tokens": 9}, "in", "out")

def test_same_requested_key_retains_original_behavior():
    usage = token_usage({"same": 0, "total_tokens": "ignored"}, "same", "same")
    assert usage is not None
    assert usage.input_tokens == usage.output_tokens == 0
"""


def prepare(used):
    assert (
        S.read(P.I.BASE / "mixed-static-matrix-20261022-1/decision.json")["accepted"]
        == 4
    )
    origins = {
        "canonical": UPSTREAM / "models_clients/_canonical.py",
        "models": UPSTREAM / "models.py",
        "errors": UPSTREAM / "errors.py",
    }
    hashes = {name: S.sha(path) for name, path in origins.items()}
    header = "from __future__ import annotations\nfrom collections.abc import Mapping\nfrom typing import cast\nfrom pydantic import BaseModel, ConfigDict, Field\n\n"
    for name, symbol in (
        ("errors", "RuntimeKitError"),
        ("errors", "ProviderError"),
        ("models", "StrictModel"),
        ("models", "Usage"),
        ("canonical", "token_count"),
    ):
        header += T.extract(origins[name], symbol) + "\n\n"
    spec = {
        "header": header,
        "symbol": "token_usage",
        "contract": CONTRACT,
        "start": T.extract(origins["canonical"], "token_usage"),
        "reference": REFERENCE,
        "public": PUBLIC,
        "private": PRIVATE,
        "cases": [
            {"args": [{"in": 0, "total_tokens": 3}, "in", "out"], "kwargs": {}},
            {
                "args": [{"in": 2, "out": 5, "total_tokens": False}, "in", "out"],
                "kwargs": {},
            },
            {"args": [{"total_tokens": 8}, "in", "out"], "kwargs": {}},
        ],
        "risk_rationale": "Public count/error compatibility spans several conditions; high-risk invariant. Exact upstream helper/model/error bodies are protected, only token_usage can change.",
        "scenarios": [
            {
                "id": "normal",
                "text": "Complete exactly one missing count from valid total",
            },
            {
                "id": "boundary",
                "text": "Known zeros, untouched known/both-unknown values, arbitrary keys and immutable Mapping",
            },
            {
                "id": "error",
                "text": "Preserved directional/Mapping errors, needed total errors and negative derived count",
            },
        ],
    }
    material = M.template(BATCH, "usage", spec)
    assert all(S.sha(path) == hashes[name] for name, path in origins.items())
    for name, path in origins.items():
        T.write(BATCH / "origins" / (name + ".py"), path.read_text(encoding="utf-8"))
    rows = {
        label: M.cell(BATCH, label, "usage", spec, material, Path(__file__))
        for label in ORDER
    }
    S.save(BATCH / "cells.json", rows)
    S.save(
        BATCH / "registration.json",
        {
            "feature_id": "real-usage-completion",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "owned_contract_ids": ["usage"],
            "dependencies": ["mixed-static-matrix-20261022-1"],
            "registered": 2,
            "order": ORDER,
            "candidate": "Current installed bounded-v1/flat-v1 with diagnostic parity fixes; original Reviewer, no research/observation extension.",
            "exposure": "New behavior on a real frozen sibling function;2repeats of1task, not2independent tasks. No post-hoc prompt change.",
            "origin": {
                name: {"path": str(path), "sha256": hashes[name]}
                for name, path in origins.items()
            },
            "isolation": "Exact token_usage/helper/error/model class bodies extracted; imports consolidated so all protected dependencies visible in the one module. Not a whole-sibling application integration test. Original files read-only.",
            "contract": CONTRACT,
            "budget": "C12requests/3edits/3write checks/1initial/12preparations/2protocol recoveries/900s; R16requests/4errors/4096output/600s;2220spercell/5400batch; no Primary hints or new tests during run.",
            "models": {
                "coder": "qwen/qwen3-coder-30b",
                "reviewer": "meta/muse-glimmer",
                "single_residency": True,
            },
            "roles_not_used": "Explorer: target already located. Coordinator: one cohesive task. No extrapolation of their ability.",
            "gate": "2/2 current complete checks, fresh Reviewer and Primary full source/diff acceptance, no drift/assistance/unsafe behavior. One failure HOLD; ordinary failure still finishes fixed diagnostic pair.",
            "stop": "Safety, infrastructure, input drift, fixed time or user stop. No unregistered retries or failure replacement.",
            "Primary_cost": "Contract/public-private tests/reference and preparation are Primary authored. No Primary-only comparison or measured cloud savings. Active time unknown; no code assistance to live Worker.",
            "weekly_used_start": used,
            "weekly_cap": None,
            "pins": M.pins(
                BATCH,
                Path(__file__),
                material[1],
                *[BATCH / "origins" / (name + ".py") for name in origins],
            ),
        },
    )
    print("Two new usage-completion cells frozen; no live yet")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "run"])
    parser.add_argument("--cell", choices=ORDER)
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.weekly_used)
    else:
        P.BATCH, P.ORDER = BATCH, ORDER
        P.run(args.cell, args.weekly_used)
