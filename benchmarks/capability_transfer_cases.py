"""Preregistered transfer fixtures. Primary references never enter worker scope."""

from __future__ import annotations

import copy

TRANSACTION_GUIDANCE = {
    "prose": "Outcomes: success has begin/write/commit, returns write value, no rollback. Begin failure has only begin and preserves that exception. Write failure has begin/write/rollback, no commit, preserves write exception even if rollback fails. Commit failure has begin/write/commit/rollback and preserves commit exception even if rollback fails. Every listed call is awaited; each rollback occurs once.",
    "matrix": "Outcome | awaited events | result\nsuccess | begin/write/commit | identical write value\nbegin failure | begin | identical begin exception\nwrite failure, rollback succeeds or fails | begin/write/rollback | identical write exception\ncommit failure, rollback succeeds or fails | begin/write/commit/rollback | identical commit exception\nNo other calls; each rollback occurs once.",
}

EXAMPLES = """Method examples (advisory, not this unit's answer):
1. SAFE_REPLACE reports target missing for `return old(x)`. SEARCH the exact
symbol, READ the current narrow block and hash; if it now says `return new(x)`,
build an exact small replacement from that observation, not the old draft.
2. Validation says an independent error branch regressed after a successful
normal-path edit. Read that failure and its source; preserve both branches,
make the smallest evidence-backed edit, then VALIDATE again. A comment claiming
an invariant is not executable evidence. No repeated identical replacement.
"""

ACTION_EXAMPLES = """Unrelated worked example; advisory only, not this unit's solution.
Toy contract: load_title(record) trims record['title']; a None title raises
ValueError. A missing key must still raise KeyError. The protected test says
with pytest.raises(ValueError): load_title({'title': None}).
Action: {"action":"VALIDATE","arguments":{"phase":"check"}}
Observation: failed; AttributeError: 'NoneType' object has no attribute 'strip'.
Interpretation: AttributeError is what happened, NOT what the test expects.
Action: {"action":"READ_FILE","arguments":{"path":"src/title.py"}}
Observation: sha256=H_CURRENT; lines:
1 def load_title(record):
2     return record['title'].strip()
Action: {"action":"SAFE_REPLACE","arguments":{"path":"src/title.py",
"expected_sha256":"H_CURRENT","find":"    return record['title'].strip()",
"replace":"    title = record['title']\\n    if title is None:\\n        raise ValueError('missing title')\\n    return title.strip()"}}
Observation: modified, new sha256=H_NEW. Missing-key lookup was preserved.
Action: {"action":"VALIDATE","arguments":{"phase":"check"}}
Observation: passed, nonzero focused tests and configured checks passed.
Only then submit FINISH_SUCCESS. H_CURRENT/H_NEW are toy placeholders: use
the actual runtime hash and legal arguments in your own call. Never edit tests
or reinterpret an unexpected exception as success.
"""


