import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import strata_explorer_trace as candidate


def test_installs_after_existing_adapter_and_preserves_final(monkeypatch):
    order = []

    class Runtime:
        def __init__(self):
            pass

        def execute(self, name, args):
            order.append(name)
            return args["observation"], args.get("final")

    module = SimpleNamespace(ExplorerRuntime=Runtime)
    monkeypatch.setattr(candidate.ARGS, "patch", lambda m, c: order.append("adapter"))
    candidate.patch(module, {})
    runtime = module.ExplorerRuntime()
    observation = {"status": "ok", "definitions": [{"path": "a.py", "line": 1}]}
    first, final = runtime.execute("TRACE", {"observation": observation})
    assert first["new_trace_evidence_count"] == 1 and final is None
    second, _ = runtime.execute("TRACE", {"observation": observation})
    assert second["new_trace_evidence_count"] == 0 and "files" not in second
    untouched, final = runtime.execute(
        "TRACE", {"observation": observation, "final": "stop"}
    )
    assert untouched is observation and final == "stop"
    untouched, _ = runtime.execute("READ_FILE", {"observation": observation})
    assert untouched is observation
    assert order[0] == "adapter"
