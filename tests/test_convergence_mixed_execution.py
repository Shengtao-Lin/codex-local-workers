"""M1 authority controls: capabilities are not worker assertions or success labels."""

import copy
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))
spec = importlib.util.spec_from_file_location(
    "mixed_gate", ROOT / "benchmarks/convergence_mixed_execution.py"
)
trial = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trial)


def sample():
    plan = {
        "feature_id": "feature",
        "contracts": [{"id": "local"}, {"id": "classification"}],
        "units": [
            {
                "unit_id": "unit-1",
                "owner": "primary",
                "owned_contract_ids": ["classification"],
                "dependencies": [],
                "scope_authority": {"modify": ["src/classification.py"], "create": []},
            },
            {
                "unit_id": "unit-2",
                "owner": "local-coder",
                "owned_contract_ids": ["local"],
                "dependencies": ["unit-1"],
                "scope_authority": {"modify": ["src/local.py"], "create": []},
            },
        ],
    }
    catalog = {
        "classification": {
            "owner": "primary",
            "route": "primary_owned",
            "modify": ["src/classification.py"],
            "evidence": "C4 HOLD",
        },
        "local": {
            "owner": "local-coder",
            "route": "direct_local",
            "modify": ["src/local.py"],
            "evidence": "named accepted chain",
        },
    }
    return plan, catalog


def test_catalog_allows_exact_primary_and_local_owners():
    plan, catalog = sample()
    assert trial.route_plan(plan, catalog) == plan


@pytest.mark.parametrize(
    "mutation",
    ["owner", "scope", "create", "unqualified", "evidence", "unknown", "mixed-unit"],
)
def test_catalog_rejects_invalid_routes(mutation):
    plan, catalog = sample()
    if mutation == "owner":
        plan["units"][0]["owner"] = "local-coder"
    elif mutation == "scope":
        plan["units"][1]["scope_authority"]["modify"].append("src/classification.py")
    elif mutation == "create":
        plan["units"][1]["scope_authority"]["create"] = ["src/new.py"]
    elif mutation == "unqualified":
        catalog["local"]["route"] = "unqualified"
    elif mutation == "evidence":
        catalog["local"]["evidence"] = None
    elif mutation == "unknown":
        del catalog["local"]
    else:
        plan["units"][1]["owned_contract_ids"].append("classification")
    with pytest.raises(ValueError):
        trial.route_plan(plan, catalog)


@pytest.mark.parametrize("authorization", [False, None, 1, "true"])
def test_dispatch_requires_literal_authority(authorization):
    with pytest.raises(ValueError):
        trial.dispatch_guard(
            None, ROOT, {}, {}, {}, "unit-1", primary_authorized=authorization
        )


def test_primary_never_enters_worker(tmp_path):
    plan, catalog = sample()
    (tmp_path / ".agent").mkdir()
    (tmp_path / ".agent/brief.json").write_text(
        json.dumps({"capability_catalog": catalog})
    )
    with pytest.raises(ValueError, match="cannot enter"):
        trial.dispatch_guard(
            None, tmp_path, plan, {}, {}, "unit-1", primary_authorized=True
        )


@pytest.mark.parametrize("accepted", [set(), {"unit-1", "unit-2"}])
def test_missing_dependency_and_duplicate_blocked(tmp_path, monkeypatch, accepted):
    plan, catalog = sample()
    (tmp_path / ".agent").mkdir()
    (tmp_path / ".agent/brief.json").write_text(
        json.dumps({"capability_catalog": catalog})
    )
    monkeypatch.setattr(trial, "accepted_state", lambda *a: accepted)
    with pytest.raises(ValueError, match="dependency"):
        trial.dispatch_guard(
            None, tmp_path, plan, {}, {}, "unit-2", primary_authorized=True
        )


def test_accepted_primary_dependency_permits_local_step(tmp_path, monkeypatch):
    plan, catalog = sample()
    (tmp_path / ".agent").mkdir()
    (tmp_path / ".agent/brief.json").write_text(
        json.dumps({"capability_catalog": catalog})
    )
    monkeypatch.setattr(trial, "accepted_state", lambda *a: {"unit-1"})
    assert (
        trial.dispatch_guard(
            None, tmp_path, plan, {}, {}, "unit-2", primary_authorized=True
        )["owner"]
        == "local-coder"
    )


