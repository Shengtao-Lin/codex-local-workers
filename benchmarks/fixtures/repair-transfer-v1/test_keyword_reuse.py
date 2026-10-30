"""One contract across scoring and cache identity, including rejection boundaries."""

import asyncio
import hashlib
import json

import pytest
from conftest import make_sample

from evaluation_harness.canonical.models import CanonicalSample
from evaluation_harness.evaluations.dedup import score_reuse_key
from evaluation_harness.scorers.base import Scorer
from evaluation_harness.scorers.deterministic import ExpectedKeywordScorer, OutputPresentScorer
from evaluation_harness.scorers.judge import FakeJudgeScorer


def legacy_key(sample: CanonicalSample, scorer: Scorer, config: dict[str, object]) -> str:
    payload = {
        "schema_version": 1,
        "sample": sample.model_dump(mode="json", exclude={"sample_id"}),
        "scorer": {
            "scorer_id": scorer.scorer_id,
            "version": scorer.version,
            "contract": scorer.contract.model_dump(mode="json"),
        },
        "effective_config": config,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@pytest.mark.parametrize(
    ("facts", "expected_score", "label", "status"),
    [
        ([" Straße ", "", "blue"], 0.5, "partial", "succeeded"),
        ([" hit", "hit ", "  "], 1.0, "pass", "succeeded"),
        (["\t", ""], None, None, "skipped"),
        ([], None, None, "skipped"),
        (["strasse", "absent"], 0.5, "partial", "succeeded"),
        (["STR ASSE"], 0.0, "partial", "succeeded"),
    ],
)
def test_normalized_facts_control_scoring_and_denominator(
    facts: list[str], expected_score: float | None, label: str | None, status: str
) -> None:
    sample = make_sample(facts=facts)
    before = sample.model_dump()
    result = asyncio.run(ExpectedKeywordScorer().score(sample))
    assert (result.score, result.label, result.status) == (expected_score, label, status)
    assert sample.model_dump() == before


@pytest.mark.parametrize(
    ("raw", "normalized"),
    [
        ([" Straße ", "", "blue"], ["Straße", "blue"]),
        ([" hit", "hit ", "\t"], ["hit", "hit"]),
        (["", " "], []),
    ],
)
def test_score_and_reuse_key_roundtrip_normalization(raw: list[str], normalized: list[str]) -> None:
    first = make_sample(facts=raw)
    second = make_sample(facts=normalized)
    scorer = ExpectedKeywordScorer()
    before = first.model_dump()
    assert asyncio.run(scorer.score(first)) == asyncio.run(scorer.score(second))
    assert score_reuse_key(first, scorer) == legacy_key(second, scorer, {})
    assert score_reuse_key(first, scorer) == score_reuse_key(second, scorer)
    assert first.model_dump() == before


def test_unrelated_scorers_keep_exact_legacy_identity() -> None:
    sample = make_sample(facts=[" hit ", ""])
    scorer = OutputPresentScorer()
    assert score_reuse_key(sample, scorer) == legacy_key(sample, scorer, {})
    assert score_reuse_key(sample, scorer) != score_reuse_key(make_sample(facts=["hit"]), scorer)


def test_absent_expectations_remain_distinct_and_supported() -> None:
    sample = make_sample()
    scorer = ExpectedKeywordScorer()
    assert score_reuse_key(sample, scorer) == legacy_key(sample, scorer, {})
    assert score_reuse_key(sample, scorer) != score_reuse_key(make_sample(facts=[]), scorer)
    assert asyncio.run(scorer.score(sample)).status == "skipped"


def test_other_identity_dimensions_and_config_still_invalidate() -> None:
    sample = make_sample(facts=[" hit ", ""])
    scorer = ExpectedKeywordScorer()
    key = score_reuse_key(sample, scorer)
    assert key != score_reuse_key(sample, scorer, {"threshold": 0.5})
    assert key != score_reuse_key(sample.model_copy(update={"source_revision": "2"}), scorer)
    assert key != score_reuse_key(make_sample(facts=["hit", "hit"]), scorer)
    assert key != score_reuse_key(make_sample(facts=["HIT"]), scorer)
    assert key == score_reuse_key(sample.model_copy(update={"sample_id": "other"}), scorer)


def test_unsafe_scorers_remain_ineligible() -> None:
    class Noncacheable(ExpectedKeywordScorer):
        contract = ExpectedKeywordScorer.contract.model_copy(update={"cacheable": False})

    class VersionTwo(ExpectedKeywordScorer):
        version = "2.0.0"
        contract = ExpectedKeywordScorer.contract.model_copy(update={"version": "2.0.0"})

    sample = make_sample(facts=[" hit "])
    assert score_reuse_key(sample, Noncacheable()) is None
    assert score_reuse_key(sample, FakeJudgeScorer()) is None
    assert score_reuse_key(sample, VersionTwo()) != score_reuse_key(sample, ExpectedKeywordScorer())
