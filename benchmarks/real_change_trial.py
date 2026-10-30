"""Six new real-source feature trials; reuse installed fixture and execution engines."""

import argparse
import os
import subprocess
from pathlib import Path

import installed_real_trial as R
import installed_scope_trial as I
import normal_task_trial as N
import bounded_evidence_support as S

BATCH = I.BASE / "real-change-trial-20261021-4"
ORDER = ["json-1", "message-1", "destination-1", "destination-2", "message-2", "json-2"]
TASKS = {
    "json": {
        "origin": "canonical/fingerprint.py",
        "symbol": "canonical_json",
        "header": "import json\nfrom typing import Any\n",
        "contract": "canonical_json(value: Any) -> bytes must reject nonfinite floating values NaN, positive infinity and negative infinity anywhere json serialization encounters them, with ValueError, instead of emitting nonstandard JSON numbers. Preserve exact previous bytes for all other supported inputs: literal Unicode, sorted keys, compact separators, UTF-8, default=str for otherwise unsupported objects, no input mutation. Existing serialization exceptions remain errors. Do not stringify nonfinite floats or replace them with null. Keep signature and imports unchanged.",
        "reference": '''def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False).encode("utf-8")
''',
        "public": '''import json
import pytest
from product.code import canonical_json

@pytest.mark.parametrize("value", [float("nan"), {"a": [float("inf")]}, [float("-inf")]])
def test_nonfinite_rejected(value):
    with pytest.raises(ValueError):
        canonical_json(value)

def test_exact_ordinary_bytes():
    value = {"雪": [False, None, 0, ""], "a": 1.5}
    assert canonical_json(value) == json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
''',
        "private": '''import copy
import json
from datetime import date
import pytest
from product.code import canonical_json

def test_compatibility_and_no_mutation():
    value = {"z": [date(2026, 10, 21), -0.0, 1e200, {}, "\\n"], "a": "雪"}
    before = copy.deepcopy(value)
    assert canonical_json(value) == json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    assert value == before

@pytest.mark.parametrize("value", [{"a": {"b": float("nan")}}, (1, float("inf")), {"x": float("-inf")}])
def test_deep_nonfinite(value):
    with pytest.raises(ValueError):
        canonical_json(value)
''',
        "cases": [{"args": [{"雪": [0, False, None]}], "kwargs": {}}, {"args": [[1, 2]], "kwargs": {}}],
    },
    "message": {
        "origin": "adapters/common.py",
        "symbol": "stable_message_id",
        "header": "import hashlib\nimport json\nfrom typing import Any\n",
        "contract": "stable_message_id(source_trace_id: str, index: int, message: dict[str, Any]) -> str must select the first eligible explicit ID from keys id then message_id. Eligible means a nonempty string (preserve whitespace exactly), or any integer including zero/negative integers but NOT bool; return str of that value. Ineligible values None, empty string, bool, floats, lists and dictionaries do not count, so try the other key. If neither key is eligible preserve the exact existing fallback msg_{source_trace_id}_{index}_{digest}, with digest the first 16 hex characters of SHA256 of json.dumps of the COMPLETE unmodified message using sort_keys=True, default=str, separators=(',', ':') and existing default ASCII escaping. Do not drop invalid ID fields from digest. Do not mutate inputs. Keep signature/imports.",
        "reference": '''def stable_message_id(source_trace_id: str, index: int, message: dict[str, Any]) -> str:
    for key in ("id", "message_id"):
        supplied = message.get(key)
        if (isinstance(supplied, str) and supplied != "") or (isinstance(supplied, int) and not isinstance(supplied, bool)):
            return str(supplied)
    digest = hashlib.sha256(json.dumps(message, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()[:16]
    return f"msg_{source_trace_id}_{index}_{digest}"
''',
        "public": '''import hashlib
import json
from product.code import stable_message_id

def test_explicit_priority():
    assert stable_message_id("t", 0, {"id": 0, "message_id": "second"}) == "0"
    assert stable_message_id("t", 0, {"id": False, "message_id": "second"}) == "second"
    assert stable_message_id("t", 0, {"id": " ", "message_id": 3}) == " "

def test_invalid_fallback_preserved():
    value = {"id": [], "message_id": {}, "雪": "x"}
    digest = hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()[:16]
    assert stable_message_id("trace", 2, value) == f"msg_trace_2_{digest}"
''',
        "private": '''import copy
import hashlib
import json
import pytest
from product.code import stable_message_id

@pytest.mark.parametrize("bad", [None, "", True, False, 1.5, ["x"], {"x": 1}])
def test_every_invalid_primary_falls_through(bad):
    value = {"id": bad, "message_id": -7}
    before = copy.deepcopy(value)
    assert stable_message_id("t", 1, value) == "-7"
    assert value == before

def test_complete_fallback_and_explicit_compatibility():
    for value in [{}, {"id": True, "message_id": False}, {"id": 1.5}, {"content": "雪"}]:
        digest = hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()[:16]
        assert stable_message_id("a/b", -1, value) == f"msg_a/b_-1_{digest}"
    assert stable_message_id("t", 1, {"id": "first", "message_id": 0}) == "first"
    assert stable_message_id("t", 1, {"message_id": 0}) == "0"
''',
        "cases": [{"args": ["t", 0, {"id": 0, "message_id": "other"}], "kwargs": {}}, {"args": ["t", 1, {}], "kwargs": {}}],
    },
    "destination": {
        "origin": "telemetry/ingestion.py",
        "symbol": "check_collector_destination",
        "header": "\"\"\"Destination ID validation; no imports required.\"\"\"\n",
        "contract": "check_collector_destination(config: dict[str, str], declared_id: str) -> None must first require config['MLFLOW_EXPERIMENT_ID'] to be a nonempty ASCII digit string (characters 0 through 9 only), otherwise raise ValueError even when declared_id equals it. Leading zeros are valid and preserved. Then retain exact string equality comparison with declared_id: return None only on exact equality; mismatch raises ValueError whose message retains 'Collector destination mismatch' and both repr values. No trimming, integer conversion or Unicode digit acceptance. Missing config key must still raise KeyError. No mutation or external effects; retain signature and existing imports (none). Non-string values are outside this str-typed contract.",
        "reference": '''def check_collector_destination(config: dict[str, str], declared_id: str) -> None:
    expected = config["MLFLOW_EXPERIMENT_ID"]
    if not expected or any(char < "0" or char > "9" for char in expected):
        raise ValueError("invalid MLflow experiment id")
    if declared_id != expected:
        raise ValueError(f"Collector destination mismatch: declared {declared_id!r}, registered {expected!r}.")
''',
        "public": '''import pytest
from product.code import check_collector_destination

@pytest.mark.parametrize("value", ["", "x", " 17", chr(0x661) + chr(0x667)])
def test_equal_invalid_is_rejected(value):
    with pytest.raises(ValueError):
        check_collector_destination({"MLFLOW_EXPERIMENT_ID": value}, value)

def test_valid_exact_and_mismatch():
    assert check_collector_destination({"MLFLOW_EXPERIMENT_ID": "0017"}, "0017") is None
    with pytest.raises(ValueError, match="Collector destination mismatch"):
        check_collector_destination({"MLFLOW_EXPERIMENT_ID": "0017"}, "17")
''',
        "private": '''import pytest
from product.code import check_collector_destination

@pytest.mark.parametrize("value", ["17\\n", "+17", "1.0", "１７", "1 7", "17/"])
def test_invalid_equal_shapes(value):
    with pytest.raises(ValueError):
        check_collector_destination({"MLFLOW_EXPERIMENT_ID": value}, value)

def test_keyerror_no_mutation_and_messages():
    with pytest.raises(KeyError):
        check_collector_destination({}, "17")
    config = {"MLFLOW_EXPERIMENT_ID": "0", "other": "keep"}
    assert check_collector_destination(config, "0") is None
    assert config == {"MLFLOW_EXPERIMENT_ID": "0", "other": "keep"}
    with pytest.raises(ValueError) as error:
        check_collector_destination(config, " 0")
    assert "Collector destination mismatch" in str(error.value)
    assert repr(" 0") in str(error.value) and repr("0") in str(error.value)
''',
        "cases": [{"args": [{"MLFLOW_EXPERIMENT_ID": "bad"}, "bad"], "kwargs": {}}, {"args": [{"MLFLOW_EXPERIMENT_ID": "0017"}, "0017"], "kwargs": {}}],
    },
}