def primary_archive(tmp_path):
    plan, _ = sample()
    parent = tmp_path / ".agent/primary-reviews/feature"
    parent.mkdir(parents=True)
    prefix = ".agent/unit-1-primary"
    records = [prefix + "-" + s + ".json" for s in ("tests", "lint", "format")]
    for path in records:
        (tmp_path / path).write_text(json.dumps({"exit": 0}))
    (tmp_path / (prefix + ".xml")).write_text(
        '<testsuites><testsuite tests="1"><testcase name="real"/></testsuite></testsuites>'
    )
    record = {
        "primary_authorized": True,
        "post_source_hashes": {"src/classification.py": "new"},
        "changed_files": ["src/classification.py"],
        "check_records": records,
        "junit": prefix + ".xml",
        "evidence": [trial.ref(tmp_path, p) for p in [*records, prefix + ".xml"]],
    }
    path = parent / "unit-1.json"
    path.write_text(json.dumps(record))
    observations = []
    api = SimpleNamespace(
        CONTRACT=SimpleNamespace(accepted_units_from_archives=lambda *a: {"unit-1"}),
        assert_sources_current=lambda state, root: observations.append(state),
    )
    return plan, api, path, record, observations


def test_primary_current_hash_used_not_initial_hash(tmp_path):
    plan, api, _, _, observations = primary_archive(tmp_path)
    assert trial.accepted_state(
        api,
        tmp_path,
        plan,
        {"src/classification.py": "old", "src/local.py": "unchanged"},
        {"unit-1": {}},
    ) == {"unit-1"}
    assert observations == [
        {"source_hashes": {"src/classification.py": "new", "src/local.py": "unchanged"}}
    ]


@pytest.mark.parametrize(
    "mutation",
    [
        "scope",
        "authorization",
        "missing-check",
        "evidence-drift",
        "failing-tests",
        "skipped-tests",
        "empty-tests",
        "source-drift",
    ],
)
def test_primary_acceptance_cannot_mask_invalid_evidence(tmp_path, mutation):
    plan, api, path, record, _ = primary_archive(tmp_path)
    changed = copy.deepcopy(record)
    if mutation == "scope":
        changed["post_source_hashes"] = {"src/outside.py": "new"}
        changed["changed_files"] = ["src/outside.py"]
    elif mutation == "authorization":
        changed["primary_authorized"] = 1
    elif mutation == "missing-check":
        changed["check_records"] = []
    elif mutation == "evidence-drift":
        (tmp_path / changed["check_records"][1]).write_text('{"exit":1}')
    elif mutation == "source-drift":

        def drift(*args):
            raise ValueError("current source changed")

        api.assert_sources_current = drift
    else:
        inner = {
            "failing-tests": "<testcase><failure/></testcase>",
            "skipped-tests": "<testcase><skipped/></testcase>",
            "empty-tests": "",
        }[mutation]
        (tmp_path / changed["junit"]).write_text(
            "<testsuites><testsuite>" + inner + "</testsuite></testsuites>"
        )
        changed["evidence"] = [
            trial.ref(tmp_path, p)
            for p in [*changed["check_records"], changed["junit"]]
        ]
    path.write_text(json.dumps(changed))
    with pytest.raises(ValueError):
        trial.accepted_state(api, tmp_path, plan, {}, {"unit-1": {}})


def test_recovery_is_once_per_feature_before_dispatch(tmp_path, monkeypatch):
    monkeypatch.setattr(trial, "frozen", lambda: None)
    monkeypatch.setattr(
        trial.core, "entry", lambda identity: ({}, {"root": str(tmp_path)})
    )
    (tmp_path / ".agent").mkdir()
    (tmp_path / ".agent/external-rework-1.json").write_text("{}")
    with pytest.raises(FileExistsError, match="exhausted"):
        trial.rework_prepare("same", "unit-2", "not authorized to retry again")


def test_recovery_never_takes_over_primary_unit(tmp_path, monkeypatch):
    plan, catalog = sample()
    monkeypatch.setattr(trial, "frozen", lambda: None)
    monkeypatch.setattr(
        trial.core, "entry", lambda identity: ({}, {"root": str(tmp_path)})
    )
    (tmp_path / ".agent").mkdir()
    for path, value in {
        "brief.json": {"capability_catalog": catalog},
        "approval.json": {"approved_plan": plan},
        "unit-1-packet.json": {},
        "unit-1-coder.json": {"status": "failed"},
    }.items():
        (tmp_path / ".agent" / path).write_text(json.dumps(value))
    with pytest.raises(ValueError, match="failed local"):
        trial.rework_prepare("same", "unit-1", "do not delegate classification")
    assert not (tmp_path / ".agent/external-rework-1.json").exists()
