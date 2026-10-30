import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from reviewer_required_tool_adapter import install


@pytest.mark.parametrize("tools", [None, [], [{"function": {"name": "REPORT"}}]])
@pytest.mark.parametrize("fail", [False, True])
def test_required_transport_changes_only_native_choice_and_restores_on_exit(
    tools, fail
):
    seen = []
    messages = [{"role": "system", "content": "unchanged"}]
    client = SimpleNamespace(native_tools=tools, native_tool_choice="auto")

    def complete(actual):
        assert actual is messages
        assert client.native_tools is tools
        seen.append(client.native_tool_choice)
        if fail:
            raise ValueError("original failure")
        return "original result"

    client.complete = complete

    class Runtime:
        def __init__(self):
            self.client = client
            self.events = []

        def event(self, name, facts):
            self.events.append((name, facts))

        def run(self):
            return self.client.complete(messages)

    install(SimpleNamespace(ReviewerRuntime=Runtime))
    runtime = Runtime()
    if fail:
        with pytest.raises(ValueError, match="original failure"):
            runtime.run()
    else:
        assert runtime.run() == "original result"
    assert seen == ["required" if tools else "auto"]
    assert client.native_tool_choice == "auto"
    assert client.complete is complete
