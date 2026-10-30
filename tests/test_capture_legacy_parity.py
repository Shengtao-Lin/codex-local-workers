"""Execute old frozen sources again offline; do not promote them to holdout."""

import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import capture_fixture_support as F
import reviewer_capture_entry as ENTRY
import reviewer_fixed_observations as OLD
import reviewer_observed_facts as REAL
from reviewer_capture_envelope import parse_command_capture

ROWS = json.loads(
    (
        F.KIT
        / "benchmarks/work/harness-convergence/r4-contract-first-20261017-1/registration.json"
    ).read_text(encoding="utf-8")
)["cells"]
PYTHON = "F:/ChatGPT/agent-evaluation-harness/.venv/Scripts/python.exe"


def expected_profile(row):
    manifest = {p: sha for p, sha in row["files"].items() if p.startswith("src/")}
    seal = json.loads(OLD.SEAL.read_text(encoding="utf-8"))
    entry = next(e for e in seal["entries"] if e["source_manifest"] == manifest)
    expected = copy.deepcopy(entry["observation"])
    if expected["profile_id"] == "collect-tools-json-observation-v1":
        real_seal = json.loads(REAL.SEAL.read_text(encoding="utf-8"))
        source = next(
            e for e in real_seal["sources"] if e["source_manifest"] == manifest
        )
        cases = json.loads(Path(source["request"]).read_text(encoding="utf-8"))["cases"]
        for example, case in zip(expected["examples"], cases, strict=True):
            example.pop("result_input")
            example["input"] = case
        expected.pop("shared_setup")
    return expected


@pytest.mark.parametrize("row", ROWS, ids=[r["id"] for r in ROWS])
def test_twenty_profiles_are_lossless(row, tmp_path):
    root = tmp_path / "copied"
    root.mkdir()
    manifest = {p: sha for p, sha in row["files"].items() if p.startswith("src/")}
    seal = json.loads(OLD.SEAL.read_text(encoding="utf-8"))
    entry = next(e for e in seal["entries"] if e["source_manifest"] == manifest)
    expected = copy.deepcopy(entry["observation"])
    target = expected["source"]["path"]
    if expected["profile_id"] == "collect-tools-json-observation-v1":
        real_seal = json.loads(REAL.SEAL.read_text(encoding="utf-8"))
        source = next(
            e for e in real_seal["sources"] if e["source_manifest"] == manifest
        )
        cases = json.loads(Path(source["request"]).read_text(encoding="utf-8"))["cases"]
        for example, case in zip(expected["examples"], cases, strict=True):
            example.pop("result_input")
            example["input"] = case
        expected.pop("shared_setup")
        module, symbol = "evaluation_harness.adapters.common", "collect_tools"
    else:
        cases = [e["input"] for e in expected["examples"]]
        module, symbol = (
            "_capture_pure_target",
            expected["profile_id"].removeprefix("fixed-pure-").removesuffix("-v1"),
        )
    for path, sha in manifest.items():
        source = Path(row["root"]) / path
        assert F.P.digest(source) == sha
        destination = root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    identity = {k: row["identity"][k] for k in ("task_id", "unit_id", "run_id")}
    policy, policy_sha = F.install_material(
        root,
        identity,
        source_paths=list(manifest),
        target={"path": target, "module": module, "symbol": symbol},
        family=expected["profile_id"],
        cases=cases,
        writable=[target],
        python=PYTHON,
    )
    argv = [PYTHON, "-B", str(root) + "/" + F.PRODUCER, "--policy", F.POLICY_PATH]
    process = subprocess.run(
        argv,
        cwd=root,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )
    assert process.returncode == 0, process.stderr
    assert not process.stderr
    current = F.P.manifest_for(root, F.POLICY_PATH, policy)
    profiles = parse_command_capture(
        [
            {
                "id": policy["check_id"],
                "status": "passed",
                "exit_code": 0,
                "argv": argv,
                "output": process.stdout,
                "output_truncated": False,
            }
        ],
        check_id=policy["check_id"],
        argv=argv,
        bindings={
            "task_id": identity["task_id"],
            "run_id": identity["run_id"],
            "producer_sha256": policy["producer_sha256"],
            "profile_sha256": policy_sha,
            "source_manifest_sha256": current["sha256"],
        },
    )
    assert json.dumps(profiles, sort_keys=True) == json.dumps(
        [expected], sort_keys=True
    )
    for path, sha in manifest.items():
        assert F.P.digest(root / path) == sha
        assert F.P.digest(Path(row["root"]) / path) == sha


@pytest.mark.parametrize("row", ROWS, ids=[r["id"] for r in ROWS])
def test_full_semantic_bundle_composition_parity(row):
    """Composition unit test with stubbed authenticated provider, not provenance proof.

    Real subprocess facts and authentic canonical entry are tested separately.
    This test must not mutate an old run to pretend it contains a new capture.
    """
    root = Path(row["root"])
    config = json.loads(
        (root / ".agent/experiment-config.json").read_text(encoding="utf-8")
    )
    original_module = F.load(
        root / ".local-agents/reviewer-runtime.py",
        "capture_parity_original_" + row["id"],
    )
    new_module = F.load(
        root / ".local-agents/reviewer-runtime.py", "capture_parity_new_" + row["id"]
    )
    original_class = ENTRY.SEMANTIC.install(original_module)
    new_class = ENTRY.install(new_module, "composition-stub-only", "0" * 64)
    old = original_class(
        root,
        {**row["identity"], "review_id": "offline-composition-old"},
        config,
        object(),
    )
    new = new_class(
        root,
        {**row["identity"], "review_id": "offline-composition-new"},
        config,
        object(),
    )
    expected = [expected_profile(row)]
    new._read_canonical_capture = lambda: (copy.deepcopy(expected), {"test_stub": True})
    new._capture_profiles = copy.deepcopy(expected)
    left, right = old.bundle(), new.bundle()
    assert json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True)
