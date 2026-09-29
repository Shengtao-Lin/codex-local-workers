"""Repeatable live v1 pipeline pilot on pinned, read-only source snapshots.

Only generated workspaces under benchmarks/work/stability-v1 are modified.
The two source repositories are checked by SHA-256 and never written.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import uuid
from dataclasses import dataclass
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
PLAN_VERSION = "v1.2"
WORK = KIT / "benchmarks" / "work" / "stability-v1"
SOURCES = {
    "harness": Path("F:/ChatGPT/agent-evaluation-harness"),
    "runtime": Path("F:/ChatGPT/agent-runtime-kit"),
}


@dataclass(frozen=True)
class Source:
    repository: str
    relative: str
    sha256: str


@dataclass(frozen=True)
class Mutation:
    target: str
    before: str
    after: str
    anchor: str


@dataclass(frozen=True)
class Case:
    name: str
    copies: tuple[Source, ...]
    target: str
    before: str
    after: str
    anchor: str
    behavior: str
    tests: str
    extra_mutations: tuple[Mutation, ...] = ()
    risk: str = "medium"
    contract_behaviors: tuple[str, ...] = ()
    contract_scenarios: tuple[str, ...] = ()
    implementation_guidance: tuple[str, ...] = ()
    baseline_static_rule: str | None = None


CASES = (
    Case(
        "selection-order",
        (
            Source(
                "harness",
                "src/evaluation_harness/contracts.py",
                "cd14b79ba672c367ad513c5ed81ea31996f592a62cee0846940d8c66c209f213",
            ),
            Source(
                "harness",
                "src/evaluation_harness/datasets/selection.py",
                "4c337d46d8a1c82b5ad7954f482545282477195c20eae7fd5de2a922b431a0ab",
            ),
        ),
        "src/evaluation_harness/datasets/selection.py",
        "            ordered.reverse()\n",
        "            pass\n",
        "def select_records",
        "For limit selection, newest order returns later timestamps first, oldest returns earlier timestamps first, and tied timestamps are deterministic by identity. Preserve other selection strategies.",
        """from datetime import datetime, timedelta, timezone

from evaluation_harness.contracts import SelectionPolicy
from evaluation_harness.datasets.selection import select_records


def test_newest_and_oldest():
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    rows = [("a", base), ("b", base + timedelta(days=1)), ("c", base + timedelta(days=2))]
    def choose(policy):
        return select_records(rows, policy, identity=lambda row: row[0], timestamp=lambda row: row[1])
    assert [row[0] for row in choose(SelectionPolicy(strategy="limit", limit=2, order="newest"))] == ["c", "b"]
    assert [row[0] for row in choose(SelectionPolicy(strategy="limit", limit=2, order="oldest"))] == ["a", "b"]


def test_tied_timestamp_is_deterministic():
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    rows = [("b", base), ("a", base)]
    result = select_records(rows, SelectionPolicy(strategy="limit", limit=2, order="newest"), identity=lambda row: row[0], timestamp=lambda row: row[1])
    assert [row[0] for row in result] == ["b", "a"]
""",
    ),
    Case(
        "mapping-metadata",
        (
            Source(
                "runtime",
                "src/agent_runtime/models.py",
                "608a31dd2a09692a380dfe5ba0d9eb97accb1f7420f6d47d1e96d454b7666577",
            ),
            Source(
                "runtime",
                "src/agent_runtime/adapters/mapping.py",
                "226ea47a005f6154be6dbabd097c39d03b4a7c37d328bd5f118c22f1d71619de",
            ),
        ),
        "src/agent_runtime/adapters/mapping.py",
        '    metadata_value = output_mapping.get("metadata", {})\n',
        "    metadata_value = {}\n",
        "def messages_output",
        "Mapping-shaped adapter output must preserve metadata entries while still validating message payloads and rejecting non-mapping metadata.",
        """import pytest

from agent_runtime.adapters.mapping import messages_output


MESSAGE = {"role": "assistant", "content": [{"type": "text", "text": "ready"}]}


def test_mapping_preserves_metadata():
    result = messages_output({"messages": [MESSAGE], "metadata": {"latency_ms": 7}}, None)
    assert result.messages[0].role == "assistant"
    assert result.metadata == {"latency_ms": 7}


def test_nonmapping_metadata_rejected():
    with pytest.raises(TypeError):
        messages_output({"messages": [MESSAGE], "metadata": "invalid"}, None)
""",
    ),
    Case(
        "metadata-limit",
        (
            Source(
                "runtime",
                "src/agent_runtime/models.py",
                "608a31dd2a09692a380dfe5ba0d9eb97accb1f7420f6d47d1e96d454b7666577",
            ),
        ),
        "src/agent_runtime/models.py",
        "MAX_METADATA_BYTES = 16_384\n",
        "MAX_METADATA_BYTES = 163_840\n",
        "MAX_METADATA_BYTES = 163_840",
        "Metadata validation and the exported MAX_METADATA_BYTES constant must agree on 16,384 encoded bytes, while allowing small JSON-compatible values and rejecting non-JSON values.",
        """import pytest

from agent_runtime import models
from agent_runtime.models import MAX_METADATA_BYTES, validate_metadata


def test_metadata_byte_limit():
    assert MAX_METADATA_BYTES == 16_384
    with pytest.raises(ValueError, match="16384|16_384"):
        validate_metadata({"payload": "x" * 16_384})


def test_small_and_nonjson():
    assert validate_metadata({"enabled": True}) == {"enabled": True}
    with pytest.raises(ValueError, match="JSON-compatible"):
        validate_metadata({"bad": object()})


def test_validator_uses_exported_limit(monkeypatch):
    monkeypatch.setattr(models, "MAX_METADATA_BYTES", 32)
    with pytest.raises(ValueError, match="32"):
        validate_metadata({"payload": "x" * 32})
""",
        contract_behaviors=(
            "MAX_METADATA_BYTES is the single authoritative 16_384-byte threshold, and validate_metadata uses it for comparison and the error message.",
            "Small JSON-compatible metadata remains valid; non-JSON-compatible values still raise ValueError.",
        ),
    ),
    Case(
        "reviewer-citation",
        (
            Source(
                "runtime",
                "src/agent_runtime/models.py",
                "608a31dd2a09692a380dfe5ba0d9eb97accb1f7420f6d47d1e96d454b7666577",
            ),
        ),
        "src/agent_runtime/models.py",
        "MAX_METADATA_BYTES = 16_384\n",
        "MAX_METADATA_BYTES = 163_840\n",
        "MAX_METADATA_BYTES = 163_840",
        "Metadata validation must reject a JSON-encoded object once its compact UTF-8 representation exceeds exactly 16,384 bytes; small JSON-compatible values remain valid.",
        """import pytest

from agent_runtime.models import validate_metadata


def test_exact_metadata_boundary():
    assert validate_metadata({"payload": "x"}) == {"payload": "x"}
    with pytest.raises(ValueError, match="16384|16_384"):
        validate_metadata({"payload": "x" * 16_384})
