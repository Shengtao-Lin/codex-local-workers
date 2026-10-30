import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import failed_test_source as R


def runtime():
    relative = "tests/test_contract.py"
    source = b"class FalseMap(dict):\n    def __bool__(self):\n        return False\n\ndef test_x():\n    assert False\n"
    focused = {
        "status": "failed",
        "inputs_unchanged": True,
        "input_facts": {relative: {"sha256": "hash"}},
        "diagnostic": {
            "failures": [{"test": "test_x", "location": relative + ":6: Failed"}]
        },
    }
    return SimpleNamespace(
        validation=SimpleNamespace(focused_tests=focused),
        packet={"focused_tests": [relative]},
        repo_root=Path("F:/isolated"),
        editor=SimpleNamespace(read_bytes=lambda _p: (source, "hash")),
        validation_count=1,
        _assert_read_allowed=lambda p: (p, None),
        read_file=lambda _a: {},
    )


def test_bound_actual_test_source_not_semantic_fix():
    item = R.collect(runtime(), {})[0]
    assert "def __bool__" in item["source"] and "return False" in item["source"]
    assert item["sha256"] == "hash" and item["failed_line"] == 6
    assert "not host repair advice" in item["meaning"]


@pytest.mark.parametrize(
    "bad", ["stale", "not_focused", "changed", "passed", "bad_line"]
)
def test_no_stale_unapproved_or_unrelated_evidence(bad):
    r = runtime()
    f = r.validation.focused_tests
    if bad == "stale":
        f["input_facts"]["tests/test_contract.py"]["sha256"] = "old"
    elif bad == "not_focused":
        r.packet["focused_tests"] = ["other.py"]
    elif bad == "changed":
        f["inputs_unchanged"] = False
    elif bad == "passed":
        f["status"] = "passed"
    else:
        f["diagnostic"]["failures"][0]["location"] = (
            "tests/test_contract.py:999: Failed"
        )
    assert R.collect(r, {}) == []
