"""Fail-closed controls for the optional source/pytest evidence profile."""

import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bounded import generic_evidence as G


@pytest.fixture
def prepared(tmp_path):
    for name, content in {
        "src/change.py": "def change(x):\n    return x\n",
        "tests/test_change.py": "def test_change():\n    assert True\n",
        "python.exe": "stand-in executable identity, never executed",
    }.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    runtime = SimpleNamespace(
        repo_root=tmp_path,
        config={"experimental_strata_subagent": True},
        packet={
            "task_id": "t",
            "unit_id": "u",
            "run_id": "r",
            "scope": {"modify": ["src/change.py"], "create": []},
        },
        single_function={"path": "src/change.py", "symbol": "change"},
        observed_hashes={},
    )
    runtime.python_path = lambda: tmp_path / "python.exe"
    runtime.validation_profile = lambda: {
        "commands": [{"id": name} for name in sorted(G.CHECK_IDS)]
    }
    allowed = {"src/change.py", "tests/test_change.py", G.POLICY_PATH}

    def allowed_read(name):
        if name not in allowed:
            raise ValueError("not approved")
        return name, tmp_path / name

    runtime._assert_read_allowed = allowed_read

    def read_file(args):
        name, path = allowed_read(args["path"])
        runtime.observed_hashes[name] = G.digest(path)

    runtime.read_file = read_file
    policy = G.build_policy(
        runtime,
        {**runtime.single_function, "module": "change"},
        {p: G.digest(tmp_path / p) for p in sorted(allowed - {G.POLICY_PATH})},
    )

    def save(value):
        path = tmp_path / G.POLICY_PATH
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
        runtime.config[G.CONFIG_SHA] = G.digest(path)

    save(policy)
    return runtime, policy, save


def test_default_is_unchanged_and_unknown_never_falls_back():
    assert G.selected({}) is False
    assert G.selected({"bounded_evidence_profile": G.PROFILE}) is True
    with pytest.raises(ValueError, match="Unknown"):
        G.selected({"bounded_evidence_profile": "typo"})


def test_real_source_binding_and_no_validation_credit(prepared):
    runtime, policy, _ = prepared
    assert G.bind_before_coder(runtime) == policy
    assert set(runtime.observed_hashes) == {*policy["source_paths"], G.POLICY_PATH}
    assert G.preflight_material(runtime)["validation_credit"] is False
    assert G.preflight_material(runtime)["typed_observations"] == "NOT_REQUESTED_BY_PROFILE"


def test_writable_edit_allowed_but_old_start_not_reusable(prepared):
    runtime, _, _ = prepared
    (runtime.repo_root / "src/change.py").write_text("def change(x):\n    return x + 1\n")
    G.policy_for(runtime)
    with pytest.raises(ValueError, match="Initial source"):
        G.policy_for(runtime, initial=True)


def test_protected_drift_rejected(prepared):
    runtime, _, _ = prepared
    (runtime.repo_root / "tests/test_change.py").write_text("# changed")
    with pytest.raises(ValueError, match="Protected"):
        G.policy_for(runtime)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda p: p.update(identity={"task_id": "wrong"}),
        lambda p: p.update(target=[]),
        lambda p: p.update(source_paths="src/change.py"),
        lambda p: p.update(source_paths=["tests/test_change.py"]),
        lambda p: p.update(source_paths=["../escape.py", "src/change.py"]),
        lambda p: p.update(initial_hashes={}),
        lambda p: p.update(readonly_hashes=[]),
        lambda p: p.update(readonly_hashes={"tests/test_change.py": "not-a-sha"}),
        lambda p: p.update(python={"path": "different", "sha256": "0" * 64}),
        lambda p: p.update(extra="unknown field"),
    ],
)
def test_invalid_trusted_policy_rejected(prepared, mutation):
    runtime, policy, save = prepared
    changed = copy.deepcopy(policy)
    mutation(changed)
    save(changed)
    with pytest.raises(ValueError):
        G.policy_for(runtime)


def test_policy_tampering_rejected_before_use(prepared):
    runtime, _, _ = prepared
    (runtime.repo_root / G.POLICY_PATH).write_text("{}")
    with pytest.raises(ValueError, match="differs"):
        G.policy_for(runtime)


def test_missing_static_check_rejected(prepared):
    runtime, _, _ = prepared
    runtime.validation_profile = lambda: {"commands": [{"id": "ruff-check"}]}
    with pytest.raises(ValueError, match="static-check"):
        G.policy_for(runtime)


def test_build_needs_explicit_subagent_and_target(prepared):
    runtime, policy, _ = prepared
    with pytest.raises(ValueError, match="implementation target"):
        G.build_policy(runtime, policy["target"], {})
    runtime.config["experimental_strata_subagent"] = False
    with pytest.raises(ValueError, match="explicit"):
        G.build_policy(runtime, policy["target"], policy["initial_hashes"])
