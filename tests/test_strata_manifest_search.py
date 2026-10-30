import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from strata_manifest_search import ManifestSearchEvidence


def evidence(tmp_path):
    approved = ["src/pkg/a.py", "src/pkg/b.py", "tests/test_a.py"]
    for name in [*approved, "src/pkg/secret.py"]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("isinstance(x, str)\n", encoding="utf-8")
    calls, saved = [], []
    r = SimpleNamespace(
        config={"experimental_evidence_files": approved},
        ledger={"requests": 1},
        archive=SimpleNamespace(run_root=tmp_path / "archive"),
        RUN_STATE=SimpleNamespace(write_json_once=lambda *args: saved.append(args)),
    )
    r._assert_read_allowed = lambda path: (path, tmp_path / path)
    r.editor = SimpleNamespace(
        read_bytes=lambda path: ((tmp_path / path).read_bytes(), "unchanged")
    )

    def search(args):
        calls.append(args)
        return {
            "results": [{"path": args["path"], "line": 1, "text": "isinstance(x, str)"}]
        }

    r.search = search
    return (
        ManifestSearchEvidence(
            r, policy_error=PermissionError, progress_error=RuntimeError
        ),
        calls,
        saved,
    )


def test_directory_selects_only_manifest_never_secret_or_tests(tmp_path):
    e, calls, saved = evidence(tmp_path)
    e.perform({"search": {"path": "src/pkg", "query": "isinstance("}})
    assert [c["path"] for c in calls] == ["src/pkg/a.py", "src/pkg/b.py"]
    assert all(c["mode"] == "literal" for c in calls)
    assert e.runtime.ledger["evidence_actions"] == 1
    assert saved[0][1]["observation"]["remaining_approved_files"] == 0


@pytest.mark.parametrize(
    "path",
    [".agent", "../src", "src/../src", "F:/src", "src\\pkg", "src/unknown", "src//pkg"],
)
def test_unapproved_or_noncanonical_roots_fail_before_search(tmp_path, path):
    e, calls, _ = evidence(tmp_path)
    with pytest.raises(PermissionError):
        e.perform({"search": {"path": path, "query": "x"}})
    assert not calls


def test_packet_scope_still_can_deny_parent_directory(tmp_path):
    e, calls, _ = evidence(tmp_path)

    def deny(_path):
        raise PermissionError("packet denied")

    e.runtime._assert_read_allowed = deny
    with pytest.raises(PermissionError, match="packet denied"):
        e.perform({"search": {"path": "src", "query": "x"}})
    assert not calls


def test_repeated_search_and_evidence_limits_are_preserved(tmp_path):
    e, _, _ = evidence(tmp_path)
    action = {"search": {"path": "src", "query": "x"}}
    e.perform(action)
    e.perform(action)
    with pytest.raises(RuntimeError, match="duplicate"):
        e.perform(action)
    e.runtime.ledger["evidence_actions"] = 4
    with pytest.raises(RuntimeError, match="exhausted"):
        e.perform({"search": {"path": "src", "query": "new"}})


def test_out_of_manifest_result_is_not_accepted(tmp_path):
    e, _, _ = evidence(tmp_path)
    e.runtime.search = lambda args: {"results": [{"path": "src/pkg/secret.py"}]}
    with pytest.raises(PermissionError, match="escaped"):
        e.perform({"search": {"path": "src", "query": "x"}})


def test_source_changed_during_search_is_rejected(tmp_path):
    e, _, _ = evidence(tmp_path)
    versions = iter(["before", "after"])
    e.runtime.editor.read_bytes = lambda path: (b"source", next(versions))
    with pytest.raises(PermissionError, match="changed"):
        e.perform({"search": {"path": "src", "query": "x"}})


def test_result_cap_reports_unscanned_files(tmp_path):
    e, _calls, saved = evidence(tmp_path)
    e.runtime.search = lambda args: {"results": [{"path": args["path"]}] * 10}
    e.perform({"search": {"path": "src", "query": "x"}})
    obs = saved[0][1]["observation"]
    assert len(obs["results"]) == 10
    assert obs["remaining_approved_files"] == 1
    assert obs["scanned_approved_files"] == ["src/pkg/a.py"]
