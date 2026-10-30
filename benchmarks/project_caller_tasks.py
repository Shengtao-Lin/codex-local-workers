"""Previously exposed local contracts, now exercised by actual package callers."""

import ast

import host_block_transfer as HASH
import prepared_slice_trial as MESSAGE

SNAPSHOT = MESSAGE.I.BASE / "project-install-20261022-1/snapshot"

HASH_CALLERS = """
from types import SimpleNamespace
import pytest
from evaluation_harness.errors import ConflictError
from evaluation_harness.jobs.queue import submit_job

class Session:
    def __init__(self, existing=None):
        self.existing = existing
        self.added = []
        self.commits = 0
        self.refreshed = []

    async def scalar(self, _query):
        return self.existing

    def add(self, job):
        self.added.append(job)

    async def commit(self):
        self.commits += 1

    async def refresh(self, job):
        self.refreshed.append(job)

@pytest.mark.asyncio
async def test_volatile_request_reuses_original_job_without_writes():
    original = {"request_id": "old", "traceparent": "a", "body": {"dataset": "d"}}
    existing = SimpleNamespace(request_hash=request_hash(original), payload=original)
    session = Session(existing)
    incoming = {"request_id": "new", "traceparent": "b", "body": {"dataset": "d"}}
    result = await submit_job(session, job_type="example", idempotency_key="key", payload=incoming)
    assert result is existing and result.payload is original
    assert original["request_id"] == "old" and incoming["request_id"] == "new"
    assert session.added == [] and session.commits == 0 and session.refreshed == []

@pytest.mark.asyncio
async def test_meaningful_request_change_remains_conflict():
    existing = SimpleNamespace(request_hash=request_hash({"body": {"request_id": "old"}}))
    session = Session(existing)
    with pytest.raises(ConflictError, match="different request"):
        await submit_job(session, job_type="example", idempotency_key="key", payload={"body": {"request_id": "new"}})
    assert session.added == [] and session.commits == 0

@pytest.mark.asyncio
async def test_new_job_keeps_original_unfiltered_payload():
    session = Session()
    payload = {"request_id": "keep-in-storage", "traceparent": "keep-too", "x": 1}
    result = await submit_job(session, job_type="example", idempotency_key="key", payload=payload)
    assert result.payload is payload
    assert result.request_hash == request_hash({"x": 1})
    assert session.added == [result] and session.commits == 1 and session.refreshed == [result]
    assert payload == {"request_id": "keep-in-storage", "traceparent": "keep-too", "x": 1}
"""

MESSAGE_CALLERS = """
import copy
from evaluation_harness.adapters.base import AdapterContext
from evaluation_harness.adapters.generic_otel import GenericOtelAdapter
from evaluation_harness.canonical.models import CanonicalSample
from tests.conftest import load_trace

@pytest.mark.parametrize("row_mode", ["trace", "turn"])
def test_integer_zero_reaches_real_adapter_and_canonical_roundtrip(application, row_mode):
    trace = load_trace("generic_multi_turn.json")
    trace.raw = {"messages": [
        {"id": 0, "message_id": "ignored", "role": "user", "content": "question"},
        {"id": False, "message_id": 0, "role": "assistant", "content": "answer"},
    ]}
    before = copy.deepcopy(trace.raw)
    samples = GenericOtelAdapter().normalize(trace, context=AdapterContext(application=application, row_mode=row_mode))
    assert len(samples) == 1
    restored = CanonicalSample.model_validate_json(samples[0].model_dump_json())
    assert restored.input_messages[0].message_id == "0"
    assert restored.output_messages[0].message_id == "0"
    assert restored.input_messages[0].content[0].text == "question"
    assert restored.output_messages[0].content[0].text == "answer"
    assert trace.raw == before
"""


def join_test_sources(*parts):
    """Combine protected test modules, retaining top-level import placement."""
    imports, body = [], []
    for source in parts:
        lines = source.splitlines(keepends=True)
        for node in ast.parse(source).body:
            start = min(
                [node.lineno, *[d.lineno for d in getattr(node, "decorator_list", [])]]
            )
            fragment = "".join(lines[start - 1 : node.end_lineno])
            (
                imports if isinstance(node, (ast.Import, ast.ImportFrom)) else body
            ).append(fragment)
    return "\n".join([*dict.fromkeys(imports), *body]) + "\n"


def tasks():
    spec = HASH.tasks()["hash"]
    spec.update(
        target="src/evaluation_harness/jobs/queue.py",
        module="evaluation_harness.jobs.queue",
        public=join_test_sources(
            spec["public"]
            .replace("from product.code", "from evaluation_harness.jobs.queue")
            .replace(
                "from product.dependencies",
                "from evaluation_harness.canonical.fingerprint",
            ),
            HASH_CALLERS,
        ),
        private=spec["private"].replace(
            "from product.code", "from evaluation_harness.jobs.queue"
        ),
    )
    # Resolve the old Reviewer ambiguity explicitly without rewriting its score.
    spec["contract"] = spec["contract"].replace(
        "Ignored values must not be inspected or serialized.",
        "Ignored values must not undergo serialization, string conversion, equality/truth testing, or traversal. Iterating payload.items() and binding value references while filtering by key is permitted.",
    ) + (
        " Preserve submit_job unchanged: requests differing only in these fields reuse an existing job created under this same hash rule without writes; retained-field changes conflict, and new jobs keep the original unfiltered payload. "
        "This experiment does not migrate persisted hashes from older versions or test database concurrency."
    )
    message = {
        "target": "src/evaluation_harness/adapters/common.py",
        "module": "evaluation_harness.adapters.common",
        "symbol": MESSAGE.SYMBOL,
        "contract": MESSAGE.CONTRACT
        + " Existing parse_message/build_samples/GenericOtelAdapter callers must carry the supplied zero ID through trace and turn modes and CanonicalSample JSON round-trip; no caller changes.",
        "reference": MESSAGE.REFERENCE,
        "public": join_test_sources(
            MESSAGE.PUBLIC.replace(
                "from product.code", "from evaluation_harness.adapters.common"
            ),
            MESSAGE_CALLERS,
        ),
        "private": MESSAGE.PRIVATE.replace(
            "from product.code", "from evaluation_harness.adapters.common"
        ),
        "cases": [
            {"args": ["trace", 1, value], "kwargs": {}}
            for value in (
                {"id": 0, "message_id": "fallback"},
                {"id": False},
                {"message_id": 0},
                {"id": 0.0},
            )
        ],
    }
    return {"hash": spec, "message": message}