def prepare(used):
    # Reuse the closed fixture builder without editing it or its prior artifacts.
    # Only replace its registration metadata for this NEW six-cell experiment.
    assert not BATCH.exists() and 0 <= used < 50
    old_save = S.save
    old_material = R.F.install_material
    def material(*args, **kwargs):
        if kwargs["target"]["symbol"] == "canonical_json":
            kwargs["family"] = "canonical-json-bytes-v1"
        return old_material(*args, **kwargs)
    def save(path, value):
        if Path(path) == BATCH / "registration.json":
            value.update(
                registered=len(ORDER),
                gate="6/6 independent full-chain accepts, each new task2/2; no assisted credit or safety drift",
                exposure="Three newly designed features on copied actual sibling functions; first three cells new, remaining repetitions exposed; not upstream confirmed bugs or deployments",
                roles="Qwen Coder and fresh Muse Reviewer; Explorer/Coordinator NOT_RUN, no qualification inferred",
                Primary="Primary authored explicit contracts, public/private acceptance and reference controls. No in-live semantic feedback or implementation takeover. Savings unknown.",
                budgets={"requests": 12, "effective_edits": 3, "initial_checks": 1, "post_edit_checks": 3, "coder_seconds": 900, "reviewer_requests": 16, "reviewer_seconds": 600},
                units={k: {"feature_id": "real-change-" + k, "risk": "high", "integration_risk": "high", "dependencies": [], "owned_contract_ids": [k], "rationale": "Serialized compatibility, ID precedence or destination validation invariant; isolation does not lower risk"} for k in TASKS},
            )
            for module in (Path(__file__), Path(R.__file__), Path(N.__file__), S.KIT / "benchmarks/supervised_record.py"):
                value["pins"][str(module)] = S.sha(module)
        old_save(path, value)
    S.save = save
    R.F.install_material = material
    R.BATCH, R.ORDER, R.TASKS = BATCH, ORDER, TASKS
    try:
        old_save(BATCH / "baseline.json", {
            "weekly_used": used,
            "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=S.KIT).decode().strip(),
            "status": subprocess.check_output(["git", "status", "--short", "-uno"], cwd=S.KIT).decode(),
            "production": {str(p): S.sha(p) for p in (S.KIT / ".local-agents").rglob("*") if p.is_file() and "__pycache__" not in p.parts},
        })
        R.prepare(used)
    finally:
        S.save = old_save
        R.F.install_material = old_material


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("--cell", choices=ORDER)
    parser.add_argument("--weekly-used", type=int, required=True)
    parser.add_argument("--observed-at", type=float)
    args = parser.parse_args()
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if args.mode == "prepare":
        prepare(args.weekly_used)
    else:
        N.run(args.cell, args.weekly_used, args.observed_at, batch=BATCH, order=ORDER, build_command=I.command, usage_limit=50, batch_seconds=10800)
