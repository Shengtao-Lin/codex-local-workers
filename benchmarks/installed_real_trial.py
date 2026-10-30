"""Small real-source transfers, keeping installed runtime and evidence types fixed."""

import argparse
import os
import shutil
import tempfile
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import capture_fixture_support as F
import installed_scope_trial as I
import limited_family_trial as L
import normal_task_trial as N
from test_installable_bounded import INSTALL

BATCH = I.BASE / "installed-real-transfer-20261021-1"
UP = Path("F:/ChatGPT/agent-evaluation-harness/src/evaluation_harness")
ORDER = ["binding-1", "hash-1", "hash-2", "binding-2"]
TASKS = {
    "binding": {
        "origin": "telemetry/ingestion.py",
        "symbol": "application_binding_path",
        "header": "from urllib.parse import quote, urlencode\n",
        "contract": "Extend application_binding_path to reject an empty workspace_id, application_id or environment string with ValueError. Preserve its signature and every nonempty-string encoding behavior: application_id is ONE percent-encoded path segment, query values are encoded using existing urlencode semantics and key order workspace_id then environment. Do not strip or normalize nonempty values, including whitespace, percent signs, slashes, Unicode and query delimiters. No network or filesystem calls. Other input types are outside this string-typed contract.",
        "reference": """def application_binding_path(workspace_id: str, application_id: str, environment: str) -> str:
    if not workspace_id or not application_id or not environment:
        raise ValueError("binding fields must be nonempty")
    return f"/v1/applications/{quote(application_id, safe='')}?" + urlencode(
        {"workspace_id": workspace_id, "environment": environment}
    )
""",
        "public": """import pytest
from product.code import application_binding_path

def test_encoded_binding():
    assert application_binding_path("work space", "app/id", "dev&qa") == "/v1/applications/app%2Fid?workspace_id=work+space&environment=dev%26qa"

@pytest.mark.parametrize("values", [("", "app", "dev"), ("w", "", "dev"), ("w", "app", "")])
def test_each_empty(values):
    with pytest.raises(ValueError):
        application_binding_path(*values)
""",
        "private": """from urllib.parse import quote, urlencode
from product.code import application_binding_path

def test_nonempty_exact_compatibility():
    for workspace, app, environment in [(" ", "雪/%", "?a=1"), ("a+b", "../x", "qa/dev"), ("%", " ", "雪")]:
        expected = "/v1/applications/" + quote(app, safe="") + "?" + urlencode({"workspace_id": workspace, "environment": environment})
        assert application_binding_path(workspace, app, environment) == expected
""",
        "cases": [
            {"args": list(v), "kwargs": {}}
            for v in [("w", "app/id", "dev"), ("", "app", "dev")]
        ],
    },
    "hash": {
        "origin": "jobs/queue.py",
        "symbol": "request_hash",
        "header": "import hashlib\nfrom typing import Any\nfrom product.dependencies import canonical_json\n",
        "contract": "Extend request_hash(payload: dict[str, Any]) so ONLY the top-level key _sampling_debug is ignored when computing the existing SHA256 of canonical_json bytes. Preserve the signature, hexadecimal digest format and exact existing canonical serialization for every other field. Nested _sampling_debug keys remain meaningful; absence of the ignored key retains the old digest exactly. Do not mutate payload or nested objects. False, zero, None, empty dictionaries and strings are meaningful values, not absent fields. Use the existing read-only canonical_json semantics, including its unsupported-object default=str behavior; do not alter that helper or introduce new rejection rules.",
        "reference": """def request_hash(payload: dict[str, Any]) -> str:
    filtered = {key: value for key, value in payload.items() if key != "_sampling_debug"}
    return hashlib.sha256(canonical_json(filtered)).hexdigest()
""",
        "public": """import copy
import hashlib
from product.code import request_hash
from product.dependencies import canonical_json

def test_top_level_debug_only():
    base = {"job": "score", "count": 0, "enabled": False}
    payload = {**base, "_sampling_debug": {"note": "trace"}}
    before = copy.deepcopy(payload)
    expected = hashlib.sha256(canonical_json(base)).hexdigest()
    assert request_hash(payload) == expected
    assert payload == before
    assert request_hash(base) == expected

def test_nested_debug_is_meaningful():
    payload = {"data": {"_sampling_debug": False, "x": None}}
    assert request_hash(payload) == hashlib.sha256(canonical_json(payload)).hexdigest()
    assert request_hash(payload) != request_hash({"data": {"x": None}})
""",
        "private": """import hashlib
from datetime import date
from product.code import request_hash
from product.dependencies import canonical_json

def test_canonical_values_and_nonmutation():
    nested = {"雪": [False, 0, None, "", {}], "date": date(2026, 1, 1)}
    payload = {"data": nested, "_sampling_debug": None}
    assert request_hash(payload) == hashlib.sha256(canonical_json({"data": nested})).hexdigest()
    assert payload["data"] is nested and "_sampling_debug" in payload
    assert nested["date"] == date(2026, 1, 1)
    assert request_hash({"_sampling_debug": False}) == request_hash({})
    assert request_hash({"x": False}) != request_hash({})
    assert request_hash({"b": 2, "a": 1}) == request_hash({"a": 1, "b": 2})
""",
        "cases": [
            {"args": [v], "kwargs": {}}
            for v in [
                {"x": 0, "_sampling_debug": "note"},
                {"nested": {"_sampling_debug": False}},
            ]
        ],
    },
}


