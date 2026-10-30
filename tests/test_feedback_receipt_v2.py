"""Control the actual subprocess command and receiver installation."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import feedback_receipt_entry as ENTRY
import feedback_recovery_trial_v2 as V2
from test_bounded_evidence_candidate import build  # noqa: F401
from test_evidence_budget_preparation import setup_runtime  # noqa: F401


def test_actual_command():
    old = V2.V1.S.KIT / "benchmarks/bounded_evidence_unit.py"
    new = V2.V1.S.KIT / "benchmarks/feedback_receipt_unit.py"
    assert V2.unit_argv(["python", "-B", old, "--packet", "packet.json"]) == [
        "python",
        "-B",
        str(new),
        "--packet",
        "packet.json",
    ]
    assert V2.unit_argv(["python", "checks.py"]) == ["python", "checks.py"]


def test_entry_receiver(request):
    def noop(messages, _worker, host):
        facts = host.INTERFACE.restore_literal(messages[1]["content"])
        return json.dumps({"replacement": facts["target"]["source"]})

    runtime, worker, host = request.getfixturevalue("build")([noop, noop], "A")
    config = {**runtime.config, "experimental_explicit_noop_receipt": True}
    fresh_host = ENTRY.ENTRY.F.load(Path(host.__file__), "receipt_entry_control_host")
    cls = ENTRY.make_runtime(worker, fresh_host)
    receiver = cls(runtime.repo_root, runtime.packet, config, runtime.client)
    receiver.preflight()
    result = receiver.run()
    assert result["bounded_evidence"]["actual"]["noops"] == 2
    raw = json.loads(
        (receiver.archive.run_root / "proposal-request-2.json").read_text()
    )
    facts = host.INTERFACE.restore_literal(raw["messages"][1]["content"])
    assert facts["host_receipt"]["recent"][-1] == {
        "status": "no_op",
        "source_sha256": facts["target"]["sha256"],
    }
