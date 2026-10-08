"""Versioned complex goals. Reference repairs belong only to Primary tests."""

from __future__ import annotations

import copy


def extend(corpus):
    corpus = copy.deepcopy(corpus)
    corpus["coverage_revision"] = "complex-v2"
    bounded = corpus["cases"][0]
    bounded["files"]["tests/test_config.py"] += """

@pytest.mark.parametrize("value", ["２", "٢", "¹", "1\\n", [], {}, 2.0])
def test_non_ascii_and_coercion_rejected(value):
    with pytest.raises(ValueError):
        parse_limit(value)
"""
    corpus["cases"].append(transaction_case())
    sql = corpus["cases"][1]
    service_tests = sql["files"]["tests/test_service.py"]
    start = service_tests.index("        class Result:")
    end = service_tests.index("        return Result()", start) + len(
        "        return Result()"
    )
    sql["files"]["tests/test_service.py"] = (
        (
            service_tests[:start]
            + "        return self.connection.execute(statement)"
            + service_tests[end:]
        )
        .replace(
            "import pytest\n",
            "import pytest\nfrom sqlalchemy import create_engine\nfrom product.query import metadata\n",
        )
        .replace(
            "        self.present = present\n",
            '        self.engine = create_engine("sqlite://")\n'
            "        metadata.create_all(self.engine)\n"
            "        self.connection = self.engine.connect()\n"
            "        self.present = present\n",
        )
    )
    return corpus


