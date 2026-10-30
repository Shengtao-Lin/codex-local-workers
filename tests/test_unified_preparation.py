"""Unified preparation, actual cap accounting, and header location negatives."""

import copy
import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import capture_coder_entry as BIND
import capture_fixture_support as F
import coder_output_channel as OUTPUT
import coder_prevalidation_format as PREPARE
import coder_unified_preparation as U
import reviewer_canonical_capture as C
import unified_preparation_trial as TRIAL


@pytest.mark.parametrize(
    "change",
    [
        "none",
        "multiple",
        "wrong_file",
        "outer",
        "body",
        "no_count",
        "wrong_check",
        "passed",
    ],
)
def test_ruff_locations_do_not_expand_header_scope(change):
    row = TRIAL.T.read(TRIAL.R.BATCH / "cells.json")["rework-1"]
    root = Path(row["root"])
    source = (root / "src/product/metadata.py").read_text(encoding="utf-8")
    _, start, end, block = U.SPAN.D.BOUNDARY.target(source, "validate_metadata")
    binding = {
        "path": "src/product/metadata.py",
        "symbol": "validate_metadata",
        "start_line": start,
        "end_line": end,
        "source": block,
    }
    validation = TRIAL.T.read(
        root
        / ".agent/tasks/fresh-metadata/runs/cycle-recovery-1/validation-attempt-3.json"
    )["validation"]
    check = copy.deepcopy(validation["configured_checks"][-1])
    assert check["id"] == "ruff-check"
    line = next(
        i for i, text in enumerate(source.splitlines(), 1) if "def check_finite" in text
    )
    if change == "multiple":
        check["output"] += "\nRUF013 another\n  --> src/product/metadata.py:18:1\n"
    elif change == "wrong_file":
        check["output"] = check["output"].replace("metadata.py:", "protected.py:")
    elif change in {"outer", "body"}:
        check["output"] = check["output"].replace(
            f":{line}:", f":{start if change == 'outer' else line + 1}:"
        )
    elif change == "no_count":
        check["output"] = check["output"].replace("Found 1 error.", "Found 2 errors.")
    elif change == "wrong_check":
        check["id"] = "untrusted-formatter"
    elif change == "passed":
        check["status"] = "passed"
    found = U.locate_ruff(
        {"validation_failure": {"configured_checks": [check]}}, binding, source, root
    )
    assert (found is not None) is (change == "none")


@pytest.mark.parametrize("tamper", ["none", "source"])
def test_real_repair_and_canonical_gate_with_one_formatter_three_checks(
    tmp_path, tamper
):
    row = TRIAL.T.read(TRIAL.BATCH / "cells.json")["new-1"]
    root = tmp_path / "isolated"
    shutil.copytree(row["root"], root)
    packet, config = (
        TRIAL.T.read(root / ".agent/packet.json"),
        TRIAL.T.read(root / ".agent/config.json"),
    )
    worker = F.load(
        root / ".local-agents/worker-runtime.py", "unified_offline_" + tmp_path.name
    )
    host = F.load(
        root / ".local-agents/host-proposal.py", "unified_host_" + tmp_path.name
    )
    BIND.install(worker, F.POLICY_PATH, row["policy_sha256"])
    cls = U.make_runtime(
        worker,
        host,
        PREPARE.make_runtime(worker, OUTPUT.make_runtime(worker, host, "schema")),
    )
    old = Path(TRIAL.T.read(TRIAL.R.BATCH / "cells.json")["rework-1"]["root"])
    first = TRIAL.T.read(
        old
        / ".agent/tasks/fresh-metadata/runs/cycle-recovery-1/proposal-response-1.json"
    )["raw"]

    class Client:
        timeout = 180
        structured_output = True
        action_schema = U.SPAN.D.INTERFACE.WHOLE_SCHEMA
        native_tools = None
        typed_action_arguments = False
        calls = 0

        def complete(self, messages):
            self.calls += 1
            if self.calls == 1:
                return first
            facts = host.INTERFACE.restore_literal(messages[1]["content"])
            assert "RUF013" in json.dumps(facts["validation_failure"])
            assert "repair_span" in facts
            line = facts["repair_span"]["source"]
            assert "seen: set[int] = None" in line
            return json.dumps(
                {
                    "replacement": line.replace(
                        "seen: set[int] = None", "seen: set[int] | None = None"
                    )
                }
            )

    client = Client()
    runtime = cls(root, packet, config, client)
    runtime.preflight()
    commands = []
    original = runtime._run_command

    def command(argv):
        commands.append(argv)
        return original(argv)

    runtime._run_command = command
    report = runtime.run()
    assert report["status"] == "validation_passed_pending_review", report.get(
        "failure_reason"
    )
    assert (
        client.calls == 2 and runtime.validation_count == 3 and runtime.host_edits == 2
    )
    assert runtime.edit_revision == 3
    assert sum("format" in a and "--check" not in a for a in commands) == 1
    assert sum("pytest" in a for a in commands) == 3
    assert sum("format" in a and "--check" in a for a in commands) <= 3
    assert not (runtime.archive.run_root / "validation-attempt-4.json").exists()
    receipt = TRIAL.T.read(runtime.archive.run_root / "unified-format-preparation.json")
    assert receipt["validation_count_before"] == receipt["validation_count_after"] == 1
    assert receipt["acceptance_credit"] is False
    request = {k: packet[k] for k in ("task_id", "unit_id", "run_id")}
    request.update(
        review_id="unified-offline-review",
        execution_protocol=report["execution_protocol"],
    )
    reviewer_module = F.load(
        root / ".local-agents/reviewer-runtime.py", "unified_reviewer_" + tmp_path.name
    )
    reviewer = reviewer_module.ReviewerRuntime(root, request, config, object())
    if tamper == "source":
        path = root / "src/product/metadata.py"
        path.write_bytes(path.read_bytes() + b"\n# stale\n")
        with pytest.raises((ValueError, RuntimeError)):
            C.load_capture(reviewer, F.POLICY_PATH, row["policy_sha256"])
    else:
        assert C.load_capture(reviewer, F.POLICY_PATH, row["policy_sha256"])[0]


def test_no_counter_refund_or_extra_formatter_after_cap():
    class Worker:
        WorkerError = RuntimeError
        PolicyViolation = RuntimeError

    class Interface:
        WHOLE_PROMPT = "original"
        normalize_whole = None

    class Host:
        INTERFACE = Interface()

    class Parent:
        def __init__(self, *args):
            self.host_check_cap = self.validation_count = 3

    cls = U.make_runtime(Worker, Host, Parent)
    runtime = cls(
        None,
        None,
        {
            "experimental_unified_preparation": True,
            "experimental_static_span_repair": True,
        },
        None,
    )
    with pytest.raises(RuntimeError, match="budget exhausted"):
        runtime.host_validate()
