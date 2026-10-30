"""Create-only material assembly; never planning, execution or acceptance."""

import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from . import capture_fixture_support as F
from . import capture_validation_facts as P
from . import compatibility_profile as COMPAT
from . import consolidated_harness as H
from . import generic_evidence as G
from . import static_focus_rules as RULES
from .reviewer_capture_envelope import _constant, _object, source_manifest

ROOT = Path(__file__).resolve().parent.parent
MATERIAL = (F.POLICY_PATH, F.PRODUCER, F.HELPER)


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_object(path):
    value = json.loads(
        path.read_text(encoding="utf-8-sig"),
        object_pairs_hook=_object,
        parse_constant=_constant,
    )
    if not isinstance(value, dict):
        raise ValueError("Preparation inputs must be JSON objects")
    return value


def build(root, packet_path, config_path, spec_path):
    """Return a byte-level plan. No subprocesses, model clients or mutations."""
    root = Path(root).resolve(strict=True)
    inputs = [packet_path, config_path, spec_path]
    initial = source_manifest(root, inputs, approved_paths=inputs)["files"]
    packet = read_object(root / packet_path)
    config = read_object(root / config_path)
    spec = read_object(root / spec_path)
    generic = G.selected(config)
    if packet.get("schema_version") != 2 or "parent_run_id" in packet:
        raise ValueError("Preparation requires a complete schema-2 packet, not inheritance")
    if set(spec) != {"schema_version", "source_paths", "target", "family", "cases"} or (
        type(spec["schema_version"]) is not int or spec["schema_version"] != 1
    ):
        raise ValueError("Invalid preparation specification fields")
    if config.get("bounded_execution_profile") != "bounded-v1":
        raise ValueError("Explicit bounded-v1 configuration required; never enabled implicitly")
    rules = COMPAT.proposal_rules(config, RULES)
    worker = F.load(ROOT / "worker-runtime.py", "bounded_preparation_worker")
    client = SimpleNamespace(structured_output=True, native_tools=None)
    runtime = worker.WorkerRuntime(root, packet, config, client)
    try:
        if (
            config.get("experimental_consolidated_harness") is not True
            or config.get("host_proposal_enabled") is not True
            or runtime.single_function is None
            or config.get("coordinator_enabled")
            or config.get("autoformat_on_ruff_failure") is not False
        ):
            raise ValueError("Existing isolated bounded configuration required")
        if (
            runtime.max_turns,
            runtime.hard_max_turns,
            runtime.invocation_timeout,
            runtime._limit("max_validation_runs", 0),
        ) != (12, 12, 900, 4):
            raise ValueError("Preparation does not change the registered execution budget")
        budget = H.recovery_budget(config)
        scope = runtime.packet["scope"]
        sources = spec["source_paths"]
        if not isinstance(sources, list) or set(sources) & set(MATERIAL):
            raise ValueError("Source manifest must exclude generated capture material")
        if len(sources) > 125:
            raise ValueError("Source manifest must leave three slots for capture material")
        # Check authority before reading any requested source bytes. Source manifest
        # then enforces exact spelling, aliases, reparse rejection and current hashes.
        for name in [*sources, *MATERIAL]:
            runtime._assert_read_allowed(name)
            if name not in scope["modify"] and not worker.path_matches_any(name, scope["readonly"]):
                raise ValueError("Unprotected preparation dependency: " + name)
        source_facts = source_manifest(root, sources, approved_paths=sources)["files"]
        tests = {path.split("::", 1)[0] for path in runtime.packet["focused_tests"]}
        if not tests or not tests <= source_facts.keys():
            raise ValueError("Manifest must include every focused protected test")
        for name in sources:
            if not name.endswith(".py"):
                continue
            for parent in (root / name).parents:
                if parent == root:
                    break
                init = (parent / "__init__.py").relative_to(root).as_posix()
                if (root / init).exists() and init not in source_facts:
                    raise ValueError("Explicit manifest omits package initializer: " + init)
        target = spec["target"]
        if not isinstance(target, dict) or set(target) != {"path", "module", "symbol"}:
            raise ValueError("Invalid preparation target")
        if any(target[k] != runtime.single_function[k] for k in ("path", "symbol")):
            raise ValueError("Preparation target differs from approved function")
        suffix = target["module"].replace(".", "/") + ".py"
        if target["path"] != suffix and not target["path"].endswith("/" + suffix):
            raise ValueError("Target module does not match its explicit source path")
        allowed = {tuple(v) for v in config.get("experimental_approved_imports", [])}
        if not allowed <= rules.IMPORT_CEILING:
            raise ValueError("Import authority exceeds existing ceiling")
        source = (root / target["path"]).read_text(encoding="utf-8-sig")
        rules.shape(source, target["symbol"], allowed)
        if {a["path"] for a in runtime.packet["edit_targets"]} != set(scope["modify"]):
            raise ValueError("Preparation requires an approved anchor for the writable file")
        for anchor in runtime.packet["edit_targets"]:
            if anchor["anchor"] not in source:
                raise ValueError("Approved edit anchor is absent")
        profile = runtime.validation_profile()
        commands = profile.get("commands", [])
        expected_capture = {
            "id": "actual-observations",
            "argv": [
                "{python}",
                "-B",
                "{repo}/" + F.PRODUCER,
                "--policy",
                F.POLICY_PATH,
            ],
        }
        if not generic and (
            len(commands) != 4
            or {c.get("id") for c in commands}
            != {"ruff-format", "ruff-check", "pyright", "actual-observations"}
            or expected_capture not in commands
        ):
            raise ValueError(
                "Existing complete configured profile required; no checks are added or removed"
            )
        if generic and (
            len(commands) != 3
            or {c.get("id") for c in commands} != G.CHECK_IDS
            or spec["family"] != G.PROFILE
            or spec["cases"] != []
        ):
            raise ValueError(
                "Generic source profile needs three complete checks and no typed observations"
            )
        python = runtime.python_path()
        producer = (ROOT / "bounded/capture_validation_facts.py").read_bytes()
        helper = (ROOT / "bounded/reviewer_capture_envelope.py").read_bytes()
        policy = (
            G.build_policy(runtime, copy.deepcopy(target), source_facts)
            if generic
            else P.validate_policy(
                {
                    "schema_version": 1,
                    "identity": {k: packet[k] for k in ("task_id", "unit_id", "run_id")},
                    "check_id": "actual-observations",
                    "producer_path": F.PRODUCER,
                    "producer_sha256": digest(producer),
                    "helper_path": F.HELPER,
                    "helper_sha256": digest(helper),
                    "python": {"path": str(python), "sha256": P.digest(python)},
                    "target": copy.deepcopy(target),
                    "source_paths": list(sources),
                    "readonly_hashes": {
                        p: h for p, h in source_facts.items() if p not in scope["modify"]
                    },
                    "family": spec["family"],
                    "cases": copy.deepcopy(spec["cases"]),
                }
            )
        )
        policy_bytes = encoded(policy)
        prepared_config = copy.deepcopy(config)
        sha_key = G.CONFIG_SHA if generic else "experimental_capture_policy_sha256"
        prepared_config[sha_key] = digest(policy_bytes)
        output = ".agent/prepared/" + packet["run_id"]
        _, output_path = runtime.editor.resolve(output)
        if output_path.exists():
            raise FileExistsError("Prepared run output already exists: " + output)
        material = (
            {G.POLICY_PATH: policy_bytes}
            if generic
            else {F.PRODUCER: producer, F.HELPER: helper, F.POLICY_PATH: policy_bytes}
        )
        outputs = {
            **material,
            output + "/packet.json": (root / packet_path).read_bytes(),
            output + "/config.json": encoded(prepared_config),
        }
        for name in outputs:
            _, destination = runtime.editor.resolve(name)
            if destination.exists():
                raise FileExistsError("Preparation never overwrites: " + name)
        # A second observation binds generated hashes to the bytes actually read.
        if source_manifest(root, inputs, approved_paths=inputs)["files"] != initial or (
            source_manifest(root, sources, approved_paths=sources)["files"] != source_facts
        ):
            raise ValueError("Preparation inputs changed while building the plan")
        receipt = {
            "schema_version": 1,
            "identity": policy["identity"],
            "input_hashes": {**initial, **source_facts},
            "output_hashes": {p: digest(raw) for p, raw in outputs.items()},
            "python": policy["python"],
            "config_changed_keys": [sha_key],
            "packet_preserved_byte_for_byte": True,
            "execution_budget": budget,
            "model_calls": 0,
            "commands_executed": 0,
            "validation_credit": False,
            "qualification": "none; preparation is not preflight, passing checks or acceptance",
            "limitations": "Explicit dependency list only, not complete import discovery. Run installed offline preflight/replay before live. One unit per fresh isolated workspace.",
            "next_inputs": {"packet": output + "/packet.json", "config": output + "/config.json"},
        }
        outputs[output + "/preparation.json"] = encoded(receipt)
        return receipt, outputs, runtime.editor
    finally:
        runtime.close()


def prepare(root, packet_path, config_path, spec_path, *, apply=False):
    receipt, outputs, editor = build(root, packet_path, config_path, spec_path)
    if apply:
        # Recheck all source/input versions and all destinations before first write.
        # Exclusive creation prevents overwriting even if another process races us.
        names = list(receipt["input_hashes"])
        if source_manifest(root, names, approved_paths=names)["files"] != receipt["input_hashes"]:
            raise ValueError("Preparation inputs changed before apply")
        if P.digest(receipt["python"]["path"]) != receipt["python"]["sha256"]:
            raise ValueError("Preparation interpreter changed before apply")
        for name in outputs:
            if editor.resolve(name)[1].exists():
                raise FileExistsError("Preparation destination appeared: " + name)
        for name, raw in outputs.items():
            _, path = editor.resolve(name)
            path.parent.mkdir(parents=True, exist_ok=True)
            # Recheck after directory creation; no rollback/delete of user data.
            _, path = editor.resolve(name)
            with path.open("xb") as stream:
                stream.write(raw)
        # Receipt is written last. Partial I/O failure is retained, never certified
        # as complete and never automatically overwritten by a subsequent attempt.
    return {"applied": apply, "create": list(outputs), **receipt}
