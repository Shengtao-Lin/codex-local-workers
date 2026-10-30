"""Producer/DTO shape controls without repository execution or semantic labels."""

import copy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import capture_validation_facts as P
import reviewer_canonical_capture as C


def policy():
    return {
        "schema_version": 1,
        "identity": {"task_id": "a", "unit_id": "a", "run_id": "a"},
        "check_id": "capture",
        "producer_path": "capture.py",
        "producer_sha256": "a" * 64,
        "helper_path": "helper.py",
        "helper_sha256": "b" * 64,
        "python": {"path": sys.executable, "sha256": "c" * 64},
        "target": {"path": "target.py", "module": "example", "symbol": "process"},
        "source_paths": ["target.py"],
        "readonly_hashes": {},
        "family": "json-call-model-dump-v1",
        "cases": [{"args": [False, 0, None], "kwargs": {}}],
    }


def test_generic_roundtrip_preserves_type_and_mutation_fact():
    p = P.validate_policy(policy())
    module = SimpleNamespace(process=lambda *args: list(args))
    before = copy.deepcopy(p)
    observations = P.observe(module, p)
    assert p == before
    assert observations[0]["outcome"]["value"] == [False, 0, None]
    assert type(observations[0]["outcome"]["value"][0]) is bool
    assert type(observations[0]["outcome"]["value"][1]) is int
    profile = {
        "profile_id": p["family"],
        "source": {"path": "target.py", "sha256": "d" * 64},
        "meaning": P.MEANING,
        "examples": observations,
    }
    assert C.validate_profiles([profile], p, {"files": {"target.py": "d" * 64}}) == [
        profile
    ]


@pytest.mark.parametrize(
    "change",
    [
        "expected",
        "command",
        "unknown-family",
        "too-many",
        "code-input",
        "infinite",
        "symbol",
        "unknown-case",
        "identity",
        "digest",
    ],
)
def test_policy_rejects_extra_authority_and_invalid_data(change):
    p = policy()
    if change in {"expected", "command"}:
        p[change] = "anything"
    elif change == "unknown-family":
        p["family"] = "shell"
    elif change == "too-many":
        p["cases"] *= 9
    elif change == "code-input":
        p["cases"][0]["args"] = [object()]
    elif change == "infinite":
        p["cases"][0]["args"] = [float("inf")]
    elif change == "symbol":
        p["target"]["symbol"] = "a();b()"
    elif change == "unknown-case":
        p["cases"][0]["expected"] = True
    elif change == "identity":
        p["identity"]["run_id"] = "../escape"
    else:
        p["producer_sha256"] = "not-a-digest"
    with pytest.raises((ValueError, TypeError)):
        P.validate_policy(p)
