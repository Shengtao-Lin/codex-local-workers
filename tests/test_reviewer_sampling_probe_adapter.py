import importlib.util
from pathlib import Path
from types import SimpleNamespace


def test_sampling_probe_observes_changes_and_restores_client_without_prompt_changes():
    path = (
        Path(__file__).resolve().parents[1]
        / "benchmarks/reviewer_sampling_probe_adapter.py"
    )
    spec = importlib.util.spec_from_file_location("sampling_probe_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    seen = []
    events = []
    messages = [{"role": "user", "content": "unchanged"}]
    client = SimpleNamespace(
        temperature=1.0, complete=lambda value: seen.append(value) or "same response"
    )
    original_complete = client.complete

    class Runtime:
        def __init__(self):
            self.client = client
            self.event = lambda name, facts: events.append((name, facts))

        def run(self):
            assert self.client.complete(messages) == "same response"
            self.client.temperature = 0.0
            assert self.client.complete(messages) == "same response"
            return "original verdict"

    module.install(SimpleNamespace(ReviewerRuntime=Runtime))
    assert Runtime().run() == "original verdict"
    assert seen == [messages, messages]
    assert [facts["temperature"] for _, facts in events] == [1.0, 0.0]
    assert client.complete is original_complete
