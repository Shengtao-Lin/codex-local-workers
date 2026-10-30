import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from strata_explorer_investigate import read_batch


def tool(name, arguments):
    return {"function": {"name": name, "arguments": arguments}}


def test_preserves_all_original_readonly_tools_in_order():
    names = ["LIST_FILES", "READ_FILE", "SEARCH", "TRACE"]
    calls = [tool(name, '{"symbol":"f","path":"src"}') for name in names]
    actions = read_batch(calls)
    assert [a["action"] for a in actions] == names
    assert all(a["arguments"] == {"symbol": "f", "path": "src"} for a in actions)


@pytest.mark.parametrize(
    "bad",
    [
        None,
        {},
        {"function": []},
        tool("REPORT", "{}"),
        tool("FINISH_SUCCESS", "{}"),
        tool("SAFE_REPLACE", "{}"),
        tool("SHELL", "{}"),
        tool("TRACE", "[]"),
        tool("SEARCH", "bad"),
    ],
)
def test_entire_batch_is_rejected_before_any_action(bad):
    with pytest.raises((ValueError, TypeError)):
        read_batch([tool("READ_FILE", '{"path":"src/a.py"}'), bad])


@pytest.mark.parametrize("count", [0, 1, 5])
def test_read_batch_remains_bounded(count):
    with pytest.raises(ValueError):
        read_batch([tool("READ_FILE", "{}")] * count)
