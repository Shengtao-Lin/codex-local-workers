"""Installed limited-entry controls, with no benchmark or model dependency."""

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


ROOT = Path(__file__).resolve().parents[1]
ENTRY = module("limited_entry_test", ROOT / "coordinator-limited.py")
FIXTURE = module("limited_brief_fixture", ROOT / "tests/test_coordinator_brief.py")


class LimitedEntryTests(unittest.TestCase):
    def fixture(self, root):
        brief, proposal = FIXTURE.example()
        brief["contract_edges"] = [["producer", "consumer"]]
        proposal["units"][1]["dependencies"] = ["producer"]
        FIXTURE.BriefTests().bind_inputs(root, brief)
        brief["capability_catalog"] = {
            c: {
                "owner": "local-coder",
                "route": "direct_local",
                "modify": [p],
                "evidence": "Primary-reviewed fixed qualification",
            }
            for c, p in (("producer", "src/a.py"), ("consumer", "src/b.py"))
        }
        config = root / ".agent/config.json"
        config.parent.mkdir(exist_ok=True)
        config.write_text(json.dumps({"python": sys.executable, "single_model_residency": True}))
        approval = root / ".agent/approval.json"
        return brief, proposal, config, approval

    def packet(self, plan, unit_id="unit-1"):
        unit = next(u for u in plan["units"] if u["unit_id"] == unit_id)
        return ENTRY.CONTRACT.materialize_bounded_packet(
            plan,
            {
                "unit_id": unit_id,
                "run_id": "bounded-a1",
                "attempt": 1,
                "packet_revision": 1,
                "goal": "Implement the approved observable behavior",
                "scope": {
                    "read": unit["scope_authority"]["read_roots"],
                    "modify": unit["scope_authority"]["modify"],
                    "create": [],
                },
                "edit_targets": [{"path": unit["scope_authority"]["modify"][0], "anchor": "value"}],
                "focused_tests": unit["packet_contract"]["required_focused_tests"],
                "supplemental_tests": [],
                "implementation_guidance": [],
            },
        )

    def test_explicit_step_rejects_truthy_non_booleans(self):
        for value in (False, None, 1, "true"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ENTRY.require_authority(value)

    def test_capability_catalog_fails_closed(self):
        with TemporaryDirectory() as tmp:
            brief, proposal, _, _ = self.fixture(Path(tmp))
            plan = ENTRY.BRIEF.proposal_plan(brief, proposal)
            self.assertEqual(ENTRY.route_plan(plan, brief["capability_catalog"]), plan)
            for defect in ("unknown", "owner", "route", "scope", "evidence", "mixed", "create"):
                p, catalog = copy.deepcopy(plan), copy.deepcopy(brief["capability_catalog"])
                if defect == "unknown":
                    del catalog["producer"]
                elif defect in {"owner", "route", "evidence"}:
                    catalog["producer"][defect] = None
                elif defect == "scope":
                    p["units"][0]["scope_authority"]["modify"].append("src/b.py")
                elif defect == "mixed":
                    catalog["consumer"]["owner"] = "primary"
                    p["units"][0]["owned_contract_ids"].append("consumer")
                else:
                    p["units"][0]["scope_authority"]["create"] = ["src/new.py"]
                with self.subTest(defect=defect), self.assertRaises(ValueError):
                    ENTRY.route_plan(p, catalog)

    def test_missing_approval_does_not_invoke_a_worker(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            brief, proposal, config, approval = self.fixture(root)
            plan = ENTRY.BRIEF.proposal_plan(brief, proposal)
            with self.assertRaises(OSError):
                ENTRY.dispatch(
                    root,
                    brief,
                    proposal,
                    approval,
                    config,
                    {},
                    self.packet(plan),
                    authorized=True,
                    runner=lambda *a, **k: self.fail("dispatched"),
                )
            self.assertFalse((root / ".agent/limited").exists())

    def test_approval_is_immutable_and_preserves_legacy_full_plan(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            brief, proposal, config, approval = self.fixture(root)
            result = ENTRY.approve(
                root,
                brief,
                proposal,
                approval,
                config,
                authorized=True,
                note="Primary reviewed contract ownership and dependencies",
            )
            self.assertFalse(result["dispatch_allowed"])
            ENTRY.CONTRACT.validate_feature_plan(result["plan"])
            self.assertEqual(ENTRY.approved(root, brief, proposal, approval, config, {})[1], set())
            with self.assertRaises(ValueError):
                ENTRY.approve(
                    root, brief, proposal, approval, config, authorized=True, note="repeat"
                )

    def test_drift_rejected_before_invocation(self):
        for defect in ("brief", "proposal", "approval", "source", "test", "config", "runtime"):
            with self.subTest(defect=defect), TemporaryDirectory() as tmp:
                root = Path(tmp)
                brief, proposal, config, approval = self.fixture(root)
                plan = ENTRY.approve(
                    root,
                    brief,
                    proposal,
                    approval,
                    config,
                    authorized=True,
                    note="Independent Primary semantic review",
                )["plan"]
                if defect in {"brief", "proposal"}:
                    (brief if defect == "brief" else proposal)[
                        "goal" if defect == "brief" else "rationale"
                    ] += " drift"
                elif defect in {"source", "test"}:
                    (root / ("src/a.py" if defect == "source" else "tests/test_a.py")).write_text(
                        "changed"
                    )
                elif defect == "config":
                    config.write_text("{}")
                else:
                    path = (
                        approval if defect == "approval" else approval.with_suffix(".binding.json")
                    )
                    obj = ENTRY.read(path)
                    obj["source_hashes" if defect == "approval" else "runtime_hashes"] = {}
                    path.write_text(json.dumps(obj))
                with self.assertRaises(ValueError):
                    ENTRY.dispatch(
                        root,
                        brief,
                        proposal,
                        approval,
                        config,
                        {},
                        self.packet(plan),
                        authorized=True,
                        runner=lambda *a, **k: self.fail("dispatched"),
                    )
                self.assertFalse((root / ".agent/limited").exists())

    def test_unaccepted_dependency_and_primary_owner_never_dispatch(self):
        for primary in (False, True):
            with self.subTest(primary=primary), TemporaryDirectory() as tmp:
                root = Path(tmp)
                brief, proposal, config, approval = self.fixture(root)
                if primary:
                    proposal["units"][1]["owner"] = "primary"
                    brief["capability_catalog"]["consumer"].update(
                        owner="primary", route="primary_owned"
                    )
                plan = ENTRY.approve(
                    root,
                    brief,
                    proposal,
                    approval,
                    config,
                    authorized=True,
                    note="Primary-owned classification must not enter Coder",
                )["plan"]
                with self.assertRaises(ValueError):
                    ENTRY.dispatch(
                        root,
                        brief,
                        proposal,
                        approval,
                        config,
                        {},
                        self.packet(plan, "unit-2"),
                        authorized=True,
                        runner=lambda *a, **k: self.fail("dispatched"),
                    )
                self.assertFalse((root / ".agent/limited").exists())

    def test_dispatch_once_runs_installed_local_unit_without_acceptance(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            brief, proposal, config, approval = self.fixture(root)
            plan = ENTRY.approve(
                root,
                brief,
                proposal,
                approval,
                config,
                authorized=True,
                note="Primary independently approves bounded qualification",
            )["plan"]
            observed = []

            def runner(argv, **kwargs):
                observed.append((argv, kwargs))
                return SimpleNamespace(returncode=0, stdout="worker facts", stderr="")

            packet = self.packet(plan)
            result = ENTRY.dispatch(
                root, brief, proposal, approval, config, {}, packet, authorized=True, runner=runner
            )
            self.assertFalse(result["feature_accepted"])
            self.assertEqual(Path(observed[0][0][2]), ROOT / "local-unit.py")
            self.assertEqual(observed[0][1]["cwd"], root)
            with self.assertRaises(FileExistsError):
                ENTRY.dispatch(
                    root,
                    brief,
                    proposal,
                    approval,
                    config,
                    {},
                    packet,
                    authorized=True,
                    runner=runner,
                )
            self.assertEqual(len(observed), 1)

    def test_source_and_read_scope_cannot_expand(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            brief, proposal, config, approval = self.fixture(root)
            plan = ENTRY.approve(
                root,
                brief,
                proposal,
                approval,
                config,
                authorized=True,
                note="Scope and tests independently reviewed",
            )["plan"]
            packet = self.packet(plan)
            packet["scope"]["read"].append("private")
            with self.assertRaises(ValueError):
                ENTRY.dispatch(
                    root,
                    brief,
                    proposal,
                    approval,
                    config,
                    {},
                    packet,
                    authorized=True,
                    runner=lambda *a, **k: self.fail("dispatched"),
                )

    def accepted_local_fixture(self, root, brief, plan):
        packet = self.packet(plan)
        task_id, run_id = packet["task_id"], packet["run_id"]
        archive = root / ".agent/tasks" / task_id / "runs" / run_id
        reviewer = root / ".agent/tasks" / task_id / "reviews/independent"
        archive.mkdir(parents=True)
        reviewer.mkdir(parents=True)
        identity = {
            k: packet[k] for k in ("task_id", "run_id", "unit_id", "feature_id", "plan_revision")
        }
        source = root / "src/a.py"
        source.write_text("value=2\n")
        validation = {
            "status": "passed",
            "configured_checks": [],
            "focused_tests": {
                "status": "passed",
                "inputs_unchanged": True,
                "junit": {"path": (archive / "junit.xml").relative_to(root).as_posix()},
            },
        }
        records = {
            archive / "packet.json": packet,
            archive / "review.json": {
                **identity,
                "decision": "accept",
                "worker_status": "ready_for_review",
                "local_review_id": "independent",
            },
            archive / "handoff.json": {
                "identity": identity,
                "status": "ready_for_review",
                "changed_files": [{"path": "src/a.py", "final_sha256": ENTRY.sha(source)}],
            },
            archive / "completed.json": {"status": "ready_for_review"},
            archive / "validation.json": validation,
            reviewer / "handoff.json": {
                "identity": {**identity, "review_id": "independent"},
                "decision": "pass_to_primary",
            },
            reviewer / "completed.json": {"decision": "pass_to_primary"},
        }
        for path, value in records.items():
            path.write_text(json.dumps(value))
        (archive / "junit.xml").write_text(
            '<testsuites><testsuite><testcase name="actual"/></testsuite></testsuites>'
        )
        refs = {"unit-1": {"task_id": task_id, "run_id": run_id}}
        return archive, reviewer, refs

    def test_dependency_acceptance_uses_current_hashes_and_actual_reviewer(self):
        for defect in (
            None,
            "reviewer-rework",
            "no-primary",
            "stale-plan",
            "zero-tests",
            "failed-validation",
            "post-edit",
            "protected-edit",
            "omitted-dependency",
        ):
            with self.subTest(defect=defect), TemporaryDirectory() as tmp:
                root = Path(tmp)
                brief, proposal, config, approval = self.fixture(root)
                plan = ENTRY.approve(
                    root, brief, proposal, approval, config, authorized=True, note="Reviewed"
                )["plan"]
                archive, reviewer, refs = self.accepted_local_fixture(root, brief, plan)
                if defect == "reviewer-rework":
                    (reviewer / "completed.json").write_text('{"decision":"rework"}')
                elif defect == "no-primary":
                    (archive / "review.json").write_text("{}")
                elif defect == "stale-plan":
                    value = ENTRY.read(archive / "packet.json")
                    value["primary_plan_sha256"] = "0" * 64
                    (archive / "packet.json").write_text(json.dumps(value))
                elif defect == "zero-tests":
                    (archive / "junit.xml").write_text("<testsuites/>")
                elif defect == "failed-validation":
                    (archive / "validation.json").write_text('{"status":"failed"}')
                elif defect in {"post-edit", "protected-edit"}:
                    (
                        root / ("src/a.py" if defect == "post-edit" else "tests/test_a.py")
                    ).write_text("drift")
                elif defect == "omitted-dependency":
                    refs["unit-2"] = refs.pop("unit-1")
                if defect is None:
                    self.assertEqual(
                        ENTRY.approved(root, brief, proposal, approval, config, refs)[1], {"unit-1"}
                    )
                else:
                    with self.assertRaises((ValueError, KeyError)):
                        ENTRY.approved(root, brief, proposal, approval, config, refs)

    def test_primary_receipt_requires_current_validation_and_junit(self):
        for defect in (
            None,
            "missing-check",
            "evidence-drift",
            "empty-tests",
            "skip",
            "non-boolean-authority",
        ):
            with self.subTest(defect=defect), TemporaryDirectory() as tmp:
                root = Path(tmp)
                brief, proposal, config, approval = self.fixture(root)
                proposal["units"][0]["owner"] = "primary"
                brief["capability_catalog"]["producer"].update(
                    owner="primary", route="primary_owned"
                )
                plan = ENTRY.approve(
                    root, brief, proposal, approval, config, authorized=True, note="Reviewed"
                )["plan"]
                prefix = ".agent/unit-1-primary"
                checks = [prefix + "-" + s + ".json" for s in ("tests", "lint", "format")]
                for p in checks:
                    (root / p).write_text('{"exit":0}')
                junit = prefix + ".xml"
                (root / junit).write_text('<testsuites><testcase name="actual"/></testsuites>')
                record = {
                    "schema_version": 1,
                    "feature_id": plan["feature_id"],
                    "unit_id": "unit-1",
                    "plan_revision": plan["plan_revision"],
                    "primary_plan_sha256": ENTRY.CONTRACT.authority_fingerprint(plan),
                    "decision": "accept",
                    "primary_authorized": True,
                    "changed_files": [],
                    "post_source_hashes": {},
                    "check_records": checks,
                    "junit": junit,
                }
                if defect == "missing-check":
                    record["check_records"] = []
                elif defect in {"skip", "empty-tests"}:
                    (root / junit).write_text(
                        "<testsuites/>"
                        if defect == "empty-tests"
                        else "<testsuites><testcase><skipped/></testcase></testsuites>"
                    )
                elif defect == "non-boolean-authority":
                    record["primary_authorized"] = 1
                record["evidence"] = [
                    {"path": p, "sha256": ENTRY.sha(root / p)} for p in [*checks, junit]
                ]
                path = root / ".agent/primary-reviews" / plan["feature_id"] / "unit-1.json"
                path.parent.mkdir(parents=True)
                path.write_text(json.dumps(record))
                if defect == "evidence-drift":
                    (root / checks[1]).write_text('{"exit":1}')
                if defect is None:
                    self.assertEqual(
                        ENTRY.approved(root, brief, proposal, approval, config, {"unit-1": {}})[1],
                        {"unit-1"},
                    )
                else:
                    with self.assertRaises(ValueError):
                        ENTRY.approved(root, brief, proposal, approval, config, {"unit-1": {}})


if __name__ == "__main__":
    unittest.main()
