"""Brief/proposal/approval safety, independent of the selected local model."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

SPEC = importlib.util.spec_from_file_location(
    "coordinator_brief_tests", Path(__file__).resolve().parents[1] / "coordinator-brief.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def example():
    scope = {
        "read_roots": ["src", "tests"],
        "modify": ["src/a.py", "src/b.py"],
        "create": [],
        "readonly": ["tests/test_a.py"],
        "forbidden": [".agent", "AGENTS.md"],
    }
    brief = {
        "schema_version": 1,
        "revision": 1,
        "feature_id": "example",
        "task_id": "example",
        "goal": "Add two separate local transformations",
        "risk_rationale": "Protected compatibility boundary",
        "feature_risk": "medium",
        "integration_risk": "medium",
        "authority": scope,
        "max_units": 3,
        "contracts": [
            {"id": c, "text": c + " unchanged semantics", "risk_floor": "medium"}
            for c in ("producer", "consumer")
        ],
        "contract_edges": [],
        "atomic_contract_groups": [],
        "source_hashes": {},
        "integration_tests": ["tests/test_a.py"],
    }
    units = []
    for ident, path in (("producer", "src/a.py"), ("consumer", "src/b.py")):
        authority = copy.deepcopy(scope)
        authority["modify"] = [path]
        units.append(
            {
                "unit_id": ident,
                "owner": "local-coder",
                "risk": "medium",
                "dependencies": [],
                "owned_contract_ids": [ident],
                "scope_authority": authority,
                "status": "planned",
                "packet_contract": {
                    "acceptance_criteria": [{"id": "expected", "text": ident}],
                    "acceptance_scenarios": [
                        {
                            "id": "normal",
                            "text": "normal input",
                            "observables": {"result": "expected"},
                        }
                    ],
                    "required_order": [],
                    "forbidden_orderings": [],
                    "validation_profile": "python-focused",
                    "required_focused_tests": ["tests/test_a.py"],
                },
            }
        )
    proposal = {
        "status": "proposed",
        "units": units,
        "questions": [],
        "integration_tests": ["tests/test_a.py"],
        "rationale": "Independent behavior can be separated, model execution remains serial",
    }
    brief["validation_profile"] = "python-focused"
    brief["acceptance_catalog"] = {
        unit["owned_contract_ids"][0]: copy.deepcopy(unit["packet_contract"]) for unit in units
    }
    proposal.pop("integration_tests")
    proposal["units"] = [
        {
            "id": unit["unit_id"],
            "goal": unit["unit_id"],
            "owner": unit["owner"],
            "risk": unit["risk"],
            "contracts": unit["owned_contract_ids"],
            "dependencies": unit["dependencies"],
            "modify": unit["scope_authority"]["modify"],
            "create": [],
        }
        for unit in units
    ]
    return brief, proposal


class BriefTests(unittest.TestCase):
    def bind_inputs(self, root, brief):
        for relative in brief["authority"]["modify"] + brief["authority"]["readonly"]:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_text("value=1\n", encoding="utf-8")
            brief["source_hashes"][relative] = hashlib.sha256(path.read_bytes()).hexdigest()

    def test_legacy_complete_plan_still_uses_original_validator(self):
        brief, proposal = example()
        plan = MODULE.proposal_plan(brief, proposal)
        self.assertEqual(MODULE.CONTRACT.validate_feature_plan(plan)["feature_id"], "example")

    def test_brief_rejects_predecomposition(self):
        brief, _ = example()
        for key in ("units", "dependencies", "edit_targets", "owned_contract_ids"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                MODULE.validate_brief({**brief, key: []})

    def test_scope_expansion_and_protected_writes_rejected(self):
        brief, original = example()
        for path in ("src/outside.py", "tests/test_a.py"):
            proposal = copy.deepcopy(original)
            proposal["units"][0]["modify"] = [path]
            with self.subTest(path=path), self.assertRaises(ValueError):
                MODULE.proposal_plan(brief, proposal)

    def test_risk_floor_cannot_be_silently_upgraded_from_invalid_proposal(self):
        brief, proposal = example()
        proposal["units"][0]["risk"] = "small"
        with self.assertRaisesRegex(ValueError, "risk below"):
            MODULE.proposal_plan(brief, proposal)

    def test_missing_duplicate_and_unknown_contracts_rejected(self):
        brief, original = example()
        for contract in ("producer", "missing"):
            proposal = copy.deepcopy(original)
            proposal["units"][1]["contracts"] = [contract]
            with self.subTest(contract=contract), self.assertRaises(ValueError):
                MODULE.proposal_plan(brief, proposal)

    def test_cycles_rejected(self):
        brief, proposal = example()
        proposal["units"][0]["dependencies"] = ["consumer"]
        proposal["units"][1]["dependencies"] = ["producer"]
        with self.assertRaisesRegex(ValueError, "cycle"):
            MODULE.proposal_plan(brief, proposal)

    def test_atomic_group_cannot_be_split(self):
        brief, proposal = example()
        brief["atomic_contract_groups"] = [["producer", "consumer"]]
        with self.assertRaisesRegex(ValueError, "atomic"):
            MODULE.proposal_plan(brief, proposal)

    def test_consumer_dependency_must_follow_contract_edge(self):
        brief, proposal = example()
        brief["contract_edges"] = [["producer", "consumer"]]
        with self.assertRaisesRegex(ValueError, "consumer lacks"):
            MODULE.proposal_plan(brief, proposal)
        proposal["units"][1]["dependencies"] = ["producer"]
        self.assertIsNotNone(MODULE.proposal_plan(brief, proposal))

    def test_integration_test_cannot_be_dropped(self):
        brief, proposal = example()
        proposal["integration_tests"] = []
        with self.assertRaisesRegex(ValueError, "proposal fields"):
            MODULE.proposal_plan(brief, proposal)

    def test_model_cannot_author_packet_assertions_or_confirmations(self):
        brief, original = example()
        for field in ("packet_contract", "required_order_confirmed", "scope_authority", "status"):
            proposal = copy.deepcopy(original)
            proposal["units"][0][field] = True
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "unit fields"):
                MODULE.proposal_plan(brief, proposal)

    def test_primary_catalog_is_required_and_copied_without_reinterpretation(self):
        brief, proposal = example()
        plan = MODULE.proposal_plan(brief, proposal)
        self.assertEqual(
            plan["units"][0]["packet_contract"], brief["acceptance_catalog"]["producer"]
        )
        self.assertEqual(plan["units"][0]["unit_id"], "unit-1")
        self.assertEqual(
            plan["units"][0]["scope_authority"]["readonly"], brief["authority"]["readonly"]
        )
        del brief["acceptance_catalog"]
        with self.assertRaisesRegex(ValueError, "acceptance_catalog"):
            MODULE.proposal_plan(brief, proposal)

    def test_unresolved_proposal_cannot_be_approved(self):
        brief, proposal = example()
        proposal.update(
            status="unresolved", units=[], questions=["Where is the missing producer contract?"]
        )
        self.assertIsNone(MODULE.proposal_plan(brief, proposal))
        with TemporaryDirectory() as directory, self.assertRaisesRegex(ValueError, "unresolved"):
            root = Path(directory)
            MODULE.approve(
                brief, proposal, root, root / ".agent/approval.json", primary_review_note="checked"
            )

    def test_model_cannot_add_primary_approval_field(self):
        brief, proposal = example()
        proposal["primary_approved"] = True
        with self.assertRaisesRegex(ValueError, "proposal fields"):
            MODULE.proposal_plan(brief, proposal)

    def test_no_approval_missing_record_fails_closed(self):
        brief, proposal = example()
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(FileNotFoundError):
                MODULE.approved_plan(brief, proposal, root, root / ".agent/missing.json")

    def test_approval_binds_all_inputs_and_is_create_only(self):
        brief, proposal = example()
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.bind_inputs(root, brief)
            path = root / ".agent/approval.json"
            record = MODULE.approve(
                brief,
                proposal,
                root,
                path,
                primary_review_note="Reviewed all contracts and source; independent tests protected",
            )
            self.assertFalse(record["proposal_dispatch_allowed"])
            self.assertEqual(
                MODULE.approved_plan(brief, proposal, root, path), record["approved_plan"]
            )
            with self.assertRaises(ValueError):
                MODULE.approve(brief, proposal, root, path, primary_review_note="again")
            for changed in ("goal", "contract"):
                revised = copy.deepcopy(brief)
                if changed == "goal":
                    revised["goal"] += " changed"
                else:
                    revised["contracts"][0]["text"] += " changed"
                with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, "stale"):
                    MODULE.approved_plan(revised, proposal, root, path)

    def test_current_source_required_after_approval(self):
        brief, proposal = example()
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "src/a.py"
            source.parent.mkdir()
            source.write_text("value=1\n", encoding="utf-8")
            brief["source_hashes"] = {"src/a.py": hashlib.sha256(source.read_bytes()).hexdigest()}
            self.bind_inputs(root, brief)
            path = root / ".agent/approval.json"
            MODULE.approve(brief, proposal, root, path, primary_review_note="checked")
            source.write_text("value=2\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "stale"):
                MODULE.approved_plan(brief, proposal, root, path)

    def test_primary_note_without_input_hashes_cannot_approve(self):
        brief, proposal = example()
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "input hashes"):
                MODULE.approve(
                    brief, proposal, root, root / ".agent/a.json", primary_review_note="checked"
                )

    def test_probe_is_bounded_readonly_and_never_approves(self):
        brief, proposal = example()

        class Client:
            def __init__(self):
                self.calls = 0

            def complete(self, messages):
                self.calls += 1
                return "bad-json" if self.calls == 1 else json.dumps(proposal)

        client = Client()
        result = MODULE.probe(brief, {}, client)
        self.assertEqual(client.calls, 2)
        self.assertFalse(result["dispatch_allowed"])
        self.assertTrue(result["semantic_primary_review_required"])
        self.assertEqual(len(result["attempts"]), 2)