""",
        risk="high",
        contract_behaviors=(
            "The exported MAX_METADATA_BYTES declaration equals exactly 16_384.",
            "validate_metadata compares the compact UTF-8 JSON byte length with MAX_METADATA_BYTES, rejects values above it with a ValueError containing the configured limit, and preserves small JSON-compatible metadata.",
        ),
    ),
    Case(
        "internal-trace",
        (
            Source(
                "harness",
                "src/evaluation_harness/telemetry/classification.py",
                "c51df87a65c3d6082114c8a88c63694f6a2c6d1720a7c52855bfa89dc5b5dd0d",
            ),
        ),
        "src/evaluation_harness/telemetry/classification.py",
        "        or service_name in internal_services\n",
        "        or service_name not in internal_services\n",
        "def is_internal_trace",
        "Internal traces are detected only by explicit evaluator attributes or configured internal service names; unrelated external services remain external.",
        """from evaluation_harness.telemetry.classification import is_internal_trace


def test_explicit_internal_signals():
    assert is_internal_trace({"attributes": {"evaluation.internal": True}})
    assert is_internal_trace({"metadata": {"evaluation.source": "worker"}})
    assert is_internal_trace({"resource": {"service.name": "custom-evaluator"}}, service_names={"custom-evaluator"})


def test_external_service_is_not_internal():
    assert not is_internal_trace({"resource": {"service.name": "customer-api"}})
    assert not is_internal_trace({"attributes": {"evaluation.internal": False}})
""",
        contract_behaviors=(
            "An explicit evaluation.internal=True attribute is sufficient even when no service name is present.",
            "An explicit evaluation.source of evaluator, worker, or api is sufficient even when no service name is present; service-name membership must not qualify this signal.",
            "A configured internal service name is independently sufficient, while an unrelated service with no explicit signal remains external.",
        ),
        contract_scenarios=(
            "A trace carrying only evaluation.internal=True is internal.",
            "A trace carrying only metadata evaluation.source=worker is internal.",
            "A trace carrying only a configured internal service name is internal; an unrelated service is external.",
        ),
    ),
    Case(
        "sample-identity",
        (
            Source(
                "harness",
                "src/evaluation_harness/canonical/models.py",
                "dbc74e1036dc06c09956e6f55e964d1a33aba71454e52b5104b72ef236bfe54f",
            ),
            Source(
                "harness",
                "src/evaluation_harness/canonical/fingerprint.py",
                "41dbf6f9ccd329539a6eaee9e65e06a5aebdd459571c51579c8beab87be5fe4b",
            ),
            Source(
                "harness",
                "src/evaluation_harness/evaluations/dedup.py",
                "5b36d5e4e845a61d28d810ef098eb2c3dc7d0e33093e164a05d19e2698e8ce3a",
            ),
            Source(
                "harness",
                "src/evaluation_harness/scorers/base.py",
                "4fae31c1ae997e592180f579dfc10b7e2b2c0853958e45bb44aaa023fd365aba",
            ),
            Source(
                "harness",
                "src/evaluation_harness/contracts.py",
                "cd14b79ba672c367ad513c5ed81ea31996f592a62cee0846940d8c66c209f213",
            ),
        ),
        "src/evaluation_harness/canonical/fingerprint.py",
        '    content = sample.model_dump(mode="json", exclude=VOLATILE_CONTENT_FIELDS)\n',
        '    content = sample.model_dump(mode="json")\n',
        'content = sample.model_dump(mode="json")',
        "Changing only sample_id must not change content_fingerprint or score_reuse_key, and mapping order must remain deterministic. score_reuse_key must still include source_metadata as scoring input, so changing source_metadata must change that key.",
        """from datetime import UTC, datetime

from evaluation_harness.canonical.fingerprint import content_fingerprint
from evaluation_harness.canonical.models import CanonicalMessage, CanonicalSample, HumanLabel, RuntimeMetadata, TextPart
from evaluation_harness.contracts import ScorerContract
from evaluation_harness.evaluations.dedup import score_reuse_key


class FakeScorer:
    scorer_id = "stable"
    version = "1.0.0"
    scorer_type = "code"
    contract = ScorerContract(
        scorer_id="stable",
        version="1.0.0",
        display_name="Stable",
        scorer_type="code",
        input_schema={},
        output_schema={},
        implementation_digest="sha256:" + "0" * 64,
    )


def sample(sample_id):
    return CanonicalSample(
        sample_id=sample_id,
        application_id="agent",
        environment="test",
        source_trace_id="trace-1",
        event_time=datetime(2026, 1, 1, tzinfo=UTC),
        input_messages=[CanonicalMessage(message_id="i", role="user", content=[TextPart(text="Hi")])],
        output_messages=[CanonicalMessage(message_id="o", role="assistant", content=[TextPart(text="Hello")])],
        runtime=RuntimeMetadata(),
    )


def test_content_fingerprint_ignores_row_identity():
    assert content_fingerprint(sample("row-1")) == content_fingerprint(sample("row-2"))


def test_content_fingerprint_ignores_existing_volatile_fields():
    original = sample("row-1")
    changed = original.model_copy(
        update={"sample_id": "row-2", "labels": [HumanLabel(label="priority", value=True, source="human")], "source_metadata": {"model": "other"}}
    )
    assert content_fingerprint(original) == content_fingerprint(changed)


def test_score_reuse_key_ignores_row_identity_and_mapping_order():
    scorer = FakeScorer()
    assert score_reuse_key(sample("row-1"), scorer, {"b": 2, "a": 1}) == score_reuse_key(sample("row-2"), scorer, {"a": 1, "b": 2})


def test_score_reuse_key_preserves_source_metadata_as_scoring_input():
    scorer = FakeScorer()
    original = sample("row-1")
    changed = original.model_copy(update={"source_metadata": {"model": "other"}})
    assert score_reuse_key(original, scorer) != score_reuse_key(changed, scorer)


def test_fingerprint_ignores_source_metadata_but_reuse_key_preserves_it():
    scorer = FakeScorer()
    original = sample("row-1")
    changed = original.model_copy(update={"source_metadata": {"model": "other"}})
    assert content_fingerprint(original) == content_fingerprint(changed)
    assert score_reuse_key(original, scorer) != score_reuse_key(changed, scorer)


def test_fingerprint_ignores_labels_but_reuse_key_preserves_them():
    scorer = FakeScorer()
    original = sample("row-1")
    changed = original.model_copy(update={"labels": [HumanLabel(label="priority", value=True, source="human")]})
    assert content_fingerprint(original) == content_fingerprint(changed)
    assert score_reuse_key(original, scorer) != score_reuse_key(changed, scorer)
