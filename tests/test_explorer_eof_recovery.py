"""EOF formatting repair must not masquerade as missing source evidence."""

import importlib.util
import json
import sys
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "explorer_eof_regression",
    Path(__file__).parents[1] / ".local-agents/explorer-runtime.py",
)
RUNTIME = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNTIME
SPEC.loader.exec_module(RUNTIME)


class Client:
    def __init__(self, actions):
        self.actions = iter(actions)
        self.native_tools = RUNTIME.EXPLORER_TOOLS
        self.native_tool_choice = "auto"
        self.requests = []

    def complete(self, messages):
        self.requests.append(
            {
                "tools": [t["function"]["name"] for t in self.native_tools],
                "messages": list(messages),
            }
        )
        return json.dumps(next(self.actions))


def tree(root):
    (root / "tests").mkdir()
    (root / "entry.py").write_text(
        "def entry():\n    a = 1\n    b = 2\n    c = 3\n    return a + b + c\n",
        encoding="utf-8",
    )
    (root / "tests/test_entry.py").write_text(
        "from entry import entry\n\ndef test_entry():\n    assert entry() == 6\n",
        encoding="utf-8",
    )


def read(path, start=1, end=99):
    return {"action": "READ_FILE", "path": path, "start_line": start, "end_line": end}


def finish(end=5):
    return {
        "action": "FINISH_SUCCESS",
        "source_refs": [
            {
                "path": "entry.py",
                "start_line": 1,
                "end_line": end,
                "kind": "implementation",
            },
            {
                "path": "tests/test_entry.py",
                "start_line": 4,
                "end_line": 4,
                "kind": "test",
            },
        ],
        "uncertainties": [],
    }


def run(root, actions):
    tree(root)
    client = Client(actions)
    runtime = RUNTIME.ExplorerRuntime(
        root,
        "Locate entry and its assertion.",
        {
            "explorer_mode": "locate",
            "explorer_required_citation_paths": ["entry.py", "tests/test_entry.py"],
            "explorer_require_test_assertion_citation": True,
            "explorer_duplicate_action_report_recovery": True,
        },
        client,
    )
    return runtime.run(), client


def observation(request):
    return json.loads(request["messages"][-1]["content"].split("\n", 1)[1])


def test_eof_after_all_reads_gets_single_report_only_correction(tmp_path):
    result, client = run(
        tmp_path, [read("entry.py"), read("tests/test_entry.py"), finish(6), finish()]
    )
    feedback = observation(client.requests[3])
    assert result["status"] == "success"
    assert client.requests[3]["tools"] == ["FINISH_SUCCESS"]
    assert feedback["source_ref_error"]["category"] == "beyond_eof"
    assert "READ_FILE the missing" not in feedback["next_step"]
    assert result["budget_usage"]["protocol_errors"] == 1
    assert len(client.requests) == 4


def test_real_unread_range_retains_read_recovery(tmp_path):
    result, client = run(
        tmp_path,
        [
            read("entry.py", 1, 2),
            read("tests/test_entry.py"),
            finish(),
            read("entry.py", 3, 5),
            finish(),
        ],
    )
    assert result["status"] == "success"
    assert "READ_FILE" in client.requests[3]["tools"]
    assert (
        observation(client.requests[3])["source_ref_error"]["category"]
        == "unread_range"
    )


def test_eof_with_unread_required_file_does_not_force_premature_terminal(tmp_path):
    result, client = run(
        tmp_path, [read("entry.py"), finish(6), read("tests/test_entry.py"), finish()]
    )
    assert result["status"] == "success"
    feedback = observation(client.requests[2])
    assert "READ_FILE" in client.requests[2]["tools"]
    assert feedback["source_ref_error"]["read_paths"] == ["tests/test_entry.py"]
    assert "tests/test_entry.py" in feedback["next_step"]


def test_second_eof_report_fails_closed_without_clipping(tmp_path):
    result, client = run(
        tmp_path, [read("entry.py"), read("tests/test_entry.py"), finish(6), finish(6)]
    )
    assert result["status"] == "failed"
    assert "source_refs" not in result
    assert len(client.requests) == 4


def test_report_only_refuses_read_before_execution(tmp_path):
    result, client = run(
        tmp_path,
        [read("entry.py"), read("tests/test_entry.py"), finish(6), read("entry.py")],
    )
    assert result["status"] == "failed"
    assert len(client.requests) == 4
    assert len([a for a in result["action_trace"] if a["action"] == "READ_FILE"]) == 2


def test_missing_required_ref_to_unread_file_retains_read_recovery(tmp_path):
    partial = finish()
    partial["source_refs"] = partial["source_refs"][:1]
    result, client = run(
        tmp_path, [read("entry.py"), partial, read("tests/test_entry.py"), finish()]
    )
    assert result["status"] == "success"
    assert "READ_FILE" in client.requests[2]["tools"]
    assert (
        observation(client.requests[2])["source_ref_error"]["category"]
        == "missing_required_paths"
    )


def test_missing_required_ref_to_already_read_file_is_report_only(tmp_path):
    partial = finish()
    partial["source_refs"] = partial["source_refs"][:1]
    result, client = run(
        tmp_path, [read("entry.py"), read("tests/test_entry.py"), partial, finish()]
    )
    assert result["status"] == "success"
    assert client.requests[3]["tools"] == ["FINISH_SUCCESS"]


def test_changed_source_hash_cannot_be_repaired_by_report_only(tmp_path):
    def actions():
        yield read("entry.py")
        yield read("tests/test_entry.py")
        path = tmp_path / "entry.py"
        path.write_text(
            path.read_text(encoding="utf-8").replace("a = 1", "a = 9"), encoding="utf-8"
        )
        yield finish()
        yield finish()

    result, client = run(tmp_path, actions())
    assert result["status"] == "failed"
    assert "source_refs" not in result
    assert client.requests[3]["tools"] == ["FINISH_SUCCESS"]
