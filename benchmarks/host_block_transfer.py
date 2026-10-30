"""New local behavior changes on frozen sibling functions; unchanged A/B adapters."""

import argparse
import shutil
from pathlib import Path

import host_block_trial as R

M, B, S, T, P = R.M, R.B, R.S, R.T, R.P
BATCH = P.I.BASE / "host-block-transfer-20261022-1"
ORDER = [
    "hash-B1",
    "binding-A1",
    "hash-A1",
    "binding-B1",
    "binding-B2",
    "hash-A2",
    "binding-A2",
    "hash-B2",
]
ORIGIN = Path("F:/ChatGPT/agent-evaluation-harness/src/evaluation_harness")


def tasks():
    canonical = T.extract(ORIGIN / "canonical/fingerprint.py", "canonical_json")
    helper = "import json\nfrom typing import Any\n\n" + canonical
    return {
        "hash": {
            "symbol": "request_hash",
            "origin": ORIGIN / "jobs/queue.py",
            "header": "import hashlib\nfrom typing import Any\nfrom .dependencies import canonical_json\n",
            "files": {"src/product/dependencies.py": helper},
            "dependency_context": helper,
            "contract": "Change request_hash(payload) so top-level keys exactly 'request_id' and 'traceparent' are excluded from the digest, regardless of their values. Preserve every other key/value and all nested occurrences of these names. Keep the existing protected canonical_json encoding and lowercase SHA-256 hex representation; no JSON/hash setting changes, stringification shortcuts, deep filtering, input mutation, or changes to helper/imports/signature. Ignored values must not be inspected or serialized. Keys are case-sensitive. Empty retained payload hashes exactly like {}. Existing handling of unsupported retained values, tuple/list values, Unicode, and canonical sorting stays defined by canonical_json. This is an isolated experiment, not a change to live job identities.",
            "reference": """def request_hash(payload: dict[str, Any]) -> str:
    retained = {key: value for key, value in payload.items() if key not in {"request_id", "traceparent"}}
    return hashlib.sha256(canonical_json(retained)).hexdigest()
""",
            "public": """import hashlib
from product.code import request_hash
from product.dependencies import canonical_json

def test_ignore_top_level_only():
    payload = {"request_id": "one", "traceparent": "two", "body": {"request_id": "kept"}, "count": 0}
    expected = {"body": {"request_id": "kept"}, "count": 0}
    assert request_hash(payload) == hashlib.sha256(canonical_json(expected)).hexdigest()

def test_empty_and_no_volatile():
    for payload in [{}, {"x": False, "text": "雪", "value": None}, {"request_id": None}]:
        expected = {} if "request_id" in payload else payload
        assert request_hash(payload) == hashlib.sha256(canonical_json(expected)).hexdigest()

def test_nested_volatile_still_matters():
    assert request_hash({"data": {"traceparent": "a"}}) != request_hash({"data": {"traceparent": "b"}})
""",
            "private": """import copy
import hashlib
import itertools
import json
import pytest
from product.code import request_hash

def expected(payload):
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()

@pytest.mark.parametrize("value", [None, False, 0, "", [], {"x": [1]}, "秘密"])
def test_all_ignored_values(value):
    raw = {"request_id": value, "traceparent": value, "Request_id": value, "body": {"traceparent": value}}
    before = copy.deepcopy(raw)
    assert request_hash(raw) == expected({"Request_id": value, "body": {"traceparent": value}})
    assert raw == before

def test_ignored_object_is_not_serialized():
    class Poison:
        def __str__(self):
            raise AssertionError("ignored value was inspected")
    assert request_hash({"request_id": Poison(), "traceparent": Poison()}) == expected({})

def test_retained_fallback_and_tuple_are_unchanged():
    class Value:
        def __str__(self):
            return "custom Unicode 雪"
    raw = {"nested": [Value(), (1, False, None)], "request_id": "ignored"}
    assert request_hash(raw) == expected({"nested": raw["nested"]})

def test_permutations_and_not_deep_filter():
    fields = [("z", 0), ("traceparent", "ignored"), ("a", [{"request_id": 2}]), ("request_id", "ignored")]
    for order in itertools.permutations(fields):
        assert request_hash(dict(order)) == expected({"z": 0, "a": [{"request_id": 2}]})

def test_retained_key_error_is_not_silently_coerced():
    with pytest.raises(TypeError):
        request_hash({1: "a", "other": "b", "request_id": "ignored"})
""",
            "cases": [
                {
                    "args": [{"request_id": "a", "data": {"traceparent": "kept"}}],
                    "kwargs": {},
                },
                {"args": [{"request_id": None, "traceparent": False}], "kwargs": {}},
            ],
        },
        "binding": {
            "symbol": "application_binding_path",
            "origin": ORIGIN / "telemetry/ingestion.py",
            "header": "from urllib.parse import quote, urlencode\n",
            "contract": "Before producing application_binding_path(workspace_id, application_id, environment), reject any of the three string arguments if it is empty, consists only of Unicode whitespace according to str.strip(), or contains an ASCII control character U+0000..U+001F or U+007F anywhere. Raise ValueError for those cases. For every valid string, preserve its original contents byte-for-byte through the existing URL encoding: do not strip valid leading/trailing whitespace or Unicode, normalize percent escapes, or change parameter order. Preserve the existing /v1/applications/<quoted application_id>?workspace_id=...&environment=... shape, quote safe='' path escaping and urlencode query semantics. No network, changes to imports/signature or unrelated functions. Inputs in scope are strings; no new coercions.",
            "reference": """def application_binding_path(workspace_id: str, application_id: str, environment: str) -> str:
    for value in (workspace_id, application_id, environment):
        if not value.strip() or any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("binding identities must be nonblank and contain no ASCII controls")
    return f"/v1/applications/{quote(application_id, safe='')}?" + urlencode({"workspace_id": workspace_id, "environment": environment})
""",
            "public": """import pytest
from product.code import application_binding_path

def test_existing_encoding():
    assert application_binding_path("space here", "a/b", "prod+one") == "/v1/applications/a%2Fb?workspace_id=space+here&environment=prod%2Bone"

@pytest.mark.parametrize("args", [("", "a", "prod"), ("w", "  ", "prod"), ("w", "a", "bad\\nvalue"), ("w\\x00", "a", "prod")])
def test_invalid_identities(args):
    with pytest.raises(ValueError):
        application_binding_path(*args)

def test_valid_whitespace_is_preserved():
    assert application_binding_path(" w ", " a ", " prod ") == "/v1/applications/%20a%20?workspace_id=+w+&environment=+prod+"
""",
            "private": """import itertools
from urllib.parse import quote, urlencode
import pytest
from product.code import application_binding_path

@pytest.mark.parametrize("position", range(3))
def test_every_ascii_control_and_unicode_blank(position):
    for value in ["", " ", "\\u3000", "\\u00a0"] + ["x" + chr(code) + "y" for code in [*range(32), 127]]:
        args = ["workspace", "app", "prod"]
        args[position] = value
        with pytest.raises(ValueError):
            application_binding_path(*args)

def test_valid_encoded_combinations_preserve_original():
    values = ["plain", " 雪 ", "a/b?x#y", "%2F", "a+b&c", "a\\u0085b", "a\\u2028b", "\\u200b"]
    for w, a, e in itertools.product(values, repeat=3):
        expected = f"/v1/applications/{quote(a, safe='')}?" + urlencode({"workspace_id": w, "environment": e})
        assert application_binding_path(w, a, e) == expected
""",
            "cases": [
                {"args": ["w", "a/b", " prod "], "kwargs": {}},
                {"args": ["w", "a", "bad\nvalue"], "kwargs": {}},
            ],
        },
    }


