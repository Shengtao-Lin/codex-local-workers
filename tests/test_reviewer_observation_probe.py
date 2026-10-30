"""No-model observation proof and rejection of executable/path/size inputs."""

import copy
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import reviewer_observation_probe as P


@pytest.mark.parametrize(
    "change",
    [
        "path",
        "code",
        "command",
        "fixture",
        "empty",
        "many_cases",
        "many_parts",
        "bad_part",
        "unknown_type",
        "extra_field",
        "name_type",
        "nan",
        "huge_int",
        "long_string",
        "deep",
        "too_many_bytes",
    ],
)
def test_bad_request_never_launches_or_writes(tmp_path, change):
    request = copy.deepcopy(P.boundary_request())
    if change in {"path", "code", "command", "fixture"}:
        request[change] = "unapproved"
    elif change == "empty":
        request["cases"] = []
    elif change == "many_cases":
        request["cases"] *= 2
    elif change == "many_parts":
        request["cases"][0]["parts"] *= 9
    elif change == "bad_part":
        request["cases"][0]["parts"][0] = None
    elif change == "unknown_type":
        request["cases"][0]["parts"][0]["type"] = "python"
    elif change == "extra_field":
        request["cases"][0]["parts"][0]["module"] = "os"
    elif change == "name_type":
        request["cases"][0]["parts"][0]["name"] = []
    elif change == "nan":
        request["cases"][0]["parts"][1]["result"] = float("nan")
    elif change == "huge_int":
        request["cases"][0]["parts"][1]["result"] = 10**1000
    elif change == "long_string":
        request["cases"][0]["parts"][1]["result"] = "x" * 2049
    elif change == "deep":
        value = {}
        for _ in range(10):
            value = {"x": value}
        request["cases"][0]["parts"][1]["result"] = value
    else:
        request["cases"] = request["cases"][:1]
        request["cases"][0]["parts"][0]["arguments"] = {
            str(i): "x" * 2048 for i in range(4)
        }
    with (
        patch.object(P.subprocess, "run") as child,
        pytest.raises((ValueError, TypeError)),
    ):
        P.execute("sample-17-candidate", request, tmp_path)
    child.assert_not_called()
    assert not list(tmp_path.iterdir())


def test_unapproved_fixture_rejected_before_execution():
    with (
        patch.object(P.subprocess, "run") as child,
        pytest.raises(ValueError, match="not approved"),
    ):
        P.fixture("../../outside")
    child.assert_not_called()


def test_immutable_source_guard_rejects_before_execution():
    with (
        patch.object(P.H.R, "assert_files", side_effect=ValueError("source changed")),
        patch.object(P.subprocess, "run") as child,
        pytest.raises(ValueError, match="source changed"),
    ):
        P.execute(
            "sample-17-candidate", P.boundary_request(), P.BATCH / "negative-guard"
        )
    child.assert_not_called()


def test_primary_archive_cannot_escape_design_batch(tmp_path):
    outside = P.BATCH.parent / ("negative-probe-escape-" + tmp_path.name)
    with (
        patch.object(P.subprocess, "run") as child,
        pytest.raises(ValueError, match="archive must stay"),
    ):
        P.execute("sample-17-candidate", P.boundary_request(), outside)
    child.assert_not_called()
    assert not outside.exists()


def test_six_json_values_preserve_types_and_no_oracle():
    request = P.boundary_request()
    assert P.validate_request(request) is request
    values = [c["parts"][1]["result"] for c in request["cases"]]
    assert [type(v) for v in values] == [type(None), bool, int, str, list, dict]
    assert "expected" not in json.dumps(request) and "gold" not in json.dumps(request)


@pytest.mark.parametrize("fixture", ["sample-17-candidate", "sample-18-candidate"])
def test_actual_archived_child_observations_are_source_bound(fixture):
    row = P.fixture(fixture)
    archive = P.BATCH / fixture
    execution = P.B.read(archive / "execution.json")
    result = P.B.read(archive / "observation.json")
    assert execution["exit_code"] == 0 and execution["timeout_seconds"] == 30
    assert execution["argv"][0] == str(P.PYTHON) and execution["argv"][1] == "-B"
    assert result["execution_completed"] and result["semantic_verdict"] is None
    assert result["source"]["sha256"] == row["files"][P.TARGET]
    assert len(result["observations"]) == 6
    statuses = []
    for observation, value in zip(
        result["observations"], (None, False, 0, "", [], {}), strict=True
    ):
        assert observation["input_before"] == observation["input_after"]
        output = observation["outcome"]["value"][0]
        assert type(output["result"]) is type(value)
        assert output["result"] == value
        statuses.append(output["status"])
    assert statuses == (
        ["requested", *["succeeded"] * 5]
        if fixture == "sample-17-candidate"
        else ["succeeded"] * 6
    )
    P.H.R.assert_files(Path(row["root"]), row["files"])
