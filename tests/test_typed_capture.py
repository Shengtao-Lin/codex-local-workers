import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import capture_validation_facts as C
import reviewer_canonical_capture as R


def policy(family, symbol, cases):
    return {
        "schema_version": 1,
        "identity": {"task_id": "t", "unit_id": "u", "run_id": "r"},
        "check_id": "actual-observations",
        "producer_path": "acceptance/capture_validation_facts.py",
        "producer_sha256": "a" * 64,
        "helper_path": "acceptance/reviewer_capture_envelope.py",
        "helper_sha256": "a" * 64,
        "python": {"path": sys.executable, "sha256": "a" * 64},
        "target": {
            "path": "src/product/code.py",
            "module": "product.code",
            "symbol": symbol,
        },
        "source_paths": ["src/product/code.py"],
        "readonly_hashes": {},
        "family": family,
        "cases": cases,
    }


def test_bytes_preserve_exact_value_without_text_decoding():
    p = policy(
        "canonical-json-bytes-v1", "canonical_json", [{"args": [], "kwargs": {}}]
    )
    C.validate_policy(p)
    out = C.observe(SimpleNamespace(canonical_json=lambda: b"\x00\xff\n"), p)
    assert out[0]["outcome"]["value"] == {"type": "bytes", "hex": "00ff0a"}
    json.dumps(out, allow_nan=False)
    profile = {
        "profile_id": p["family"],
        "source": {"path": p["target"]["path"], "sha256": "a" * 64},
        "examples": out,
        "meaning": C.MEANING,
    }
    manifest = {"files": {p["target"]["path"]: "a" * 64}}
    R.validate_profiles([profile], p, manifest)
    for bad in (
        {"type": "bytes", "hex": "x0"},
        {"type": "bytes", "hex": "0"},
        {"type": "text", "hex": "ff"},
    ):
        invalid = copy.deepcopy(profile)
        invalid["examples"][0]["outcome"]["value"] = bad
        with pytest.raises(C.CaptureRejected):
            R.validate_profiles([invalid], p, manifest)


@pytest.mark.parametrize("kind", ["str", "bytes", "bytearray"])
def test_raw_observes_target_directly(kind):
    p = policy(
        "mapping-raw-utf8-v1", "mapping_raw", [{"kind": kind, "text": '{"x":false}'}]
    )
    C.validate_policy(p)
    observed = []

    def target(trace):
        observed.append(type(trace.raw).__name__)
        return json.loads(trace.raw)

    out = C.observe(
        SimpleNamespace(
            mapping_raw=target, SourceTrace=lambda **kw: SimpleNamespace(**kw)
        ),
        p,
    )
    assert observed == [kind]
    assert out[0]["outcome"]["value"] == {"x": False}
    assert out[0]["input_unchanged"]
    profile = {
        "profile_id": p["family"],
        "source": {"path": p["target"]["path"], "sha256": "a" * 64},
        "examples": out,
        "meaning": C.MEANING,
    }
    R.validate_profiles([profile], p, {"files": {p["target"]["path"]: "a" * 64}})


@pytest.mark.parametrize(
    "change", ["wrong_symbol", "eval_kind", "extra_code", "wrong_text"]
)
def test_no_new_execution_authority(change):
    p = policy("mapping-raw-utf8-v1", "mapping_raw", [{"kind": "bytes", "text": "{}"}])
    if change == "wrong_symbol":
        p["target"]["symbol"] = "eval"
    elif change == "eval_kind":
        p["cases"][0]["kind"] = "eval"
    elif change == "extra_code":
        p["cases"][0]["code"] = "anything"
    else:
        p["cases"][0]["text"] = []
    with pytest.raises(C.CaptureRejected):
        C.validate_policy(copy.deepcopy(p))
