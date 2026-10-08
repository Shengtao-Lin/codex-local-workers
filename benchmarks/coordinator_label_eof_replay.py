"""Synthetic EOF feedback witness; no live Explorer qualification credit."""

import importlib.util
import json
import sys
from pathlib import Path

import coordinator_label_pilot as pilot
from capability_fit import write
from inherited_context_recovery import digest, read


def main():
    pilot.configure()
    pilot.matrix.verify()
    spec = importlib.util.spec_from_file_location(
        "label_eof_witness_runtime",
        pilot.SNAPSHOT / ".local-agents/explorer-runtime.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    root = pilot.BASE / "oracle-checks/labelled-receipt/mutant-0"
    paths = [
        "src/product/entry.py",
        "src/product/target.py",
        "src/product/labels.py",
        "src/product/collector.py",
        "tests/test_target.py",
    ]
    before = {p: digest(root / p) for p in paths}

    class Client:
        native_tools = module.EXPLORER_TOOLS
        native_tool_choice = "auto"

        def __init__(self):
            self.turn = 0
            self.observation = None
            self.tools_at_correction = None

        def complete(self, messages):
            self.turn += 1
            if self.turn <= len(paths):
                return json.dumps({"action": "READ_FILE", "path": paths[self.turn - 1]})
            if self.turn == 7:
                self.observation = json.loads(messages[-1]["content"].split("\n", 1)[1])
                self.tools_at_correction = [
                    t["function"]["name"] for t in self.native_tools
                ]
            return json.dumps(
                {
                    "action": "FINISH_SUCCESS",
                    "source_refs": [
                        {
                            "path": paths[0],
                            "start_line": 4,
                            "end_line": 6 if self.turn == 6 else 5,
                            "kind": "caller",
                        },
                        {
                            "path": paths[1],
                            "start_line": 5,
                            "end_line": 8,
                            "kind": "implementation",
                        },
                        {
                            "path": paths[2],
                            "start_line": 1,
                            "end_line": 2,
                            "kind": "definition",
                        },
                        {
                            "path": paths[3],
                            "start_line": 1,
                            "end_line": 5,
                            "kind": "definition",
                        },
                        {
                            "path": paths[4],
                            "start_line": 48,
                            "end_line": 60,
                            "kind": "test",
                        },
                    ],
                    "uncertainties": [],
                }
            )

    cell = pilot.matrix.verify()["cells"][0]
    config = read(Path(cell["root"]) / ".agent/config.json")
    client = Client()
    runtime = module.ExplorerRuntime(
        root, "Synthetic EOF feedback witness, not qualification.", config, client
    )
    report = runtime.run()
    contradiction = (
        "another READ_FILE cannot create a line beyond EOF"
        in client.observation["error"]
        and "READ_FILE the missing" in client.observation["next_step"]
        and "READ_FILE" in client.tools_at_correction
    )
    if (
        not contradiction
        or report["status"] != "success"
        or before != {p: digest(root / p) for p in paths}
    ):
        raise ValueError("EOF feedback witness did not reproduce cleanly")
    facts = {
        "synthetic": True,
        "model_requests": 0,
        "qualification_credit": False,
        "feedback_conflict_reproduced": contradiction,
        "observation_at_correction": client.observation,
        "allowed_tools_at_correction": client.tools_at_correction,
        "corrected_mock_report_status": report["status"],
        "source_inputs_unchanged": True,
        "driver_sha256": digest(Path(__file__)),
        "runtime_sha256": digest(pilot.SNAPSHOT / ".local-agents/explorer-runtime.py"),
        "interpretation": "All five files already read; EOF rejection still selects needs_read and leaves read tools available. This proves contradictory runtime feedback, not sole causation of a live model choice or a repaired runtime.",
    }
    write(pilot.BASE / "eof-feedback-witness-1.json", facts)
    print(json.dumps(facts))


if __name__ == "__main__":
    main()
