"""Small fixture adapter for the installed preparation entry; reuse checks and runner."""

import shutil
import tempfile
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import limited_family_trial as L
import prepared_slice_trial as P
from test_installable_bounded import INSTALL

TARGET = "src/product/code.py"


def format_project(root):
    for args in (("check", "--select", "I", "--fix"), ("format",)):
        result = T.run([S.PYTHON, "-B", "-m", "ruff", *args, "src", "tests"], root)
        if result["exit_code"]:
            raise ValueError(result)


def template(batch, topic, spec):
    root = batch / "templates" / topic
    T.write(root / TARGET, spec["header"] + "\n\n" + spec["start"])
    T.write(root / "src/product/__init__.py", "")
    T.write(root / "tests/test_contract.py", spec["public"])
    for name, source in spec.get("files", {}).items():
        T.write(root / name, source)
    shutil.copyfile(P.SEED / "pyproject.toml", root / "pyproject.toml")
    private = batch / "private" / topic / "test_independent.py"
    T.write(private, spec["private"])
    reference = batch / "reference-checks" / topic
    shutil.copytree(root, reference, ignore=shutil.ignore_patterns("code.py"))
    T.write(reference / TARGET, spec["header"] + "\n\n" + spec["reference"])
    format_project(root)
    format_project(reference)
    observed = {
        "baseline": L.checks(root, private),
        "reference": L.checks(reference, private),
    }
    S.save(batch / "task-controls" / f"{topic}.json", observed)
    assert any(c["exit_code"] != 0 for c in observed["baseline"])
    assert all(c["exit_code"] == 0 for c in observed["reference"]), observed
    return root, private, reference


def cell(batch, label, topic, spec, material, plan_path, *, runtime_override=None):
    template_root, private, reference = material
    root = batch / "cells" / label / "isolated"
    with tempfile.TemporaryDirectory(prefix="prepared-matrix-install-") as directory:
        stage = Path(directory)
        INSTALL.install(S.KIT, stage, apply=True)
        shutil.copytree(stage, root)
    for name in ("src", "tests"):
        shutil.copytree(
            template_root / name,
            root / name,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
    shutil.copyfile(template_root / "pyproject.toml", root / "pyproject.toml")
    if runtime_override:
        for relative, origin in runtime_override.items():
            shutil.copyfile(origin, root / relative)
    packet = S.read(P.SEED / ".agent/packet.json")
    identity = {
        key: batch.name + "-" + label for key in ("task_id", "unit_id", "run_id")
    }
    packet.update(
        identity,
        feature_id="bounded-" + topic,
        goal=spec["contract"],
        primary_plan_sha256=S.sha(plan_path),
    )
    packet["risk"]["reasons"] = [spec["risk_rationale"]]
    packet["owned_contract_ids"] = [topic]
    packet["required_behavior"] = [
        {
            "id": topic,
            "text": spec["contract"],
            "risk_floor": "high",
            "implementation_ref": {"path": TARGET, "symbol": spec["symbol"]},
        }
    ]
    packet["acceptance_criteria"] = [
        {
            "id": topic,
            "text": "Complete specified behavior, preserved input/compatibility and all strict checks",
        }
    ]
    packet["acceptance_scenarios"] = spec["scenarios"]
    packet["edit_targets"] = [{"path": TARGET, "anchor": "def " + spec["symbol"] + "("}]
    source_paths = [
        TARGET,
        "src/product/__init__.py",
        "tests/test_contract.py",
        "pyproject.toml",
        *spec.get("files", {}),
    ]
    packet["scope"]["readonly"] += list(spec.get("files", {}))
    config = S.read(P.SEED / ".agent/config.json")
    config["coder_single_function"] = {
        "path": TARGET,
        "symbol": spec["symbol"],
        "dependencies": spec["header"] + spec.get("dependency_context", ""),
    }
    capture = {
        "schema_version": 1,
        "target": {"path": TARGET, "module": "product.code", "symbol": spec["symbol"]},
        "source_paths": source_paths,
        "family": "json-call-model-dump-v1",
        "cases": spec["cases"],
    }
    for name, value in (
        ("packet", packet),
        ("config", config),
        ("capture-spec", capture),
    ):
        S.save(root / f".agent/{name}.json", value)
    argv = [
        S.PYTHON,
        "-B",
        root / ".local-agents/local-bounded-prepare.py",
        "--packet",
        ".agent/packet.json",
        "--config",
        ".agent/config.json",
        "--capture-spec",
        ".agent/capture-spec.json",
        "--apply",
    ]
    prepared = T.run(argv, root)
    S.save(batch / "preparation" / f"{label}.json", prepared)
    assert prepared["exit_code"] == 0, prepared
    preflight = P.command(root, mode="preflight")
    preflight[preflight.index("--report") + 1] = str(root / ".agent/preflight.json")
    result = T.run(preflight, root)
    S.save(batch / "preflight" / f"{label}.json", result)
    assert result["exit_code"] == 0, result
    proof = batch / "replay" / label / "isolated"
    shutil.copytree(root, proof)
    replay = proof.parent / "reference.json"
    S.save(
        replay,
        [
            {
                "kind": "replacement",
                "content": T.extract(reference / TARGET, spec["symbol"]),
            }
        ],
    )
    result = T.run(P.command(proof, replay=replay), proof, timeout=180)
    S.save(proof.parent / "process.json", result)
    assert result["exit_code"] == 0, result
    return {
        "root": str(root),
        "identity": identity,
        "topic": topic,
        "target": TARGET,
        "private_tests": str(private),
        "start_sha256": S.sha(root / TARGET),
        "files": {
            p.relative_to(root).as_posix(): S.sha(p)
            for p in root.rglob("*")
            if p.is_file()
            and not any(
                v in p.parts for v in ("__pycache__", ".pytest_cache", ".ruff_cache")
            )
        },
    }


def pins(batch, *paths):
    paths = [
        Path(__file__),
        Path(P.__file__),
        Path(T.__file__),
        Path(L.__file__),
        batch / "cells.json",
        *paths,
    ]
    paths += [
        p
        for p in (S.KIT / ".local-agents").rglob("*")
        if p.is_file()
        and p.suffix in {".py", ".json", ".md"}
        and "__pycache__" not in p.parts
    ]
    return {str(p): S.sha(p) for p in paths}