""",
        (
            Mutation(
                "src/evaluation_harness/evaluations/dedup.py",
                '        "sample": sample.model_dump(mode="json", exclude={"sample_id"}),\n',
                '        "sample": sample.model_dump(mode="json"),\n',
                '"sample": sample.model_dump(mode="json"),',
            ),
        ),
        contract_behaviors=(
            "content_fingerprint excludes the existing VOLATILE_CONTENT_FIELDS from the serialized sample before canonical hashing; do not invent mapping-order fields.",
            "score_reuse_key excludes only sample_id from the serialized sample. It must preserve source_metadata and every other scoring-relevant sample field.",
            "score_reuse_key retains the existing schema version, scorer id/version/contract, and effective_config in its payload; mapping order is normalized by sorted-key JSON serialization.",
            "score_reuse_key returns the existing sha256:<hex digest> shape and keeps the non-cacheable scorer guard unchanged.",
        ),
        contract_scenarios=(
            "Changing only sample_id leaves both content_fingerprint and score_reuse_key unchanged.",
            "Changing source_metadata leaves content_fingerprint unchanged but changes score_reuse_key.",
            "Changing labels leaves content_fingerprint unchanged but changes score_reuse_key.",
            "Reordering effective_config keys leaves score_reuse_key unchanged.",
        ),
        implementation_guidance=(
            "The failing test name uses row_identity as a concept, not a model field: CanonicalSample defines sample_id and no row_identity field. The observed fingerprint module already defines VOLATILE_CONTENT_FIELDS containing sample_id; use that existing constant for content_fingerprint. In score_reuse_key exclude only the actual sample_id field so source_metadata remains scoring input. Each faulty model_dump call occupies one source line. Prefer changing only that call on each file, preserving the surrounding payload, hashing, guards, and return formats. For SAFE_REPLACE, use an exact short current line rather than a whole function; after a miss, reread the target line before retrying. SAFE_REPLACE_LINE accepts exactly one replacement line, never a multiline block.",
        ),
    ),
    Case(
        "scorer-unused-binding",
        (
            Source(
                "harness",
                "src/evaluation_harness/contracts.py",
                "cd14b79ba672c367ad513c5ed81ea31996f592a62cee0846940d8c66c209f213",
            ),
            Source(
                "harness",
                "src/evaluation_harness/canonical/models.py",
                "dbc74e1036dc06c09956e6f55e964d1a33aba71454e52b5104b72ef236bfe54f",
            ),
            Source(
                "harness",
                "src/evaluation_harness/scorers/base.py",
                "4fae31c1ae997e592180f579dfc10b7e2b2c0853958e45bb44aaa023fd365aba",
            ),
            Source(
                "harness",
                "src/evaluation_harness/scorers/deterministic.py",
                "6d193404055b2e624c271cb59cf1f13ae0ca2155195bb77aca770c024b3dc6da",
            ),
        ),
        "src/evaluation_harness/scorers/deterministic.py",
        "        present = bool(sample.output_messages and sample.output_messages[0].content)\n",
        "        stale_output = None\n"
        "        present = bool(sample.output_messages and sample.output_messages[0].content)\n",
        "async def score",
        "Remove the unused local binding flagged by Ruff F841 in OutputPresentScorer.score while preserving present/absent output scores, labels, and rationale.",
        """import asyncio
from types import SimpleNamespace

from evaluation_harness.scorers.deterministic import OutputPresentScorer


class ObservedSample:
    def __init__(self, messages):
        self.messages = messages
        self.reads = 0

    @property
    def output_messages(self):
        self.reads += 1
        return self.messages


def test_present_output_scores_one():
    sample = ObservedSample([SimpleNamespace(content=["hello"])])
    result = asyncio.run(OutputPresentScorer().score(sample))
    assert (result.score, result.label) == (1.0, "pass")
    assert result.rationale == "The sample contains an assistant output."
    assert sample.reads <= 2


def test_absent_output_scores_zero():
    sample = ObservedSample([])
    result = asyncio.run(OutputPresentScorer().score(sample))
    assert (result.score, result.label) == (0.0, "fail")
    assert result.rationale == "No output was captured."
    assert sample.reads <= 1
""",
        contract_behaviors=(
            "The unused local binding in OutputPresentScorer.score is removed without changing score, label, or rationale for present and absent outputs.",
            "The changed source passes the project's Ruff format and lint checks, including F841.",
            "The scorer must not add redundant reads of sample.output_messages: at most two for a present output and one for an absent output.",
        ),
        contract_scenarios=(
            "A present output produces score 1.0 and label pass without extra output_messages reads.",
            "An absent output produces score 0.0 and label fail without extra output_messages reads.",
        ),
        baseline_static_rule="F841",
    ),
    Case(
        "selection-percentage",
        (
            Source(
                "harness",
                "src/evaluation_harness/contracts.py",
                "cd14b79ba672c367ad513c5ed81ea31996f592a62cee0846940d8c66c209f213",
            ),
            Source(
                "harness",
                "src/evaluation_harness/datasets/selection.py",
                "4c337d46d8a1c82b5ad7954f482545282477195c20eae7fd5de2a922b431a0ab",
            ),
        ),
        "src/evaluation_harness/datasets/selection.py",
        "    threshold = int((policy.percentage or 0) * 100)\n",
        "    threshold = int((policy.percentage or 0) * 10)\n",
        "def select_records",
        "Percentage selection compares the first 64 bits of SHA-256(seed:identity) modulo 10,000 against percentage times 100; 100 percent selects every eligible record, and results do not depend on input order.",
        """import hashlib
from datetime import datetime, timezone

from evaluation_harness.contracts import SelectionPolicy
from evaluation_harness.datasets.selection import select_records


def selected(rows, percentage):
    return select_records(
        rows,
        SelectionPolicy(strategy="percentage", seed=11, percentage=percentage),
        identity=lambda row: row,
        timestamp=lambda row: datetime(2025, 1, 1, tzinfo=timezone.utc),
    )


def expected(rows, percentage):
    threshold = int(percentage * 100)
    return [
        row for row in rows
        if int.from_bytes(hashlib.sha256(f"11:{row}".encode()).digest()[:8], "big") % 10_000 < threshold
    ]


def test_half_percentage_uses_ten_thousand_bucket_scale():
    rows = [f"row-{number}" for number in range(100)]
    assert selected(rows, 50) == expected(rows, 50)


def test_full_percentage_includes_every_row():
    rows = [f"row-{number}" for number in range(20)]
    assert selected(rows, 100) == rows
""",
    ),
    Case(
        "metadata-key-length",
        (
            Source(
                "runtime",
                "src/agent_runtime/models.py",
                "608a31dd2a09692a380dfe5ba0d9eb97accb1f7420f6d47d1e96d454b7666577",
            ),
        ),
        "src/agent_runtime/models.py",
        "        if not key or len(key) > 128:\n",
        "        if not key or len(key) > 1024:\n",
        "def validate_metadata",
        "Metadata keys must contain 1–128 characters; a 128-character key is valid, empty and 129-character keys are rejected, and the encoded-byte limit remains in force.",
        """import pytest

from agent_runtime.models import validate_metadata


def test_key_length_boundary():
    assert validate_metadata({"x" * 128: 1}) == {"x" * 128: 1}
    with pytest.raises(ValueError, match="128"):
        validate_metadata({"x" * 129: 1})


def test_empty_key_is_rejected():
    with pytest.raises(ValueError, match="128"):
        validate_metadata({"": 1})


def test_encoded_byte_limit_still_applies():
    with pytest.raises(ValueError, match="16384|16_384"):
        validate_metadata({"payload": "x" * 16_384})
""",
    ),
    Case(
        "selection-random-seed",
        (
            Source(
                "harness",
                "src/evaluation_harness/contracts.py",
                "cd14b79ba672c367ad513c5ed81ea31996f592a62cee0846940d8c66c209f213",
            ),
            Source(
                "harness",
                "src/evaluation_harness/datasets/selection.py",
                "4c337d46d8a1c82b5ad7954f482545282477195c20eae7fd5de2a922b431a0ab",
            ),
        ),
        "src/evaluation_harness/datasets/selection.py",
        "        random.Random(policy.seed).shuffle(ordered)\n",
        "        random.Random(policy.seed or 7).shuffle(ordered)\n",
        "def select_records",
        "Random selection sorts by identity, shuffles the whole list with exactly policy.seed including valid seed 0, and then applies the limit. Nonzero seeds and input-order independence remain intact.",
        """from datetime import datetime, timezone
from random import Random

