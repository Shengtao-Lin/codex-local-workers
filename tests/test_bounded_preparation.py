"""Installed create-only preparation; no actual Worker/model success credit."""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import test_installable_bounded as I

sys.path.insert(0, str(I.KIT / ".local-agents"))
from bounded import prepare_unit as P


def project(root, topic="labels", label="prepared-control"):
    I.INSTALL.install(I.KIT, root, apply=True)
    template = I.L.BATCH / "templates" / topic
    for name in ("src", "tests"):
        shutil.copytree(template / name, root / name)
    shutil.copyfile(template / "pyproject.toml", root / "pyproject.toml")
    prior = I.L.BATCH / "cells" / (topic + "-1") / "isolated"
    packet = I.S.read(prior / ".agent/packet.json")
    packet.update({key: label for key in ("task_id", "unit_id", "run_id")})
    config = I.S.read(I.L.SEED / ".agent/config.json")
    config["bounded_execution_profile"] = "bounded-v1"
    config["bounded_compatibility_profile"] = "flat-v1"
    config["coder_single_function"] = I.S.read(prior / ".agent/config.json")[
        "coder_single_function"
    ]
    spec = {
        "schema_version": 1,
        "source_paths": [p for p in packet["scope"]["readonly"] if p not in P.MATERIAL]
        + packet["scope"]["modify"],
        "target": {
            "path": "src/product/code.py",
            "module": "product.code",
            "symbol": I.L.TASKS[topic]["symbol"],
        },
        "family": "json-call-model-dump-v1",
        "cases": I.L.TASKS[topic]["cases"],
    }
    for name, value in (("packet", packet), ("config", config), ("capture-spec", spec)):
        I.S.save(root / f".agent/{name}.json", value)
    return packet, config, spec


def prepare(root, apply=False):
    return P.prepare(
        root,
        ".agent/packet.json",
        ".agent/config.json",
        ".agent/capture-spec.json",
        apply=apply,
    )


def tree(root):
    return {
        p.relative_to(root).as_posix(): I.S.sha(p)
        for p in root.rglob("*")
        if p.is_file()
    }


def update(root, name, value):
    (root / f".agent/{name}.json").write_text(json.dumps(value), encoding="utf-8")