def prepare(used):
    prior = S.read(I.BATCH / "decision.json")
    assert prior["accepted"] == 4 and 0 <= used < 50
    rows, origins = {}, {}
    for topic, spec in TASKS.items():
        origin = UP / spec["origin"]
        initial_hash = S.sha(origin)
        start = T.extract(origin, spec["symbol"])
        assert S.sha(origin) == initial_hash
        origins[topic] = {"path": str(origin), "sha256": initial_hash}
        template = BATCH / "templates" / topic
        T.write(template / "src/product/__init__.py", "")
        T.write(template / "src/product/code.py", spec["header"] + "\n\n" + start)
        dependencies = spec["header"]
        if topic == "hash":
            helper = UP / "canonical/fingerprint.py"
            helper_hash = S.sha(helper)
            text = "import json\nfrom typing import Any\n\n\n" + T.extract(
                helper, "canonical_json"
            )
            assert S.sha(helper) == helper_hash
            T.write(template / "src/product/dependencies.py", text)
            dependencies += "\nReadonly dependency source:\n" + text
            origins[topic]["dependency"] = {"path": str(helper), "sha256": helper_hash}
        T.write(template / "tests/test_contract.py", spec["public"])
        private = BATCH / "private" / topic / "test_independent.py"
        T.write(private, spec["private"])
        shutil.copyfile(L.SEED / "pyproject.toml", template / "pyproject.toml")
        proof = BATCH / "reference-checks" / topic
        shutil.copytree(template, proof)
        (proof / "src/product/code.py").write_text(
            spec["header"] + "\n\n" + spec["reference"], encoding="utf-8"
        )
        for root in (template, proof):
            for args in (("check", "--select", "I", "--fix"), ("format",)):
                assert (
                    T.run([S.PYTHON, "-B", "-m", "ruff", *args, "src", "tests"], root)[
                        "exit_code"
                    ]
                    == 0
                )
        reference = L.checks(proof, private)
        baseline = T.run([S.PYTHON, "-B", "-m", "pytest", "-q", "tests"], template)
        S.save(
            BATCH / "task-controls" / (topic + ".json"),
            {"baseline": baseline, "reference": reference},
        )
        assert baseline["exit_code"] == 1 and all(
            c["exit_code"] == 0 for c in reference
        )
        for cell in (c for c in ORDER if c.startswith(topic + "-")):
            with tempfile.TemporaryDirectory(
                prefix="real-worker-install-"
            ) as directory:
                staging = Path(directory)
                INSTALL.install(S.KIT, staging, apply=True)
                root = BATCH / "cells" / cell / "isolated"
                shutil.copytree(staging, root)
            shutil.copytree(template / "src", root / "src")
            shutil.copytree(template / "tests", root / "tests")
            shutil.copyfile(template / "pyproject.toml", root / "pyproject.toml")
            identity = {
                k: BATCH.name + "-" + cell for k in ("task_id", "unit_id", "run_id")
            }
            packet = S.read(L.SEED / ".agent/packet.json")
            packet.update(
                identity,
                feature_id="real-slice-" + topic,
                goal=spec["contract"],
                primary_plan_sha256=S.sha(__file__),
            )
            target = "src/product/code.py"
            sources = [
                p.relative_to(root).as_posix()
                for p in root.rglob("*")
                if p.is_file()
                and (
                    p.relative_to(root).parts[0] in {"src", "tests"}
                    or p.name == "pyproject.toml"
                )
            ]
            packet["scope"]["readonly"] = [p for p in sources if p != target] + [
                F.POLICY_PATH,
                F.PRODUCER,
                F.HELPER,
            ]
            packet["owned_contract_ids"] = [topic]
            packet["edit_targets"] = [
                {"path": target, "anchor": "def " + spec["symbol"] + "("}
            ]
            packet["required_behavior"] = [
                {
                    "id": topic,
                    "text": spec["contract"],
                    "risk_floor": "high",
                    "implementation_ref": {"path": target, "symbol": spec["symbol"]},
                }
            ]
            packet["acceptance_criteria"] = [
                {
                    "id": topic,
                    "text": "Full contract, protected compatibility and complete strict profile",
                }
            ]
            packet["review_feedback"] = []
            config = S.read(L.SEED / ".agent/config.json")
            config["bounded_execution_profile"] = "bounded-v1"
            config["coder_single_function"] = {
                "path": target,
                "symbol": spec["symbol"],
                "dependencies": dependencies,
            }
            _, digest = F.install_material(
                root,
                identity,
                source_paths=sources,
                target={
                    "path": target,
                    "module": "product.code",
                    "symbol": spec["symbol"],
                },
                family="json-call-model-dump-v1",
                cases=spec["cases"],
                writable=[target],
                python=S.PYTHON,
            )
            config["experimental_capture_policy_sha256"] = digest
            I.refresh_material(root, config)
            S.save(root / ".agent/packet.json", packet)
            S.save(root / ".agent/config.json", config)
            preflight = I.command(root, "preflight")
            preflight[preflight.index("--report") + 1] = str(
                root / ".agent/preflight.json"
            )
            result = T.run(preflight, root)
            S.save(BATCH / "preflight" / (cell + ".json"), result)
            assert result["exit_code"] == 0
            if cell.endswith("-1"):
                replay_root = BATCH / "full-chain-replay" / topic / "isolated"
                shutil.copytree(root, replay_root)
                replay = replay_root.parent / "reference.json"
                S.save(
                    replay, [{"replacement": T.extract(proof / target, spec["symbol"])}]
                )
                control = T.run(
                    I.command(replay_root, replay=replay), replay_root, timeout=180
                )
                S.save(replay_root.parent / "process.json", control)
                assert control["exit_code"] == 0
            rows[cell] = {
                "root": str(root),
                "topic": topic,
                "identity": identity,
                "target": target,
                "private_tests": str(private),
                "files": {
                    p.relative_to(root).as_posix(): S.sha(p)
                    for p in root.rglob("*")
                    if p.is_file()
                    and not any(
                        v in p.parts
                        for v in ("__pycache__", ".pytest_cache", ".ruff_cache")
                    )
                },
            }
    S.save(BATCH / "cells.json", rows)
    S.save(BATCH / "origins.json", origins)
    pins = [
        Path(__file__),
        Path(I.__file__),
        BATCH / "cells.json",
        BATCH / "origins.json",
    ]
    pins += [
        p
        for p in (S.KIT / ".local-agents").rglob("*.py")
        if "__pycache__" not in p.parts
    ]
    pins += list((BATCH / "private").rglob("*.py"))
    S.save(
        BATCH / "registration.json",
        {
            "order": ORDER,
            "registered": 4,
            "weekly_used_start": used,
            "weekly_stop": 50,
            "batch_seconds": 10800,
            "pins": {str(p): S.sha(p) for p in pins},
            "gate": "4/4 independent complete accepts, each task2/2, no runtime hints/code takeover/safety drift",
            "continue_rule": "Ordinary implementation failure HOLD and complete fixed order; infrastructure/drift/safety/time/weekly50 stop; no resampling",
            "candidate": "Same installed bounded-v1 and fixed budgets/Reviewer as installed repair batch",
            "risk": "high feature/unit/integration due public serialization and request identity compatibility; no upstream deployment or source changes",
            "exposure": "Two new requested behaviors on real unchanged copied sibling functions; JSON-native scope only; reference remains outside Worker roots",
            "roles": "Qwen Coder, fresh Muse Reviewer; source located by Primary, no contrived Explorer call; Coordinator NOT_RUN",
            "Primary": "Prepared contracts/public-private tests/reference controls; no algorithm hints in live; preparation costs retained, savings unknown",
        },
    )
    print("Four real-source transfer units frozen")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=("prepare", "run"))
    p.add_argument("--cell", choices=ORDER)
    p.add_argument("--weekly-used", type=int, required=True)
    p.add_argument("--observed-at", type=float)
    args = p.parse_args()
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if args.mode == "prepare":
        prepare(args.weekly_used)
    else:
        N.run(
            args.cell,
            args.weekly_used,
            args.observed_at,
            batch=BATCH,
            order=ORDER,
            build_command=I.command,
            usage_limit=50,
            batch_seconds=10800,
        )