from evaluation_harness.contracts import SelectionPolicy
from evaluation_harness.datasets.selection import select_records


def choose(rows, seed):
    return select_records(
        rows,
        SelectionPolicy(strategy="random", seed=seed, limit=3),
        identity=lambda row: row,
        timestamp=lambda row: datetime(2025, 1, 1, tzinfo=timezone.utc),
    )


def expected(seed):
    rows = list("abcdefghij")
    Random(seed).shuffle(rows)
    return rows[:3]


def test_zero_seed_uses_zero_not_fallback():
    assert choose(list("jihgfedcba"), 0) == expected(0)


def test_nonzero_seed_and_input_order():
    assert choose(list("abcdefghij"), 7) == expected(7)
    assert choose(list("jihgfedcba"), 7) == expected(7)
        """,
    ),
    Case(
        "guardrail-casefold",
        (
            Source(
                "runtime",
                "src/agent_runtime/errors.py",
                "816b4db2a9e569429901df290acb30dad45b362002ce1a4a934f2afc65267e7a",
            ),
            Source(
                "runtime",
                "src/agent_runtime/models.py",
                "608a31dd2a09692a380dfe5ba0d9eb97accb1f7420f6d47d1e96d454b7666577",
            ),
            Source(
                "runtime",
                "src/agent_runtime/hooks/__init__.py",
                "b4771a39421a7cccefda34a2c7bbfbef42320ed1e8368663f352f9805557d11c",
            ),
            Source(
                "runtime",
                "src/agent_runtime/hooks/base.py",
                "396b410b87db527636ce6ea042a699632be8c14bdba41aaac7797201b313d1e9",
            ),
            Source(
                "runtime",
                "src/agent_runtime/hooks/guardrails.py",
                "3b02c3bc76b265330c3c1e95bec0aacf8efc8ceee9f4c1ad8d3df80e95159581",
            ),
            Source(
                "runtime",
                "src/agent_runtime/telemetry/__init__.py",
                "10e97be492dd0a800ca1a18e4788a6d3498b93c4601ecae1467b5edf0aa257bb",
            ),
            Source(
                "runtime",
                "src/agent_runtime/telemetry/tracing.py",
                "eab9a9b40ab1cf8f684e81caf7d175d0c91c0efda3fb4953b07bb978ea656f8a",
            ),
        ),
        "src/agent_runtime/hooks/guardrails.py",
        "                    text = part.text.casefold()\n",
        "                    text = part.text\n",
        "class PhraseBlockGuardrail",
        "PhraseBlockGuardrail matches configured non-empty phrases against text case-insensitively after trimming and normalization. Mixed-case matching blocks with configured_phrase; unrelated text remains allowed, and empty phrase sets are rejected.",
        """import asyncio
from uuid import uuid4

import pytest

from agent_runtime.hooks.guardrails import PhraseBlockGuardrail
from agent_runtime.models import Message, RuntimeContext, TextContent


def evaluate(guardrail, text):
    context = RuntimeContext(run_id=uuid4(), thread_id=uuid4())
    message = Message(role="user", content=[TextContent(text=text)])
    return asyncio.run(guardrail.evaluate([message], context=context))


def test_mixed_case_phrase_blocks():
    guardrail = PhraseBlockGuardrail(["  ForBiDdEn  "])
    result = evaluate(guardrail, "This contains fOrBiDdEn material")
    assert result.allowed is False
    assert result.reason_code == "configured_phrase"
    assert evaluate(guardrail, "FORBIDDEN").allowed is False


def test_nonmatching_text_remains_allowed():
    assert evaluate(PhraseBlockGuardrail(["forbidden"]), "ordinary text").allowed is True


def test_empty_phrase_configuration_is_rejected():
    with pytest.raises(ValueError, match="non-empty"):
        PhraseBlockGuardrail(["  "])
""",
        contract_behaviors=(
            "Configured phrases are trimmed and case-folded; every TextContent part is case-folded before substring matching, and a match returns allowed=False with reason_code configured_phrase.",
            "Nonmatching text remains allowed and an all-empty configured phrase set raises ValueError.",
        ),
        contract_scenarios=(
            "Mixed-case configured phrases match mixed-case message text and block.",
            "A nonmatching message remains allowed and an empty phrase set is rejected.",
        ),
        risk="high",
    ),
    Case(
        "mapping-message-sequence",
        (
            Source(
                "runtime",
                "src/agent_runtime/models.py",
                "608a31dd2a09692a380dfe5ba0d9eb97accb1f7420f6d47d1e96d454b7666577",
            ),
            Source(
                "runtime",
                "src/agent_runtime/adapters/mapping.py",
                "226ea47a005f6154be6dbabd097c39d03b4a7c37d328bd5f118c22f1d71619de",
            ),
        ),
        "src/agent_runtime/adapters/mapping.py",
        "    if not isinstance(raw_messages, Sequence) or isinstance(raw_messages, (str, bytes)):\n",
        "    if not isinstance(raw_messages, Sequence):\n",
        "def messages_output",
        "Mapping adapter output requires a sequence of message objects, not a bare string or bytes. Invalid message-container shapes raise TypeError; each supplied element must be validated rather than filtered or silently discarded.",
        """import pytest
from pydantic import ValidationError

from agent_runtime.adapters.mapping import messages_output


MESSAGE = {"role": "assistant", "content": [{"type": "text", "text": "ready"}]}


@pytest.mark.parametrize("value", ["hello", b"hello", 42])
def test_invalid_message_containers_raise_type_error(value):
    with pytest.raises(TypeError, match="message sequence"):
        messages_output({"messages": value}, None)


def test_sequence_of_messages_still_maps():
    result = messages_output({"messages": [MESSAGE]}, None)
    assert result.messages[0].role == "assistant"
    assert result.messages[0].content[0].text == "ready"


def test_invalid_element_is_not_silently_dropped():
    with pytest.raises(ValidationError):
        messages_output({"messages": [MESSAGE, "not-a-message"]}, None)
