"""Oversized reports cannot lock unread required evidence out of recovery."""

from test_explorer_eof_recovery import RUNTIME, Client, finish, observation, read


def run(root, actions):
    (root / "tests").mkdir()
    (root / "entry.py").write_text(
        "def entry():\n    return 6\n" + "# padding\n" * 90, encoding="utf-8"
    )
    (root / "tests/test_entry.py").write_text(
        "from entry import entry\n\ndef test_entry():\n    assert entry() == 6\n",
        encoding="utf-8",
    )
    client = Client(actions)
    runtime = RUNTIME.ExplorerRuntime(
        root,
        "Locate entry and its protected assertion.",
        {
            "explorer_mode": "locate",
            "explorer_required_citation_paths": ["entry.py", "tests/test_entry.py"],
            "explorer_require_test_assertion_citation": True,
        },
        client,
    )
    return runtime.run(), client


def test_oversized_report_missing_test_keeps_real_read_available(tmp_path):
    result, client = run(
        tmp_path, [read("entry.py"), finish(81), read("tests/test_entry.py"), finish(2)]
    )
    assert result["status"] == "success"
    feedback = observation(client.requests[2])
    assert "READ_FILE" in client.requests[2]["tools"]
    assert feedback["source_ref_error"] == {
        "category": "line_budget",
        "read_paths": ["tests/test_entry.py"],
    }
    assert result["budget_usage"]["protocol_errors"] == 1


def test_oversized_report_with_complete_evidence_is_one_shot_final_only(tmp_path):
    result, client = run(
        tmp_path, [read("entry.py"), read("tests/test_entry.py"), finish(81), finish(2)]
    )
    assert result["status"] == "success"
    assert client.requests[3]["tools"] == ["FINISH_SUCCESS"]
    assert observation(client.requests[3])["source_ref_error"]["read_paths"] == []


def test_second_oversized_report_cannot_be_clipped_into_success(tmp_path):
    result, client = run(
        tmp_path,
        [read("entry.py"), read("tests/test_entry.py"), finish(81), finish(81)],
    )
    assert result["status"] == "failed"
    assert "source_refs" not in result
    assert len(client.requests) == 4


def test_incomplete_evidence_cannot_be_accepted_by_shortening_report(tmp_path):
    result, _ = run(tmp_path, [read("entry.py"), finish(81), finish(2)] * 5)
    assert result["status"] == "failed"
    assert "source_refs" not in result


def test_complete_evidence_report_only_read_is_rejected_before_execution(tmp_path):
    result, _ = run(
        tmp_path,
        [read("entry.py"), read("tests/test_entry.py"), finish(81), read("entry.py")],
    )
    assert result["status"] == "failed"
    assert len([a for a in result["action_trace"] if a["action"] == "READ_FILE"]) == 2


def test_count_repair_keeps_all_six_required_files_explicit(tmp_path):
    paths = ["entry.py", "tests/test_entry.py", "a.py", "b.py", "c.py", "d.py"]
    (tmp_path / "tests").mkdir()
    for path in paths:
        (tmp_path / path).write_text("assert True\n", encoding="utf-8")
    refs = [
        {
            "path": p,
            "start_line": 1,
            "end_line": 1,
            "kind": "test" if p.startswith("tests/") else "implementation",
        }
        for p in paths
    ]
    valid = {"action": "FINISH_SUCCESS", "source_refs": refs, "uncertainties": []}
    invalid = {**valid, "source_refs": [*refs, refs[-1]]}
    client = Client([*[read(p) for p in paths], invalid, valid])
    runtime = RUNTIME.ExplorerRuntime(
        tmp_path,
        "Locate six required files.",
        {
            "explorer_mode": "locate",
            "explorer_required_citation_paths": paths,
            "explorer_require_test_assertion_citation": True,
        },
        client,
    )
    result = runtime.run()
    assert result["status"] == "success"
    feedback = observation(client.requests[7])
    assert feedback["required_citation_paths"] == sorted(paths)
    assert "exactly six reference objects" in feedback["next_step"]
    assert client.requests[7]["tools"] == ["FINISH_SUCCESS"]
    assert len(result["source_refs"]) == 6
