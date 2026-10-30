import ast
import copy
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import reviewer_assembled_request_adapter as adapter


def run_wrappers(wire_last):
    initial = [
        {"role": "system", "content": "contract"},
        {"role": "user", "content": "packet"},
    ]
    dialogue = [
        {
            "role": "assistant" if index % 2 == 0 else "user",
            "content": ("action" if index % 2 == 0 else "OBSERVATION\n") + "x" * 150,
        }
        for index in range(14)
    ]
    seen = []
    events = []

    class Runtime:
        def __init__(self):
            self.client = SimpleNamespace(
                complete=self.complete,
                native_tools=[],
                context_length=1200,
                max_tokens=100,
                context_safety_margin=100,
            )
            self.context_recovery = False
            self.read_lines = {"source.py": {1}}

        def complete(self, messages):
            seen.append(copy.deepcopy(messages))
            return "unchanged response"

        def event(self, name, facts):
            events.append((name, facts))

        def run(self):
            return self.client.complete([*initial, *dialogue])

    reviewer = SimpleNamespace(ReviewerRuntime=Runtime)

    def add_state():
        original = Runtime.run

        def run(runtime):
            complete = runtime.client.complete

            def assembled(messages):
                runtime.client.native_tools = [{"schema": "y" * 1800}]
                return complete(
                    [
                        *messages,
                        {
                            "role": "user",
                            "content": "CURRENT_CONTROLLER_STATE " + "z" * 200,
                        },
                    ]
                )

            runtime.client.complete = assembled
            try:
                return original(runtime)
            finally:
                runtime.client.complete = complete

        Runtime.run = run

    if wire_last:
        add_state()
        adapter.install(reviewer)
    else:
        adapter.install(reviewer)
        add_state()
    runtime = Runtime()
    original_complete = runtime.client.complete
    assert runtime.run() == "unchanged response"
    assert runtime.client.complete == original_complete
    assert runtime.read_lines == {"source.py": {1}}
    assert seen[0][:2] == initial
    assert seen[0][-11:] == [
        *dialogue[-10:],
        {"role": "user", "content": "CURRENT_CONTROLLER_STATE " + "z" * 200},
    ]
    return seen[0], events


def test_actual_wrapper_order_budgets_after_added_prompt_and_schema():
    wrong, wrong_events = run_wrappers(False)
    corrected, events = run_wrappers(True)
    assert not wrong_events
    assert (sum(len(message["content"]) for message in wrong) + 1800 + 3) // 4 > 1000
    assert (
        sum(len(message["content"]) for message in corrected) + 1800 + 3
    ) // 4 <= 1000
    assert events[0][0] == "assembled_wire_context_trim"


def test_live_adapter_installs_budget_wrapper_last():
    tree = ast.parse(Path(adapter.__file__).read_text(encoding="utf-8"))
    main = next(node for node in tree.body if isinstance(node, ast.If))
    calls = [
        node.value.func.id
        for node in main.body
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id.startswith("install")
    ]
    assert calls[-1] == "install"
    assert calls.index("install_analogy") < calls.index("install")