def prepare(used):
    old = P.I.BASE / "host-block-trial-20261022-2"
    decision = S.read(old / "decision.json")
    assert decision["status"] == "HOLD_OVERALL_WITH_NARROW_BLOCK_REPAIR_BENEFIT"
    previous = S.read(old / "registration.json")
    assert S.sha(B.__file__) == previous["pins"][str(Path(B.__file__))]
    specs, materials, rows = tasks(), {}, {}
    for topic, spec in specs.items():
        origin = spec["origin"]
        origin_sha = S.sha(origin)
        T.write(BATCH / "origins" / (topic + ".py"), origin.read_text(encoding="utf-8"))
        spec["start"] = T.extract(origin, spec["symbol"])
        spec["risk_rationale"] = (
            "Public URL/identity compatibility boundaries; high risk despite narrow pure function. Only isolated experiment changes, Primary reviews all diffs and complete independent checks."
        )
        spec["scenarios"] = [
            {
                "id": "normal",
                "text": "Specified new behavior with exact original encoding/dependency semantics",
            },
            {
                "id": "boundary",
                "text": "Falsy, Unicode, nested, empty and control-character boundaries; preserve valid old behavior",
            },
            {
                "id": "error",
                "text": "Exact new rejections and preserved dependency failures; no mutation or side effects",
            },
        ]
        materials[topic] = M.template(BATCH, topic, spec)
        assert S.sha(origin) == origin_sha
    T.write(
        BATCH / "origins/canonical.py",
        (ORIGIN / "canonical/fingerprint.py").read_text(encoding="utf-8"),
    )
    R.BATCH = BATCH
    for label in ORDER:
        topic, arm_repeat = label.split("-")
        row = M.cell(
            BATCH, label, topic, specs[topic], materials[topic], Path(__file__)
        )
        row["arm"], row["repeat"] = arm_repeat[0], int(arm_repeat[1])
        root = Path(row["root"])
        # One candidate-specific reference replay per topic/arm; same-version
        # controls apply to the second repetition instead of another ritual replay.
        if row["repeat"] == 1:
            proof = BATCH / "block-replay" / label / "isolated"
            shutil.copytree(root, proof)
            reference = T.extract(
                materials[topic][2] / M.TARGET, specs[topic]["symbol"]
            )
            current = T.extract(root / M.TARGET, specs[topic]["symbol"])
            value = (
                {
                    "kind": "edits",
                    "edits": [{"find": current, "replace": reference}],
                    "reason": "",
                }
                if row["arm"] == "B"
                else {"kind": "replacement", "content": reference}
            )
            replay = proof.parent / "reference.json"
            S.save(replay, [value])
            result = T.run(R.command(proof, replay=replay), proof, timeout=180)
            S.save(proof.parent / "process.json", result)
            assert result["exit_code"] == 0, result
        rows[label] = row
    for topic in specs:
        assert (
            len({v["start_sha256"] for v in rows.values() if v["topic"] == topic}) == 1
        )
    S.save(BATCH / "cells.json", rows)
    S.save(
        BATCH / "registration.json",
        {
            "feature_id": "host-block-new-behavior-transfer",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "owned_contract_ids": [
                "hash",
                "binding",
                "immutable-input",
                "independent-acceptance",
            ],
            "dependencies": ["host-block-trial-20261022-2"],
            "registered": 8,
            "order": ORDER,
            "question": "Does the unchanged exact-block interface retain or improve full-chain completion on two new requested behavior changes, instead of only the exposed SSE failure?",
            "candidate": "Same A/B code hash as prior trial, all base runtime and Reviewer unchanged. Original8-cell strict gate remains HOLD; this is diagnostic transfer, not qualification backfill.",
            "exposure": "New contracts/public-private tests on two real frozen sibling functions. Source files may have appeared in prior research; not an unknown repository or broad benchmark. Each task has two correlated repeats per arm. Only original functions are extracted; imports consolidated, helper copied exactly; no claim of sibling application integration.",
            "scope": "Only the named function editable; canonical_json/dependencies and tests/config protected. Reference and private tests outside Worker readable workspace. No extra Primary hints, Explorer, Coordinator, or code takeover during live.",
            "budget": previous["budgets"],
            "models": previous["models"],
            "gate": "B4/4 full checks+fresh Reviewer+Primary acceptance, zero false release/unsafe drift/assistance. Comparative gain requires B>A or fewer requests/noops for the same accepted cells. Equal4/4 only supports limited transfer feasibility, not benefit, general stability or adoption.",
            "continue_rule": previous["continue_rule"],
            "next_branch": "If B holds and A succeeds, do not adopt block interface generally. If both succeed, keep whole-function default and consider blocks only exposed-stall evidence, not as new global default. If both fail, preserve task-family boundary and investigate concrete failure, not add prompts or trials to replace scores.",
            "primary_cost": "One-time adapter reused; new contract/tests/reference are task-preparation cost. Full review remains recurring. No concrete repair provided in Worker goal, reference hidden. Active time/cloud tokens unknown, no Primary-only economics.",
            "weekly_used_start": used,
            "weekly_cap": None,
            "production_defaults_changed": False,
            "commit_push": False,
            "pins": M.pins(
                BATCH,
                Path(__file__),
                Path(R.__file__),
                Path(B.__file__),
                old / "decision.json",
                *[v[1] for v in materials.values()],
                *sorted((BATCH / "origins").glob("*.py")),
            ),
        },
    )
    print(
        "Eight new-behavior transfer cells frozen with unchanged candidate; no live yet",
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "run"])
    parser.add_argument("--cell", choices=ORDER)
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.weekly_used)
    else:
        R.BATCH = BATCH
        P.BATCH, P.ORDER, P.command = BATCH, ORDER, R.command
        P.run(args.cell, args.weekly_used)