def cli(root, *extra):
    return subprocess.run(
        [
            I.S.PYTHON,
            "-B",
            root / ".local-agents/local-bounded-prepare.py",
            "--packet",
            ".agent/packet.json",
            "--config",
            ".agent/config.json",
            "--capture-spec",
            ".agent/capture-spec.json",
            *extra,
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_preview_does_not_write_or_execute(monkeypatch):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        project(root)
        before = tree(root)

        def deny(*args, **kwargs):
            raise AssertionError("Preparation must not execute a command or model")

        monkeypatch.setattr(subprocess, "run", deny)
        result = prepare(root)
        assert result["applied"] is False
        assert result["model_calls"] == result["commands_executed"] == 0
        assert result["validation_credit"] is False
        assert tree(root) == before


def test_installed_cli_preserves_inputs_and_generates_equivalent_policy():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        packet, config, spec = project(root)
        before = tree(root)
        preview = cli(root)
        assert preview.returncode == 0, preview.stderr
        assert tree(root) == before
        result = cli(root, "--apply")
        assert result.returncode == 0, result.stderr
        receipt = json.loads(result.stdout)
        out = root / ".agent/prepared/prepared-control"
        assert (out / "packet.json").read_bytes() == (
            root / ".agent/packet.json"
        ).read_bytes()
        prepared_config = I.S.read(out / "config.json")
        assert {
            k
            for k in config.keys() | prepared_config.keys()
            if config.get(k) != prepared_config.get(k)
        } == {"experimental_capture_policy_sha256"}
        assert all(I.S.sha(root / p) == sha for p, sha in before.items())
        assert set(tree(root)) - set(before) == set(receipt["create"])
        policy = I.S.read(root / P.F.POLICY_PATH)
        assert policy["target"] == spec["target"]
        assert policy["cases"] == spec["cases"]
        assert policy["identity"] == {
            k: packet[k] for k in ("task_id", "unit_id", "run_id")
        }
        assert prepared_config["experimental_capture_policy_sha256"] == I.S.sha(
            root / P.F.POLICY_PATH
        )
        after = tree(root)
        repeated = cli(root, "--apply")
        assert repeated.returncode == 2 and "already exists" in repeated.stderr
        assert tree(root) == after
        assert not (root / "benchmarks").exists()


@pytest.mark.parametrize(
    "bad",
    [
        "missing-readonly",
        "forbidden-source",
        "target-symbol",
        "target-module",
        "missing-package-init",
        "missing-test",
        "escape",
        "case-alias",
        "unknown-field",
        "missing-check",
        "capture-command",
        "budget",
        "opt-in",
        "anchor",
        "output-conflict",
        "missing-anchor",
        "inheritance",
    ],
)
def test_invalid_preparation_is_rejected_before_any_write(bad):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        packet, config, spec = project(root)
        if bad == "missing-readonly":
            packet["scope"]["readonly"].remove(P.F.PRODUCER)
        elif bad == "forbidden-source":
            spec["source_paths"].append(".local-agents/config.example.json")
        elif bad == "target-symbol":
            spec["target"]["symbol"] = "not_the_approved_function"
        elif bad == "target-module":
            spec["target"]["module"] = "product.other"
        elif bad == "missing-package-init":
            spec["source_paths"].remove("src/product/__init__.py")
        elif bad == "missing-test":
            spec["source_paths"].remove(packet["focused_tests"][0])
        elif bad == "escape":
            spec["source_paths"].append("../outside.py")
        elif bad == "case-alias":
            spec["source_paths"].append("src/Product/code.py")
        elif bad == "unknown-field":
            spec["expected_results"] = ["never forwarded"]
        elif bad == "missing-check":
            config["validation_profiles"][packet["validation_profile"]][
                "commands"
            ].pop()
        elif bad == "capture-command":
            commands = config["validation_profiles"][packet["validation_profile"]][
                "commands"
            ]
            next(c for c in commands if c["id"] == "actual-observations")["argv"] = [
                "{python}",
                "-c",
                "print('fake')",
            ]
        elif bad == "budget":
            packet["limits"]["max_model_turns"] = 6
        elif bad == "opt-in":
            del config["bounded_execution_profile"]
        elif bad == "anchor":
            packet["edit_targets"][0]["anchor"] = "def nonexistent("
        elif bad == "missing-anchor":
            packet["edit_targets"] = []
        elif bad == "inheritance":
            packet["parent_run_id"] = "an-existing-run"
        elif bad == "output-conflict":
            I.S.save(root / P.F.POLICY_PATH, {"existing": "preserve"})
        for name, value in (
            ("packet", packet),
            ("config", config),
            ("capture-spec", spec),
        ):
            update(root, name, value)
        before = tree(root)
        result = cli(root, "--apply")
        assert result.returncode == 2, (bad, result.stdout, result.stderr)
        assert tree(root) == before, bad


def test_duplicate_json_is_not_silently_normalized():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        project(root)
        (root / ".agent/capture-spec.json").write_text(
            '{"schema_version":1,"schema_version":1}', encoding="utf-8"
        )
        before = tree(root)
        result = cli(root, "--apply")
        assert result.returncode == 2 and "duplicate JSON key" in result.stderr
        assert tree(root) == before


def test_changed_input_between_plan_and_apply_rejected(monkeypatch):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        project(root)
        original = P.build

        def drift(*args):
            result = original(*args)
            with (root / "src/product/code.py").open("a", encoding="utf-8") as stream:
                stream.write("\n# concurrent user change\n")
            return result

        monkeypatch.setattr(P, "build", drift)
        with pytest.raises(ValueError, match="changed before apply"):
            prepare(root, apply=True)
        assert not (root / "acceptance").exists()
        assert not (root / ".agent/prepared").exists()


@pytest.mark.parametrize("topic", ["labels", "unique", "route"])
def test_prepared_inputs_complete_installed_offline_chain(topic):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        project(root, topic, "prepared-" + topic)
        result = cli(root, "--apply")
        assert result.returncode == 0, result.stderr
        receipt = json.loads(result.stdout)
        I.S.save(
            root / ".agent/replay.json",
            [{"kind": "replacement", "content": I.L.TASKS[topic]["reference"]}],
        )
        run = subprocess.run(
            [
                I.S.PYTHON,
                "-B",
                root / ".local-agents/local-bounded-unit.py",
                "--mode",
                "unit",
                "--packet",
                receipt["next_inputs"]["packet"],
                "--config",
                receipt["next_inputs"]["config"],
                "--report",
                ".agent/unit-report.json",
                "--review-report",
                ".agent/reviewer-report.json",
                "--summary",
                ".agent/unit-summary.json",
                "--replay",
                ".agent/replay.json",
            ],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        assert run.returncode == 0, (run.stdout, run.stderr)
        report = I.S.read(root / ".agent/unit-report.json")
        actual = report["consolidated_harness"]["actual"]
        assert actual["edits"] == actual["post_edit_checks"] == 1
        summary = I.S.read(root / ".agent/unit-summary.json")
        assert summary["reviewer_started"] is False
        assert summary["reviewer_input_authenticated"] is True
        assert summary["reviewer_decision"] == "NOT_RUN"
        assert not (root / "benchmarks").exists()


def test_incomplete_apply_never_claims_completion_or_overwrites(monkeypatch):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        project(root)
        original = Path.open

        def fail_one(path, mode="r", *args, **kwargs):
            if path == root / P.F.POLICY_PATH and mode == "xb":
                raise OSError("simulated interrupted filesystem write")
            return original(path, mode, *args, **kwargs)

        monkeypatch.setattr(Path, "open", fail_one)
        with pytest.raises(OSError, match="simulated interrupted"):
            prepare(root, apply=True)
        assert (root / P.F.PRODUCER).exists()
        assert not (root / ".agent/prepared/prepared-control/preparation.json").exists()
        before = tree(root)
        with pytest.raises(FileExistsError, match="never overwrites"):
            prepare(root, apply=True)
        assert tree(root) == before


def test_output_parent_reparse_is_rejected_without_new_files(monkeypatch):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        project(root)
        before = tree(root)
        loader = P.F.load

        def marked(path, name):
            module = loader(path, name)
            original = module.SAFE_EDIT.is_reparse_point
            monkeypatch.setattr(
                module.SAFE_EDIT,
                "is_reparse_point",
                lambda path: path == root / "acceptance" or original(path),
            )
            return module

        monkeypatch.setattr(P.F, "load", marked)
        with pytest.raises(ValueError, match="reparse"):
            prepare(root, apply=True)
        assert tree(root) == before


def test_preview_does_not_take_or_remove_existing_worker_lock():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        project(root)
        I.S.save(root / ".agent/local-worker-write.lock", {"unrelated": "preserve"})
        before = tree(root)
        prepare(root)
        assert tree(root) == before
