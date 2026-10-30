"""Offline R3 prototype: explicit host facts, never legacy acknowledgement.

This is not a distributable entry point and does not dispatch a Reviewer.
Live qualification requires a separately authorized protocol receiver.
"""

from pathlib import Path
import json
import xml.etree.ElementTree as ET

import harness_convergence_r2 as diagnostic

WORKER = diagnostic.load_runtime()
PROTOCOL = "host-proposal-v1"
PENDING = "validation_passed_pending_review"


class HostProposalRuntime(WORKER.WorkerRuntime):
    def __init__(self, root, packet, config, client):
        if config.get("host_proposal_enabled") is not True:
            raise WORKER.WorkerError("Host proposal mode requires explicit trusted opt-in")
        super().__init__(root, packet, config, client)
        if self.single_function is None:
            raise WORKER.WorkerError("Host proposal mode requires a single-function scope")
        self._host_validation_active = False

    def _contract_check(self, args, *, diagnostic=False):
        if self._host_validation_active and diagnostic and not args:
            return None
        return super()._contract_check(args, diagnostic=diagnostic)

    def validate_host(self):
        if self._host_validation_active:
            raise WORKER.WorkerError("Nested host validation is forbidden")
        self._host_validation_active = True
        try:
            return super().validate({"phase": "check"})
        finally:
            self._host_validation_active = False

    def complete_host(self):
        if not self.changed or self.edit_revision == 0:
            raise WORKER.WorkerError("A green baseline is not an implemented unit")
        if self.validation is None or self.validation.status != "passed":
            raise WORKER.WorkerError("Current host validation has not passed")
        if self.validated_input_facts != self._validation_facts():
            raise WORKER.WorkerError("Validation inputs changed after host checks")
        # Never reinterpret this as legacy ready_for_review/final validation.
        if self.validation.contract_check is not None or self.last_contract_check is not None:
            raise WORKER.WorkerError("Host facts must not contain synthesized worker assessment")
        WORKER.RUN_STATE.write_json_once(self.archive.run_root / "execution-protocol.json", {
            "protocol": PROTOCOL, "status": PENDING,
            "worker_assessment": None, "validation_profile": self.packet["validation_profile"],
            "configured_check_ids": [row["id"] for row in self.validation.configured_checks or []],
            "review_required": True, "primary_required": True})
        return self._complete_run(self.report(PENDING, ["Host checks passed; independent review pending"], None, []))


def verify_host_handoff(root, report, *, enabled=False):
    if enabled is not True or report.get("status") != PENDING:
        raise ValueError("New protocol not explicitly authorized or not pending review")
    root = Path(root).resolve()
    identity = report.get("identity", {})
    task = WORKER.require_identifier(identity.get("task_id"), "task_id")
    run = WORKER.require_identifier(identity.get("run_id"), "run_id")
    unit = WORKER.require_identifier(identity.get("unit_id"), "unit_id")
    archive = root / ".agent/tasks" / task / "runs" / run

    def read(name):
        return json.loads((archive / name).read_text(encoding="utf-8"))

    packet = WORKER.validate_packet(read("packet.json"))
    protocol = read("execution-protocol.json")
    if protocol.get("protocol") != PROTOCOL or protocol.get("worker_assessment") is not None:
        raise ValueError("Unknown protocol or fabricated assessment")
    if (packet["task_id"], packet["unit_id"], packet["run_id"]) != (task, unit, run):
        raise ValueError("Canonical identity mismatch")
    if any(read(name).get("status") != PENDING for name in ("handoff.json", "completed.json")):
        raise ValueError("Mixed new/legacy completion states")
    validation = read("validation.json")
    focused = validation.get("focused_tests", {})
    checks = validation.get("configured_checks") or []
    if validation.get("status") != "passed" or validation.get("contract_check") is not None:
        raise ValueError("Missing validation or synthesized confirmation")
    if validation.get("py_compile", {}).get("status") != "passed":
        raise ValueError("Syntax check missing or failed")
    if focused.get("status") != "passed" or focused.get("inputs_unchanged") is not True:
        raise ValueError("Focused tests failed or inputs changed")
    if not checks or sorted(row.get("id") for row in checks) != sorted(protocol.get("configured_check_ids", [])):
        raise ValueError("Configured check set changed")
    if any(row.get("status") != "passed" or row.get("exit_code") != 0 for row in checks):
        raise ValueError("Configured check failed")
    junit = focused.get("junit", {})
    if type(junit.get("executed")) is not int or junit["executed"] <= 0:
        raise ValueError("Zero or invalid executed test count")
    junit_path = root / junit["path"]
    if not junit_path.resolve().is_relative_to(archive.resolve()):
        raise ValueError("JUnit path outside canonical archive")
    tree = ET.parse(junit_path)
    cases = tree.findall(".//testcase")
    if not cases or any(tree.findall(".//" + tag) for tag in ("failure", "error")):
        raise ValueError("JUnit has no actual cases or failing cases")
    if all(case.find("skipped") is not None for case in cases):
        raise ValueError("All tests skipped")
    if sum(case.find("skipped") is None for case in cases) != junit["executed"]:
        raise ValueError("JUnit count differs from validation claim")
    changes = read("changes.json")
    if changes.get("unattributed_relevant_changes"):
        raise ValueError("Unattributed changes")
    paths = {row["path"] for row in changes.get("runtime_edits", [])}
    if not paths or not paths <= set(packet["scope"]["modify"]):
        raise ValueError("Changed paths exceed single-function scope")
    handoff = read("handoff.json")
    if {row["path"] for row in handoff.get("changed_files", [])} != paths:
        raise ValueError("Reported changed paths differ from actual runtime edits")
    expected = read("post-state.json").get("validation_inputs", {})
    if not expected or any(selector.split("::", 1)[0] not in expected for selector in packet["focused_tests"]):
        raise ValueError("Missing validation input facts")
    for relative, fact in expected.items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Validation path escapes root")
        if fact.get("exists") is False:
            if path.exists():
                raise ValueError("Previously absent validation input appeared")
        elif not path.is_file() or diagnostic.base.sha(path) != fact.get("sha256"):
            raise ValueError("Validation input hash changed")
    diff = (archive / "cumulative.diff").read_text(encoding="utf-8")
    if not diff.strip():
        raise ValueError("Actual diff missing")
    return {"task_id": task, "unit_id": unit, "run_id": run, "protocol": PROTOCOL}
