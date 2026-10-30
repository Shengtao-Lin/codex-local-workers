"""Envelope negatives only, not proof that arbitrary JSON is authentic evidence."""

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from reviewer_capture_envelope import CaptureRejected, parse_command_capture


def fixture():
    bindings = {
        "task_id": "offline",
        "run_id": "one",
        "producer_sha256": "a" * 64,
        "profile_sha256": "b" * 64,
        "source_manifest_sha256": "c" * 64,
    }
    envelope = {
        "schema_version": 1,
        "bindings": bindings,
        "observations": [{"input": None}],
    }
    check = {
        "id": "capture",
        "status": "passed",
        "exit_code": 0,
        "output_truncated": False,
        "argv": ["python", "-B", "capture.py"],
        "output": json.dumps(envelope),
    }
    return check, bindings, envelope


def parse(checks, bindings):
    return parse_command_capture(
        checks,
        check_id="capture",
        argv=["python", "-B", "capture.py"],
        bindings=bindings,
    )


def test_lossless_and_detached():
    check, bindings, _ = fixture()
    assert parse([check], bindings) == [{"input": None}]
    assert parse([check], bindings) is not parse([check], bindings)


@pytest.mark.parametrize(
    "change",
    [
        {"status": "failed"},
        {"exit_code": 1},
        {"exit_code": False},
        {"output_truncated": True},
        {"output_truncated": None},
        {"timed_out": True},
        {"argv": ["other"]},
    ],
)
def test_command_negative(change):
    check, bindings, _ = fixture()
    check.update(change)
    with pytest.raises(CaptureRejected):
        parse([check], bindings)


@pytest.mark.parametrize(
    "output",
    [
        "warning\n{}",
        "{}\nwarning",
        "{} {}",
        '{"x":1,"x":2}',
        '{"x":NaN}',
        '{"x":Infinity}',
        "[]",
        "",
        "x" * 65537,
    ],
    ids=[
        "prefix",
        "suffix",
        "two-json",
        "duplicate-key",
        "nan",
        "infinity",
        "array",
        "empty",
        "oversize",
    ],
)
def test_strict_json_negative(output):
    check, bindings, _ = fixture()
    check["output"] = output
    with pytest.raises(CaptureRejected):
        parse([check], bindings)


@pytest.mark.parametrize(
    "field",
    [
        "task_id",
        "run_id",
        "producer_sha256",
        "profile_sha256",
        "source_manifest_sha256",
    ],
)
def test_binding_negative(field):
    check, bindings, envelope = fixture()
    envelope = copy.deepcopy(envelope)
    envelope["bindings"][field] = "different"
    check["output"] = json.dumps(envelope)
    with pytest.raises(CaptureRejected):
        parse([check], bindings)


@pytest.mark.parametrize("mode", ["missing", "duplicate", "extra", "empty", "boolean"])
def test_envelope_negative(mode):
    check, bindings, envelope = fixture()
    checks = [check]
    if mode == "missing":
        checks = []
    elif mode == "duplicate":
        checks.append(copy.deepcopy(check))
    elif mode == "extra":
        envelope["expected"] = "succeeded"
    elif mode == "empty":
        envelope["observations"] = []
    else:
        envelope["schema_version"] = True
    check["output"] = json.dumps(envelope)
    with pytest.raises(CaptureRejected):
        parse(checks, bindings)
