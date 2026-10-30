"""Advice is source-bound, untrusted, cannot accept or bypass edit protections."""

import copy
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import semantic_advice_diagnostic as S


def fixture():
    return S.T.read(S.BATCH / "fixture.json")


def valid():
    f = fixture()
    return {"binding_id": f["evidence"]["binding_id"], "cause": "untrusted cause",
            "required_change": "untrusted recommendation", "evidence_ids": ["E1"]}


def test_valid_materializes_exact_displayed_source():
    f = fixture()
    result = S.advice(json.dumps(valid()), f)
    assert result["source_citations"] == [f["evidence"]["citation_evidence"]["E1"]]
    assert result["authority"] == "untrusted_advice_only_not_acceptance"


@pytest.mark.parametrize("change", [
    {"binding_id": "old"}, {"evidence_ids": ["unread"]},
    {"evidence_ids": ["E1", "E1"]}, {"evidence_ids": []},
    {"cause": ""}, {"required_change": "x" * 2001},
    {"validation_passed": True}, {"accept": True},
    {"source_citations": [{"path": "fake", "quote": "fake"}]},
])
def test_invalid_advice_rejected(change):
    with pytest.raises(ValueError):
        S.advice(json.dumps({**valid(), **change}), fixture())


def test_duplicate_json_key_rejected():
    raw = json.dumps(valid())
    with pytest.raises(ValueError):
        S.advice(raw[:-1] + ',"cause":"duplicate"}', fixture())


def test_stale_evidence_rejected(tmp_path):
    f = fixture()
    old = tmp_path / "source.py"
    old.write_text("before", encoding="utf-8")
    f["evidence"]["pins"] = {str(old): S.T.sha(old)}
    e = f["evidence"]
    e["binding_id"] = S.digest({k: v for k, v in e.items() if k != "binding_id"})
    old.write_text("after", encoding="utf-8")
    with pytest.raises(ValueError, match="stale"):
        S.advice(json.dumps({**valid(), "binding_id": e["binding_id"]}), f)


def test_only_difference_is_untrusted_advice():
    f = fixture()
    before = copy.deepcopy(f)
    a = S.messages(f)
    b = S.messages(f, S.advice(json.dumps(valid()), f))
    fa = S.D.INTERFACE.restore_literal(a[1]["content"])
    fb = S.D.INTERFACE.restore_literal(b[1]["content"])
    assert fb.pop("untrusted_semantic_advice")["authority"] == "untrusted_advice_only_not_acceptance"
    assert a[0] == b[0] and fa == fb and f == before


def test_pristine_and_ancestor_freeze():
    f = fixture()
    assert S.T.sha(S.BATCH / "snapshot.py") == f["binding"]["sha256"]
    for row in S.T.read(S.BATCH / "cells.json").values():
        assert all(S.T.sha(Path(row["root"]) / p) == sha for p, sha in row["files"].items())
        assert not (Path(row["root"]) / ".agent").exists()
    assert all(S.T.sha(p) == sha for p, sha in S.T.read(S.P.BATCH / "freeze.json")["pins"].items())


def test_original_edit_guard_and_25_checks_positive(tmp_path):
    f = fixture()
    seed = Path(S.T.read(S.BATCH / "cells.json")["direct-1"]["root"])
    root = tmp_path / "isolated"
    shutil.copytree(seed, root)
    # Prior accepted real implementation is an OFFLINE control only, never model input.
    reference = S.C.N.BATCH / "cases/messages_output-candidate-1/isolated" / f["binding"]["path"]
    function = S.D.BOUNDARY.target(reference.read_text(encoding="utf-8"), "messages_output")[3]
    assert S.D.apply(root, json.dumps({"replacement": function}), "whole", f)["applied"]
    commands = [
        [S.M.PYTHON, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
         "tests/test_messages_output.py", S.C.N.BATCH / "private/messages_output/test_private_messages_output.py"],
        [S.M.PYTHON, "-B", "-m", "ruff", "format", "--check", "src", "tests"],
        [S.M.PYTHON, "-B", "-m", "ruff", "check", "src", "tests"],
        [S.M.PYTHON, "-B", "-m", "pyright", "--pythonpath", S.M.PYTHON]]
    for cmd in commands:
        check = S.M.command(cmd, root, {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(root / "src")})
        assert check["exit_code"] == 0, check
    assert "25 passed" in S.M.command(commands[0], root, {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(root / "src")})["stdout"]


def test_original_edit_guard_stale_negative(tmp_path):
    f = fixture()
    row = S.T.read(S.BATCH / "cells.json")["direct-1"]
    root = tmp_path / "isolated"
    shutil.copytree(row["root"], root)
    f["binding"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="Source differs"):
        S.D.apply(root, "{}", "whole", f)
    assert all(S.T.sha(root / p) == sha for p, sha in row["files"].items())