def transaction_case():
    return {
        "case_id": "atomic-evidence-publish",
        "origin": "primary-authored",
        "goal": "Publish copied evidence under a lease atomically; expose an isolated summary.",
        "feature_risk": "high",
        "integration_risk": "high",
        "files": {
            "src/product/__init__.py": "",
            "src/product/evidence.py": """def copy_evidence(source, run_id):
    return dict(source, run_id=run_id, reused_from=source["run_id"])
""",
            "src/product/publish.py": """from product.evidence import copy_evidence


async def publish(store, source, run_id, lease):
    evidence = copy_evidence(source, run_id)
    await store.write(evidence)
    await store.commit()
    return evidence
""",
            "src/product/summary.py": """def summary(records, run_id):
    return records
""",
            "tests/test_publish.py": """import asyncio
from copy import deepcopy

import pytest

from product.publish import publish


class Store:
    def __init__(self, valid=True, fail=None):
        self.valid = valid
        self.fail = fail
        self.events = []
        self.staged = None
        self.saved = None

    async def check_lease(self, lease):
        self.events.append(("lease", lease))
        return self.valid

    async def write(self, evidence):
        self.events.append(("write", None))
        self.staged = deepcopy(evidence)
        if self.fail == "write":
            raise OSError("write failed")

    async def commit(self):
        self.events.append(("commit", None))
        if self.fail == "commit":
            raise OSError("commit failed")
        self.saved = self.staged

    async def rollback(self):
        self.events.append(("rollback", None))
        self.staged = None


def source():
    return {"run_id": "old", "status": "succeeded", "cacheable": True,
            "evidence": {"scores": [1, 2], "metadata": {"version": "v1"}}}


def test_publish_copies_complete_evidence_and_orders_lease():
    original = source()
    snapshot = deepcopy(original)
    store = Store()
    result = asyncio.run(publish(store, original, "new", "lease-1"))
    assert [event[0] for event in store.events] == ["lease", "write", "commit"]
    assert store.events[0][1] == "lease-1"
    assert result == dict(snapshot, run_id="new", reused_from="old")
    result["evidence"]["scores"].append(99)
    result["evidence"]["metadata"]["version"] = "changed"
    assert original == snapshot
    assert store.saved == dict(snapshot, run_id="new", reused_from="old")


def test_invalid_lease_never_writes():
    store = Store(valid=False)
    with pytest.raises(RuntimeError, match="lease"):
        asyncio.run(publish(store, source(), "new", "expired"))
    assert store.events == [("lease", "expired")]
    assert store.saved is None


@pytest.mark.parametrize("failure", ["write", "commit"])
def test_failure_rolls_back_and_preserves_original(failure):
    original = source()
    snapshot = deepcopy(original)
    store = Store(fail=failure)
    with pytest.raises(OSError, match=failure):
        asyncio.run(publish(store, original, "new", "lease-1"))
    expected = ["lease", "write"] + (["commit"] if failure == "commit" else [])
    assert [event[0] for event in store.events] == expected + ["rollback"]
    assert store.saved is None and store.staged is None
    assert original == snapshot


@pytest.mark.parametrize("field,value", [("status", "failed"), ("cacheable", False)])
def test_ineligible_source_has_no_side_effects(field, value):
    original = source()
    original[field] = value
    store = Store()
    with pytest.raises(ValueError):
        asyncio.run(publish(store, original, "new", "lease-1"))
    assert store.events == []
""",
            "tests/test_rollback_failure.py": """import asyncio

import pytest

from product.publish import publish
from test_publish import Store, source


@pytest.mark.parametrize("failure", ["write", "commit"])
def test_rollback_error_does_not_replace_original(failure):
    class BrokenRollback(Store):
        async def rollback(self):
            await super().rollback()
            raise RuntimeError("rollback failed")

    store = BrokenRollback(fail=failure)
    with pytest.raises(OSError, match=failure):
        asyncio.run(publish(store, source(), "new", "lease"))
    assert [event[0] for event in store.events].count("rollback") == 1
""",
            "tests/test_summary.py": """from copy import deepcopy

from product.summary import summary


def test_summary_filters_provenance_and_does_not_alias():
    records = [{"run_id": "new", "status": "succeeded", "reused_from": "old",
                "evidence": {"scores": [3]}},
               {"run_id": "other", "status": "succeeded", "reused_from": "old"},
               {"run_id": "new", "status": "failed", "reused_from": "old"},
               {"run_id": "new", "status": "succeeded", "reused_from": None}]
    snapshot = deepcopy(records)
    result = summary(records, "new")
    assert result == {"total": 3, "reused": 1, "records": [records[0], records[2], records[3]]}
    result["records"][0]["evidence"]["scores"].append(9)
    assert records == snapshot
    assert summary([], "new") == {"total": 0, "reused": 0, "records": []}
""",
        },
        "units": [
            {
                "unit_id": "atomic-publish",
                "risk": "high",
                "dependencies": [],
                "path": "src/product/publish.py",
                "paths": ["src/product/publish.py", "src/product/evidence.py"],
                "anchors": {
                    "src/product/publish.py": "async def publish",
                    "src/product/evidence.py": "def copy_evidence",
                },
                "anchor": "async def publish",
                "required_order": [
                    "Validate eligibility before any store call",
                    "Await check_lease before write",
                    "Await write before commit",
                ],
                "forbidden_orderings": [
                    "Write or commit after rejected lease",
                    "Return success after write or commit failure",
                ],
                "tests": ["tests/test_publish.py", "tests/test_rollback_failure.py"],
                "contract": "Reject non-succeeded or non-cacheable sources with ValueError before any store call. Await check_lease(lease) before write; invalid lease raises RuntimeError mentioning lease without write/commit. Copy complete nested evidence without aliases, set run_id and reused_from to original run_id. Await write then commit exactly once. A write or commit exception must await rollback once and re-raise the original exception, never return success. Keep these transaction invariants in this atomic multi-file unit. Return copied evidence after successful commit.",
            },
            {
                "unit_id": "isolated-summary",
                "risk": "medium",
                "dependencies": ["atomic-publish"],
                "path": "src/product/summary.py",
                "anchor": "def summary",
                "tests": [
                    "tests/test_summary.py",
                    "tests/test_publish.py",
                    "tests/test_rollback_failure.py",
                ],
                "contract": "Filter exact run_id, preserve input order, return total and reused counts plus deep-copied records. Reused counts only succeeded records with nonnull reused_from. Empty input yields zero counts and empty records. Never mutate inputs or accepted publication code.",
            },
        ],
    }