def transfer_cases(template):
    specs = [
        (
            "transfer-retry-delay",
            "medium",
            "Accept exact int (not bool) or ASCII decimal string in 0..9. Reject other types, signs, whitespace, non-ASCII digits with ValueError; return seconds as int.",
            "def delay(value):\n    return int(value)\n",
            """import pytest
from product.target import delay

@pytest.mark.parametrize("value,expected", [(0,0),(9,9),("00",0),("9",9)])
def test_valid(value, expected):
    assert delay(value) == expected

@pytest.mark.parametrize("value", [True,False,-1,10,"10","+1"," 1","1\\n","１","١",1.0,None,[],{}])
def test_invalid(value):
    with pytest.raises(ValueError):
        delay(value)
""",
            """def delay(value):
    if type(value) is int:
        result = value
    elif isinstance(value, str) and value and all("0" <= char <= "9" for char in value):
        result = int(value)
    else:
        raise ValueError("invalid delay")
    if not 0 <= result <= 9:
        raise ValueError("delay outside range")
    return result
""",
            [
                "def delay(value):\n    return int(value)\n",
                "def delay(value):\n    return 0\n",
            ],
        ),
        (
            "transfer-tag-projection",
            "medium",
            "Select records whose enabled is exactly True. Return tags sorted by name, preserving equal-name input order. Deep-copy every nested tag; preserve input and reject a selected record with missing tag via KeyError. Ignore disabled records even if malformed.",
            "def project(records):\n    return [record['tag'] for record in records]\n",
            """from copy import deepcopy
import pytest
from product.target import project

def test_isolated_and_stable():
    records = [{"enabled":True,"tag":{"name":"b","data":[1]}}, {"enabled":True,"tag":{"name":"a","data":[2]}}, {"enabled":True,"tag":{"name":"a","data":[3]}}, {"enabled":False}, {"enabled":1,"tag":{"name":"x"}}]
    before = deepcopy(records)
    result = project(records)
    assert [item["data"] for item in result] == [[2],[3],[1]]
    result[0]["data"].append(8)
    assert records == before

def test_empty_and_missing():
    assert project([]) == []
    assert project([{"enabled":False}]) == []
    with pytest.raises(KeyError):
        project([{"enabled":True}])
""",
            """from copy import deepcopy

def project(records):
    tags = [deepcopy(record["tag"]) for record in records if record.get("enabled") is True]
    return sorted(tags, key=lambda tag: tag["name"])
""",
            [
                'def project(records):\n    return sorted([record["tag"] for record in records if record.get("enabled") is True], key=lambda tag: tag["name"])\n'
            ],
        ),
        (
            "transfer-lock-release",
            "high",
            "Await lock.acquire before operation; if it returns False raise RuntimeError without operation/release. After successful acquisition await operation then release exactly once on success or failure. Preserve the operation exception if release also fails. Successful operation plus failed release must propagate release exception. Return operation result unchanged.",
            "async def guarded(lock, operation):\n    return await operation()\n",
            """import asyncio
import pytest
from product.target import guarded

class Lock:
    def __init__(self, events, acquired=True, fail=False):
        self.events, self.acquired, self.fail = events, acquired, fail
    async def acquire(self):
        self.events.append("acquire")
        return self.acquired
    async def release(self):
        self.events.append("release")
        if self.fail:
            raise RuntimeError("release")

@pytest.mark.parametrize("operation_fails,release_fails", [(False,False),(True,False),(True,True),(False,True)])
def test_order_and_original_error(operation_fails, release_fails):
    events = []
    original = OSError("operation")
    value = {"result":[1]}
    async def operation():
        events.append("operation")
        if operation_fails:
            raise original
        return value
    lock = Lock(events, fail=release_fails)
    if operation_fails:
        with pytest.raises(OSError) as caught:
            asyncio.run(guarded(lock, operation))
        assert caught.value is original
    elif release_fails:
        with pytest.raises(RuntimeError, match="release"):
            asyncio.run(guarded(lock, operation))
    else:
        assert asyncio.run(guarded(lock, operation)) is value
    assert events == ["acquire","operation","release"]

def test_denied():
    events = []
    async def operation():
        events.append("operation")
    with pytest.raises(RuntimeError):
        asyncio.run(guarded(Lock(events, acquired=False), operation))
    assert events == ["acquire"]
""",
            """from contextlib import suppress

async def guarded(lock, operation):
    if not await lock.acquire():
        raise RuntimeError("lock denied")
    try:
        result = await operation()
    except Exception:
        with suppress(Exception):
            await lock.release()
        raise
    await lock.release()
    return result
""",
            [
                'async def guarded(lock, operation):\n    if not await lock.acquire():\n        raise RuntimeError("lock denied")\n    try:\n        return await operation()\n    finally:\n        await lock.release()\n'
            ],
        ),
    ]
    specs.append(
        (
            "transfer-transaction-save",
            "high",
            (
                "Await begin, write(rows), then commit. Return write result unchanged. "
                "If begin fails, propagate its identical exception without write, commit or rollback. "
                "If write or commit fails, await rollback exactly once, preserve the identical original "
                "exception even if rollback fails, and never commit after write failure. Never rollback on success."
            ),
            "async def save(store, rows):\n    await store.begin()\n    value = await store.write(rows)\n    await store.commit()\n    return value\n",
            """import asyncio
import pytest
from product.target import save

@pytest.mark.parametrize("failed,rollback_fails", [(None,False),("begin",False),("write",False),("write",True),("commit",False),("commit",True)])
def test_transaction(failed, rollback_fails):
    events = []
    original = OSError("original")
    rows, value = object(), object()
    class Store:
        async def begin(self):
            events.append("begin")
            if failed == "begin":
                raise original
        async def write(self, received):
            assert received is rows
            events.append("write")
            if failed == "write":
                raise original
            return value
        async def commit(self):
            events.append("commit")
            if failed == "commit":
                raise original
        async def rollback(self):
            events.append("rollback")
            if rollback_fails:
                raise RuntimeError("rollback")
    if failed:
        with pytest.raises(OSError) as caught:
            asyncio.run(save(Store(), rows))
        assert caught.value is original
    else:
        assert asyncio.run(save(Store(), rows)) is value
    expected = {
        None: ["begin","write","commit"],
        "begin": ["begin"],
        "write": ["begin","write","rollback"],
        "commit": ["begin","write","commit","rollback"],
    }
    assert events == expected[failed]
""",
            """from contextlib import suppress

async def save(store, rows):
    await store.begin()
    try:
        value = await store.write(rows)
        await store.commit()
    except BaseException:
        with suppress(BaseException):
            await store.rollback()
        raise
    return value
""",
            [
                "async def save(store, rows):\n    await store.begin()\n    try:\n        value = await store.write(rows)\n        await store.commit()\n    except BaseException:\n        await store.rollback()\n        raise\n    return value\n",
                "async def save(store, rows):\n    try:\n        await store.begin()\n        value = await store.write(rows)\n        await store.commit()\n    except BaseException:\n        try:\n            await store.rollback()\n        except BaseException:\n            pass\n        raise\n    return value\n",
            ],
        )
    )
    transaction = specs[-1]
    cancellation_contract = transaction[2] + (
        " Failure includes asyncio.CancelledError from begin, write, commit or rollback. "
        "After write/commit cancellation attempt rollback exactly once and preserve the original "
        "exception object even when rollback raises CancelledError. Begin cancellation needs no rollback. "
        "This contract covers awaited methods raising cancellation, not repeated external task.cancel()."
    )
    ordinary_only = transaction[5].replace("BaseException", "Exception")
    cancellation_tests = """
@pytest.mark.parametrize("failed", ["begin", "write", "commit"])
@pytest.mark.parametrize("original_cancelled", [False, True])
@pytest.mark.parametrize("rollback_cancelled", [False, True])
def test_cancel_boundary(failed, original_cancelled, rollback_cancelled):
    events = []
    original = asyncio.CancelledError("original") if original_cancelled else OSError("original")
    class Store:
        async def begin(self):
            events.append("begin")
            if failed == "begin":
                raise original
        async def write(self, rows):
            events.append("write")
            if failed == "write":
                raise original
        async def commit(self):
            events.append("commit")
            raise original
        async def rollback(self):
            events.append("rollback")
            if rollback_cancelled:
                raise asyncio.CancelledError("rollback")
    with pytest.raises(type(original)) as caught:
        asyncio.run(save(Store(), []))
    assert caught.value is original
    assert events == {
        "begin": ["begin"],
        "write": ["begin", "write", "rollback"],
        "commit": ["begin", "write", "commit", "rollback"],
    }[failed]
"""
    specs.append(
        (
            "transfer-save-cancel",
            "high",
            cancellation_contract,
            ordinary_only,
            transaction[4] + cancellation_tests,
            transaction[5],
            [ordinary_only, transaction[6][0]],
        )
    )
    overlay_tests = """from copy import deepcopy
from product.target import overlay

def test_recursive_merge_and_delete():
    base = {"nested": {"keep": 1, "remove": 2}, "outside": 9}
    patch = {"nested": {"remove": None, "add": 3}}
    assert overlay(base, patch) == {"nested": {"keep": 1, "add": 3}, "outside": 9}

def test_inputs_unchanged():
    base = {"nested": {"values": [1], "remove": 2}}
    patch = {"nested": {"remove": None, "new": [3]}}
    before = deepcopy((base, patch))
    overlay(base, patch)
    assert (base, patch) == before

def test_no_alias_to_base_or_patch():
    base = {"keep": {"values": [1]}}
    patch = {"new": [{"values": [2]}]}
    result = overlay(base, patch)
    result["keep"]["values"].append(8)
    result["new"][0]["values"].append(9)
    assert base == {"keep": {"values": [1]}}
    assert patch == {"new": [{"values": [2]}]}

def test_mapping_replaces_scalar_and_applies_nested_deletions():
    assert overlay({"a": 7}, {"a": {"gone": None, "b": 2}}) == {"a": {"b": 2}}

def test_empty_patch_is_independent_copy():
    base = {"a": [{"b": [1]}]}
    result = overlay(base, {})
    result["a"][0]["b"].append(3)
    assert base == {"a": [{"b": [1]}]}

def test_lists_replace_and_missing_deletion_is_noop():
    assert overlay({"a": [1]}, {"a": [2], "absent": None}) == {"a": [2]}
"""
    overlay_reference = """from copy import deepcopy

def overlay(base, patch):
    result = deepcopy(base)
    for key, value in patch.items():
        if value is None:
            result.pop(key, None)
        elif isinstance(value, dict):
            previous = result.get(key)
            result[key] = overlay(previous if isinstance(previous, dict) else {}, value)
        else:
            result[key] = deepcopy(value)
    return result
"""
    overlay_initial = "def overlay(base, patch):\n    result = dict(base)\n    result.update(patch)\n    return result\n"
    specs.append(
        (
            "transfer-overlay",
            "medium",
            "For dict inputs, recursively merge dict patch values into dict base values (or an empty dict when replacing a scalar). None patch values delete keys, missing deletion is a no-op. Lists and other non-dict non-None values replace, not concatenate. Return a fully deep-independent result; do not mutate or alias either input, including unchanged base subtrees and nested patch lists. Empty patch still returns an independent copy. Input keys are strings and values are JSON-compatible; no other input forms required.",
            overlay_initial,
            overlay_tests,
            overlay_reference,
            [
                overlay_initial,
                overlay_reference.replace(
                    "result = deepcopy(base)", "result = dict(base)"
                ).replace("deepcopy(value)", "value"),
            ],
        )
    )
    results, oracles = [], {}
    for identity, risk, contract, source, tests, reference, mutants in specs:
        case = copy.deepcopy(template)
        case.update(
            case_id=identity, goal=contract, feature_risk=risk, integration_risk=risk
        )
        case["files"] = {
            "src/product/__init__.py": "",
            "src/product/target.py": source,
            "tests/test_target.py": tests,
        }
        unit = copy.deepcopy(template["units"][0])
        unit.update(
            unit_id="transfer-unit",
            risk=risk,
            path="src/product/target.py",
            anchor=source.split("(")[0].split()[-1],
            tests=["tests/test_target.py"],
            dependencies=[],
            contract=contract,
        )
        # The materializer consumes behavior, not the feature's display goal.
        unit["behavior"] = contract
        if identity in {"transfer-transaction-save", "transfer-save-cancel"}:
            unit["required_order"] = [
                "Await begin before write and write before commit",
                "Await rollback exactly once after write or commit failure",
            ]
            unit["forbidden_orderings"] = [
                "Write, commit or rollback after begin failure",
                "Commit after write failure or rollback after success",
                "Replace the original failure with rollback failure",
            ]
        if identity == "transfer-lock-release":
            unit["required_order"] = [
                "Await successful lock.acquire before operation",
                "Await operation before release",
            ]
            unit["forbidden_orderings"] = [
                "Invoke operation or release after rejected acquisition",
                "Replace an operation exception with a release exception",
            ]
        case["units"] = [unit]
        results.append(case)
        oracles[identity] = {"reference": reference, "mutants": mutants}
    # Separately versioned diagnostic development cohort; old fixtures stay exact.
    for original, identity in (
        ("transfer-save-cancel", "diag-save-cancel"),
        ("transfer-overlay", "diag-overlay"),
    ):
        case = copy.deepcopy(next(c for c in results if c["case_id"] == original))
        case["case_id"] = identity
        case["files"]["src/product/target.py"] = (
            "import math\n\n" + case["files"]["src/product/target.py"]
        )
        results.append(case)
        oracles[identity] = copy.deepcopy(oracles[original])
    return results, oracles