""",
        contract_behaviors=(
            "The messages field must be a sequence that is not a bare str or bytes; invalid container shapes raise TypeError.",
            "Validate every element in order with Message validation; an invalid element raises rather than being silently filtered out, and valid messages remain in the result.",
        ),
        contract_scenarios=(
            "A bare string or bytes messages value raises TypeError.",
            "A sequence with a valid message followed by an invalid element is rejected rather than truncated.",
            "A valid message sequence maps to InvocationOutput.",
        ),
        risk="high",
    ),
)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def prepare(
    case: Case, root: Path, source_config: dict, *, packet_name: str = "packet.json"
) -> tuple[Path, Path]:
    if packet_name not in {"packet.json", "packet-draft.json"}:
        raise ValueError("unsupported packet output name")
    root.mkdir(parents=True, exist_ok=False)
    for source in case.copies:
        original = SOURCES[source.repository] / source.relative
        raw = original.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != source.sha256:
            raise ValueError(f"source snapshot changed: {original} ({digest})")
        destination = root / source.relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
    mutations = (
        Mutation(case.target, case.before, case.after, case.anchor),
        *case.extra_mutations,
    )
    for mutation in mutations:
        target = root / mutation.target
        text = target.read_text(encoding="utf-8")
        if text.count(mutation.before) != 1:
            raise ValueError(f"fixture injection anchor changed: {mutation.target}")
        target.write_text(
            text.replace(mutation.before, mutation.after, 1), encoding="utf-8"
        )
    for directory in (root / "src").rglob("*"):
        if directory.is_dir() and not (directory / "__init__.py").exists():
            (directory / "__init__.py").write_text("", encoding="utf-8")
    (root / "tests").mkdir()
    test_path = root / "tests" / f"test_{case.name.replace('-', '_')}.py"
    test_path.write_text(case.tests, encoding="utf-8")
    (root / "conftest.py").write_text(
        "import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).parent / 'src'))\n",
        encoding="utf-8",
    )
    formatted = run_command(
        root, [sys.executable, "-m", "ruff", "format", "src", "tests"], 90
    )
    if formatted.returncode != 0:
        raise ValueError(
            f"fixture formatting failed: {formatted.stdout}{formatted.stderr}"
        )
    normalized_imports = run_command(
        root,
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--select",
            "I",
            "--fix",
            "src",
            "tests",
        ],
        90,
    )
    if normalized_imports.returncode != 0:
        raise ValueError(
            f"fixture import normalization failed: {normalized_imports.stdout}{normalized_imports.stderr}"
        )
    lint = run_command(
        root, [sys.executable, "-m", "ruff", "check", "src", "tests"], 90
    )
    if case.baseline_static_rule is not None:
        lint_json = run_command(
            root,
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                "--output-format",
                "json",
                "src",
                "tests",
            ],
            90,
        )
        try:
            issues = json.loads(lint_json.stdout)
        except ValueError as exc:
            raise ValueError(f"fixture lint output is not JSON: {case.name}") from exc
        if (
            lint_json.returncode == 0
            or not isinstance(issues, list)
            or len(issues) != 1
            or issues[0].get("code") != case.baseline_static_rule
            or Path(str(issues[0].get("filename"))).resolve()
            != (root / case.target).resolve()
        ):
            raise ValueError(
                f"fixture needs exactly one {case.baseline_static_rule} in "
                f"{case.target}: {lint_json.stdout}{lint_json.stderr}"
            )
    elif lint.returncode != 0:
        raise ValueError(f"fixture lint failed: {lint.stdout}{lint.stderr}")
    # Copy only distributable kit files. The installer rejects nested targets by design.
    sys.path.insert(0, str(KIT / "scripts"))
    from install_local_agents import inventory

    for relative in inventory(KIT):
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(KIT / relative, destination)
    config = {
        **source_config,
        "python": sys.executable,
        "explorer_required_citation_paths": [
            *dict.fromkeys(mutation.target for mutation in mutations),
            test_path.relative_to(root).as_posix(),
        ],
        "require_edit_targets": True,
        "max_local_repairs": (
            max(3, int(source_config.get("max_local_repairs", 2)))
            if case.name == "sample-identity"
            else int(source_config.get("max_local_repairs", 2))
        ),
        "reviewer_require_approved_execution": case.risk == "high",
        "validation_profiles": {
            "stability-strict": {
                "python": sys.executable,
                "compile": True,
                "pytest_argv": ["-B", "-m", "pytest"],
                "commands": [
                    {
                        "id": "ruff-format",
                        "argv": [
                            "{python}",
                            "-m",
                            "ruff",
                            "format",
                            "--check",
                            "src",
                            "tests",
                        ],
                    },
                    {
                        "id": "ruff-check",
                        "argv": ["{python}", "-m", "ruff", "check", "src", "tests"],
                    },
                ],
            }
        },
    }
    config_path = root / ".local-agents" / "config.json"
    write_json(config_path, config)
    behavior_texts = case.contract_behaviors or (case.behavior,)
    behavior_ids = [f"behavior-{index}" for index in range(1, len(behavior_texts) + 1)]
    scenario_texts = case.contract_scenarios or (
        "The main behavior matches the contract.",
        "The focused boundary or error path matches the contract.",
    )
    packet = {
        "schema_version": 2,
        "task_id": f"stability-{case.name}",
        "feature_id": f"stability-{case.name}",
        "unit_id": case.name,
        "run_id": f"{case.name}-a1",
        "attempt": 1,
        "plan_revision": 1,
        "packet_revision": 1,
        "goal": case.behavior,
        "risk": {
            "feature": case.risk,
            "unit": case.risk,
            "integration": case.risk,
            "reasons": [
                "Isolated copied real-code behavior with protected acceptance tests."
            ],
        },
        "dependencies": [],
        "owned_contract_ids": behavior_ids,
        "scope": {
            "read": ["src", "tests", "conftest.py"],
            "readonly": [test_path.relative_to(root).as_posix()],
            "modify": [mutation.target for mutation in mutations],
            "create": [],
            "forbidden": [],
        },
        "edit_targets": [
            {"path": mutation.target, "anchor": mutation.anchor}
            for mutation in mutations
        ],
        "required_behavior": [
            {"id": behavior_id, "text": text, "risk_floor": case.risk}
            for behavior_id, text in zip(behavior_ids, behavior_texts, strict=True)
        ],
        "acceptance_criteria": [
            {"id": "focused-tests", "text": "Protected focused tests pass."},
            {"id": "static", "text": "Ruff format and lint pass."},
        ],
        "acceptance_scenarios": [
            {
                "id": f"scenario-{index}",
                "text": text,
                "observables": {"protected_test_assertion": True},
            }
            for index, text in enumerate(scenario_texts, 1)
        ],
        "implementation_guidance": list(case.implementation_guidance),
        "validation_profile": "stability-strict",
        "focused_tests": [test_path.relative_to(root).as_posix()],
    }
    packet_path = root / ".agent" / packet_name
    write_json(packet_path, packet)
    write_json(
        root / "fixture-source.json",
        [
            {
                "path": item.relative,
                "sha256": item.sha256,
                "source_repository": item.repository,
            }
            for item in case.copies
        ],
    )
    return config_path, packet_path


def run_command(
    root: Path, argv: list[str], timeout: int
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def read_events(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def explorer_has_line_evidence(report: dict, case: Case, test_path: str) -> bool:
    if report.get("explorer_mode") == "locate":
        return localization_has_relevant_evidence(report, case, test_path)
    observed = set(report.get("evidence_summary", {}).get("observed_files", []))
    targets = {case.target, *(mutation.target for mutation in case.extra_mutations)}
    if not targets | {test_path} <= observed:
        return False
    cited_text = unicodedata.normalize(
        "NFKC",
        "\n".join(
            str(item)
            for item in [*report.get("findings", []), *report.get("call_flow", [])]
        ),
    )
    clauses = re.split(r"(?<=[.!?])\s+|\n", cited_text)
    return all(
        any(
            re.search(rf"(?<![\w./]){re.escape(path)}(?![\w./])", clause)
            and re.search(r"\blines?\s*\d+|:\d+\b", clause, re.IGNORECASE)
            for clause in clauses
        )
        for path in targets | {test_path}
    )


def localization_has_relevant_evidence(
    report: dict, case: Case, test_path: str
) -> bool:
    """Score locations against held-out fixture mutations, never send these oracles to models."""
    refs = report.get("source_refs", [])
    if (
        not isinstance(refs, list)
        or not refs
        or report.get("semantic_verdict") != "not_evaluated"
    ):
        return False
    if any(not isinstance(ref, dict) for ref in refs):
        return False
    mutations = (
        Mutation(case.target, case.before, case.after, case.anchor),
        *case.extra_mutations,
    )
    for mutation in mutations:
        # Formatting is normalized by fixture preparation; preserve token/text identity.
        expected = " ".join(mutation.after.split())
        if not any(
            ref.get("path") == mutation.target
            and ref.get("kind") == "implementation"
            and expected in " ".join(str(ref.get("quote", "")).split())
            for ref in refs
        ):
            return False
    return any(
        ref.get("path") == test_path
        and ref.get("kind") == "test"
        and (
            "assert " in str(ref.get("quote", ""))
            or "pytest.raises(" in str(ref.get("quote", ""))
        )
        for ref in refs
    )


def full_explorer_report(root: Path, compact: dict) -> dict:
    diagnostic = compact.get("diagnostic_report")
    if not isinstance(diagnostic, str):
        return compact
    path = (root / diagnostic).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        return compact
    return {**compact, **json.loads(path.read_text(encoding="utf-8"))}


def explorer_task(case: Case, test_path: str, mode: str = "investigate") -> str:
    mutations = (
        Mutation(case.target, case.before, case.after, case.anchor),
        *case.extra_mutations,
    )
    reads = [mutation.target for mutation in mutations]
    if case.name == "sample-identity":
        reads.append("src/evaluation_harness/canonical/models.py")
    reads.append(test_path)
    requested_reads = " and ".join(f"READ_FILE {path}" for path in reads)
    anchors = ", ".join(mutation.anchor for mutation in mutations)
    if mode == "locate":
        required_paths = ", ".join(mutation.target for mutation in mutations)
        return (
            f"{requested_reads}. Locate the implementation of {anchors} and the "
            "focused test assertions that exercise it. Select observed source_refs "
            "covering each relevant controlling branch or value and the assertions, "
            f"including these implementation files: {required_paths}. Other source reads "
            "are context, not mandatory references. Use implementation/test "
            "kinds accurately. Return locations, not predicted results or a repair. "
            "Use SEARCH for symbols when a file exceeds a read window."
        )
    if mode != "investigate":
        raise ValueError("unknown Explorer task mode")
    question = (
        f"{requested_reads}. Answer only this: which exact source branch or branches "
        f"of {anchors} control the focused behavior? Cite observed source and test "
        "lines. For each distinct focused assertion in the observed tests, "
        "substitute its concrete input into the relevant branch conditions, "
        "state the source-predicted result and the asserted result, and say "
        "whether they conflict; include boundary and error cases, not just "
        "one convenient positive or negative example. In FINISH_SUCCESS, "
        "put each source and test citation in findings or call_flow as the full "
        "path followed by line N; put the observed test path in relevant_tests "
        "and use nonempty strings in findings. Trace past an outer type guard into subsequent "
        "conversion or validation, including the exact exception type; a guard "
        "passing does not establish that the test passes. "
        "Explicitly separate source prediction, test expectation, and any "
        "actually executed result; do not say an assertion passes unless "
        "execution evidence was provided. A defective implementation is a successful investigation "
        "when you identify its observed lines, so use FINISH_SUCCESS with that "
        "evidence. Do not SEARCH for these known paths as text."
    )
    if case.name == "sample-identity":
        question += (
            " Specifically determine whether the current content_fingerprint and "
            "score_reuse_key dumps actually exclude sample_id. Check the "
            "CanonicalSample field definition and the exact model_dump arguments; "
            "a VOLATILE_CONTENT_FIELDS constant is not proof it is used."
        )
    if case.name == "mapping-message-sequence":
        question += (
            " Specifically evaluate the test's str and bytes message containers "
            "at the Sequence guard and then at per-element Message.model_validate; "
            "distinguish the actual exception type from the asserted TypeError."
        )
    if case.baseline_static_rule:
        question += (
            f" This fixture's baseline failure is Ruff {case.baseline_static_rule}, "
            "not a pytest assertion. Identify the exact source line and reason "
            "for that static-check failure while separately noting what the "
            "focused tests establish."
        )
    return question


def looks_like_infra_failure(*values: object) -> bool:
    text = " ".join(str(value or "") for value in values).lower()
    return any(
        marker in text
        for marker in (
            "http ",
            "http error",
            "context window",
            "context length",
            "timed out",
            "timeout",
            "deadline exhausted",
            "lm studio request failed",
            "lmstudio_unavailable",
            "empty assistant message",
            "unexpected response shape",
        )
    )


def context_summary(events: list[dict]) -> dict:
    requests = []
    for event in events:
        facts = event.get("facts", {})
        stats = (
            facts
            if event.get("event") == "model_request"
            else facts.get("model_request")
        )
        if isinstance(stats, dict) and stats.get("context_length"):
            requests.append(stats)
    if not requests:
        return {"requests": 0}
    return {
        "requests": len(requests),
        "context_length": requests[0].get("context_length"),
        "max_estimated_input_tokens": max(
            int(item.get("estimated_input_tokens", 0)) for item in requests
        ),
        "max_reported_input_tokens": max(
            (
                int(item["reported_input_tokens"])
                for item in requests
                if "reported_input_tokens" in item
            ),
            default=None,
        ),
        "min_estimated_remaining_tokens": min(
            int(item.get("estimated_remaining_tokens", 0)) for item in requests
        ),
        "max_estimated_context_utilization": max(
            float(item.get("estimated_context_utilization", 0)) for item in requests
        ),
        "max_reported_context_utilization": max(
            (
                float(item["reported_context_utilization"])
                for item in requests
                if "reported_context_utilization" in item
            ),
            default=None,
        ),
    }


def archive_metrics(root: Path, case: Case) -> dict:
    task = root / ".agent" / "tasks" / f"stability-{case.name}"
    coder_events = read_events(task / "runs" / f"{case.name}-a1" / "events.jsonl")
    failed_validation_positions = [
        index
        for index, event in enumerate(coder_events)
        if event.get("event") == "tool_action"
        and event.get("facts", {}).get("action") == "VALIDATE"
        and event.get("facts", {}).get("status") == "failed"
    ]
    repairs_to_edit = 0
    for position in failed_validation_positions:
        next_actions = [
            event.get("facts", {}).get("action")
            for event in coder_events[position + 1 :]
            if event.get("event") == "tool_action"
        ]
        if next_actions and next_actions[0] in {
            "SAFE_CREATE",
            "SAFE_REPLACE",
            "SAFE_REPLACE_LINE",
        }:
            repairs_to_edit += 1
    first_repair_immediate_edit = int(
        bool(failed_validation_positions)
        and next(
            (
                event.get("facts", {}).get("action")
                for event in coder_events[failed_validation_positions[0] + 1 :]
                if event.get("event") == "tool_action"
            ),
            None,
        )
        in {"SAFE_CREATE", "SAFE_REPLACE", "SAFE_REPLACE_LINE"}
    )
    review_events = []
    for path in (task / "reviews").glob("*/events.jsonl"):
        review_events.extend(read_events(path))
    review_report: dict = {}
    review_report_path = root / ".agent" / "last-local-review-report.json"
    if review_report_path.is_file():
        review_report = json.loads(review_report_path.read_text(encoding="utf-8-sig"))
        if isinstance(review_report.get("model_request"), dict):
            review_events.append(
                {"event": "model_request", "facts": review_report["model_request"]}
            )
    citation_rounds = sum(
        event.get("event") == "protocol_error"
        and "source_quote" in str(event.get("facts", {}).get("error", ""))
        for event in review_events
    )
    explorer_events = []
    for path in (root / ".agent" / "explorer-runs").glob("*/events.jsonl"):
        explorer_events.extend(read_events(path))
    return {
        "plan_version": PLAN_VERSION,
        "failed_validation_actions": len(failed_validation_positions),
        "next_action_is_edit": repairs_to_edit,
        "first_repair_next_action_is_edit": first_repair_immediate_edit,
        "repair_gate_rejections": sum(
            event.get("event") == "repair_action_rejected" for event in coder_events
        ),
        "repair_focus_issued": sum(
            event.get("event") == "repair_focus_issued" for event in coder_events
        ),
        "repair_target_selected": sum(
            bool(event.get("facts", {}).get("required_paths"))
            for event in coder_events
            if event.get("event") == "repair_focus_issued"
        ),
        "repair_path_rejections": sum(
            event.get("event") == "repair_path_rejected" for event in coder_events
        ),
        "repair_supervision_nudge_issued": sum(
            event.get("event") == "repair_supervision_nudge_issued"
            for event in coder_events
        ),
        "prior_read_restored_after_repair_nudge": sum(
            event.get("event") == "repair_context_compacted"
            and event.get("facts", {}).get("restored_prior_read") is True
            for event in coder_events
        ),
        "validated_terminal_gate_entered": sum(
            event.get("event") == "validated_terminal_nudge_issued"
            for event in coder_events
        ),
        "post_validation_action_rejected": sum(
            event.get("event") == "validated_terminal_nudge_issued"
            for event in coder_events
        ),
        "terminal_nudge_issued": sum(
            event.get("event") == "validated_terminal_nudge_issued"
            for event in coder_events
        ),
        "runtime_finalized_after_terminal_nudge": sum(
            event.get("event") == "validated_terminal_runtime_finalized"
            for event in coder_events
        ),
        "repair_focus_next_action_has_new_evidence": sum(
            event.get("event") == "repair_evidence_action_allowed"
            for event in coder_events
        ),
        "citation_required": case.risk == "high",
        "citation_fix_rounds": citation_rounds,
        "citation_converged": bool(review_report.get("contract_review"))
        and review_report.get("decision") in {"pass_to_primary", "rework", "escalate"},
        "citation_converged_after_fix": citation_rounds > 0
        and review_report.get("decision") in {"pass_to_primary", "rework", "escalate"},
        "reviewer_protocol_errors": sum(
            event.get("event") == "protocol_error" for event in review_events
        ),
        "context": {
            "explorer": context_summary(explorer_events),
            "coder": context_summary(coder_events),
            "reviewer": context_summary(review_events),
        },
    }


def run_case(case: Case, root: Path, source_config: dict) -> dict:
    config_path, packet_path = prepare(case, root, source_config)
    test_path = f"tests/test_{case.name.replace('-', '_')}.py"
    collection = run_command(
        root,
        [sys.executable, "-m", "pytest", test_path, "--collect-only", "-q"],
        90,
    )
    if collection.returncode != 0 or "no tests collected" in collection.stdout.lower():
        raise ValueError(
            "fixture test collection failed before the injected behavior could be "
            f"measured: {case.name}\n{collection.stdout}{collection.stderr}"
        )
    baseline = run_command(root, [sys.executable, "-m", "pytest", test_path, "-q"], 90)
    if case.baseline_static_rule is None:
        if baseline.returncode == 0:
            raise ValueError(f"fixture test baseline unexpectedly passes: {case.name}")
    elif baseline.returncode != 0:
        raise ValueError(
            f"static-only fixture tests must pass before repair: {case.name}\n"
            f"{baseline.stdout}{baseline.stderr}"
        )
    started = time.perf_counter()
    explorer_path = root / ".agent" / "explorer-report.json"
    explorer = run_command(
        root,
        [
            sys.executable,
            str(root / ".local-agents" / "local-explore.py"),
            "--task",
            explorer_task(
                case, test_path, source_config.get("explorer_mode", "investigate")
            ),
            "--task-id",
            f"stability-{case.name}",
            "--config",
            str(config_path),
            "--report",
            str(explorer_path),
        ],
        600,
    )
    explorer_report = (
        json.loads(explorer_path.read_text(encoding="utf-8"))
        if explorer_path.is_file()
        else {}
    )
    explorer_full_path = None
    diagnostic_report = explorer_report.get("diagnostic_report")
    if isinstance(diagnostic_report, str):
        candidate = (root / diagnostic_report).resolve()
        if candidate.is_relative_to(root.resolve()) and candidate.is_file():
            explorer_full_path = str(candidate)
    unit = run_command(
        root,
        [
            sys.executable,
            str(root / ".local-agents" / "local-unit.py"),
            "--packet",
            str(packet_path),
            "--config",
            str(config_path),
        ],
        1200,
    )
    elapsed = round(time.perf_counter() - started, 2)
    coder_path = root / ".agent" / "last-local-coder-report.json"
    coder = (
        json.loads(coder_path.read_text(encoding="utf-8"))
        if coder_path.is_file()
        else {}
    )
    try:
        handoff = json.loads(unit.stdout)
    except ValueError:
        handoff = {}
    independent = run_command(
        root, [sys.executable, "-m", "pytest", test_path, "-q"], 90
    )
    independent_format = run_command(
        root, [sys.executable, "-m", "ruff", "format", "--check", "src", "tests"], 90
    )
    independent_lint = run_command(
        root, [sys.executable, "-m", "ruff", "check", "src", "tests"], 90
    )
    result = {
        "plan_version": PLAN_VERSION,
        "case": case.name,
        "workspace": str(root),
        "baseline_failed": baseline.returncode != 0
        or case.baseline_static_rule is not None,
        "baseline_failure_kind": "ruff" if case.baseline_static_rule else "pytest",
        "explorer_exit": explorer.returncode,
        "explorer_status": explorer_report.get("status"),
        "explorer_failure_reason": explorer_report.get("failure_reason"),
        "explorer_evidence_valid": explorer_has_line_evidence(
            full_explorer_report(root, explorer_report), case, test_path
        ),
        "explorer_report": str(explorer_path),
        "explorer_full_report": explorer_full_path,
        "explorer_compact_findings_truncated": explorer_report.get(
            "findings_truncated"
        ),
        "unit_exit": unit.returncode,
        "coder_status": coder.get("status"),
        "coder_failure_reason": coder.get("failure_reason"),
        "reviewer_decision": handoff.get("reviewer_decision"),
        "handoff_stage": handoff.get("stage"),
        "handoff_reason": handoff.get("reason"),
        "independent_tests_passed": independent.returncode == 0,
        "independent_format_passed": independent_format.returncode == 0,
        "independent_lint_passed": independent_lint.returncode == 0,
        "independent_test_tail": independent.stdout[-500:],
        "wall_seconds": elapsed,
        "agent_dir": str(root / ".agent"),
        "unit_output_tail": (unit.stdout + unit.stderr)[-800:],
        "metrics": archive_metrics(root, case),
    }
    result["infra_failure"] = looks_like_infra_failure(
        result["explorer_failure_reason"],
        result["coder_failure_reason"],
        result["handoff_reason"],
        result["unit_output_tail"],
    )
    result["qualified_pass"] = (
        result["explorer_status"] == "success"
        and result["explorer_evidence_valid"]
        and result["coder_status"] == "ready_for_review"
        and result["reviewer_decision"] == "pass_to_primary"
        and result["independent_tests_passed"]
        and result["independent_format_passed"]
        and result["independent_lint_passed"]
    )
    write_json(root / "stability-result.json", result)
    return result


def unreachable_role_aligned_gate(results: list[dict], planned: int) -> str | None:
    """Name a failed 90% gate only when no future result can repair its count."""
    remaining = planned - len(results)
    minimum = math.ceil(0.9 * planned)
    explorer = sum(
        item.get("explorer_status") == "success"
        and item.get("explorer_evidence_valid") is True
        for item in results
    )
    if explorer + remaining < minimum:
        return f"Explorer evidence can reach at most {explorer + remaining}/{planned}"
    qualified = sum(item.get("qualified_pass") is True for item in results)
    if qualified + remaining < minimum:
        return f"protocol E2E can reach at most {qualified + remaining}/{planned}"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run pinned local v1.2 E2E stability cases"
    )
    parser.add_argument(
        "--config", type=Path, default=KIT / ".local-agents" / "config.json"
    )
    parser.add_argument("--cases", default=",".join(case.name for case in CASES))
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument(
        "--stop-when-unreachable",
        action="store_true",
        help="Stop a two-round role-aligned candidate once a 90% gate is impossible.",
    )
    parser.add_argument("--explorer-model")
    parser.add_argument(
        "--explorer-mode", choices=("investigate", "locate"), default="investigate"
    )
    parser.add_argument("--coder-model")
    parser.add_argument("--coder-context-length", type=int)
    parser.add_argument("--reviewer-model")
    args = parser.parse_args()
    if not 1 <= args.rounds <= 5:
        parser.error("--rounds must be between 1 and 5")
    selected = set(args.cases.split(","))
    if selected - {case.name for case in CASES}:
        parser.error(
            f"unknown cases: {sorted(selected - {case.name for case in CASES})}"
        )
    if args.stop_when_unreachable and (args.rounds != 2 or len(selected) < 11):
        parser.error("--stop-when-unreachable needs two rounds of at least 11 cases")
    planned = len(selected) * args.rounds
    source_config = json.loads(args.config.read_text(encoding="utf-8-sig"))
    source_config["explorer_mode"] = args.explorer_mode
    source_config.setdefault(
        "model_context_lengths",
        {
            source_config.get("explorer_model", "explorer"): 32768,
            source_config.get("coder_model", "coder"): 24576,
            source_config.get("reviewer_model", "reviewer"): 24576,
        },
    )
    if args.reviewer_model:
        source_config["reviewer_model"] = args.reviewer_model
    if args.explorer_model:
        source_config["explorer_model"] = args.explorer_model
    if args.coder_model:
        source_config["coder_model"] = args.coder_model
    context_lengths = source_config["model_context_lengths"]
    if args.coder_context_length:
        source_config["coder_context_length"] = args.coder_context_length
        context_lengths[source_config["coder_model"]] = args.coder_context_length
    for role in ("explorer", "coder", "reviewer"):
        model = source_config.get(f"{role}_model")
        if model in context_lengths:
            source_config.setdefault(f"{role}_context_length", context_lengths[model])
    batch = WORK / f"batch-{uuid.uuid4().hex[:12]}"
    frozen_inputs = candidate_inputs(source_config)
    write_json(batch / "candidate-inputs.json", frozen_inputs)
    results = []
    for number in range(1, args.rounds + 1):
        for case in CASES:
            if case.name not in selected:
                continue
            result = run_case(
                case, batch / f"round-{number}" / case.name, source_config
            )
            results.append(result)
            print(json.dumps(result, ensure_ascii=False), flush=True)
            write_json(
                batch / "summary.json",
                {
                    "schema_version": 1,
                    "plan_version": PLAN_VERSION,
                    "results": results,
                },
            )
            stop_marker = batch / "STOP_REQUESTED"
            inputs_changed = candidate_inputs(source_config) != frozen_inputs
            if args.stop_when_unreachable or stop_marker.is_file() or inputs_changed:
                reason = (
                    "Runtime/runner inputs changed during the candidate"
                    if inputs_changed
                    else "Primary requested stop at a completed-case boundary: "
                    + stop_marker.read_text(encoding="utf-8")[:1000]
                    if stop_marker.is_file()
                    else unreachable_role_aligned_gate(results, planned)
                )
                if reason is not None:
                    write_json(
                        batch / "summary.json",
                        {
                            "schema_version": 1,
                            "plan_version": PLAN_VERSION,
                            "results": results,
                            "stopped_early": True,
                            "planned_cells": planned,
                            "stop_reason": reason,
                        },
                    )
                    print(
                        json.dumps(
                            {
                                "batch": str(batch),
                                "decision": "NO-GO",
                                "completed_cells": len(results),
                                "planned_cells": planned,
                                "stop_reason": reason,
                            },
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )
                    return 1
    explorer_successes = sum(
        item["explorer_status"] == "success" and item["explorer_evidence_valid"]
        for item in results
    )
    coder_successes = sum(
        item["coder_status"] == "ready_for_review" for item in results
    )
    reviewer_valid_reports = sum(
        item["reviewer_decision"] in {"pass_to_primary", "rework", "escalate"}
        for item in results
    )
    e2e_passes = sum(item["qualified_pass"] for item in results)
    print(
        json.dumps(
            {
                "batch": str(batch),
                "plan_version": PLAN_VERSION,
                "cases": len(results),
                "explorer_successes": explorer_successes,
                "explorer_success_rate": round(explorer_successes / len(results), 4),
                "ready_for_review": coder_successes,
                "coder_success_rate": round(coder_successes / len(results), 4),
                "reviewer_valid_reports": reviewer_valid_reports,
                "reviewer_valid_report_rate": round(
                    reviewer_valid_reports / len(results), 4
                ),
                "reviewer_passes": sum(
                    item["reviewer_decision"] == "pass_to_primary" for item in results
                ),
                "e2e_passes": e2e_passes,
                "e2e_pass_rate": round(e2e_passes / len(results), 4),
                "infra_failures": sum(item["infra_failure"] for item in results),
                "reviewer_model": source_config.get("reviewer_model"),
                "model_context_lengths": source_config.get("model_context_lengths"),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return (
        0
        if all(
            item["explorer_status"] == "success"
            and item["unit_exit"] == 0
            and item["independent_tests_passed"]
            for item in results
        )
        else 1
    )


def candidate_inputs(source_config: dict) -> dict:
    paths = [
        "benchmarks/stability_e2e.py",
        "benchmarks/localization_readiness.py",
        "benchmarks/v1_2_readiness.py",
        "benchmarks/explorer_semantic_audit.py",
        ".local-agents/explorer-runtime.py",
        ".local-agents/worker-runtime.py",
        ".local-agents/reviewer-runtime.py",
        ".local-agents/local-unit.py",
        ".local-agents/run-state.py",
        ".local-agents/safe-edit.py",
        ".local-agents/evidence-cache.py",
        ".local-agents/task-policy.py",
    ]
    return {
        "schema_version": 1,
        "explorer_mode": source_config.get("explorer_mode", "investigate"),
        "models": {
            role: source_config.get(f"{role}_model")
            for role in ("explorer", "coder", "reviewer")
        },
        "config_sha256": hashlib.sha256(
            json.dumps(source_config, sort_keys=True).encode()
        ).hexdigest(),
        "files": {
            path: hashlib.sha256((KIT / path).read_bytes()).hexdigest()
            for path in paths
        },
    }


if __name__ == "__main__":
    raise SystemExit(main())
