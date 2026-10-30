"""Prepare one authenticated-by-host task without executing project/model code."""

import copy
import hashlib
import importlib.util
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

from general_state import StateError, TaskLedger, fingerprint, identifier, read
from strata_artifacts import save

RUNTIME = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RUNTIME))
spec = importlib.util.spec_from_file_location(
    "strata_general_worker", RUNTIME / "worker-runtime.py"
)
W = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = W
spec.loader.exec_module(W)

EXCLUDED = W.EXCLUDED_PARTS | {
    "acceptance_private",
    "dist",
    "build",
    ".mypy_cache",
    ".pyright",
}
CONTROL_NAMES = {
    "pyproject.toml",
    "pytest.ini",
    "setup.cfg",
    "conftest.py",
    "ruff.toml",
    ".ruff.toml",
    "pyrightconfig.json",
}
INVENTORY_LIMITS = {
    "model": (125, 8 * 1024 * 1024),
    "checks": (2048, 32 * 1024 * 1024),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def forbidden_name(path):
    return any(
        p in EXCLUDED
        or p == ".env"
        or p.startswith(".env.")
        or p.lower() in {"credentials", "secrets", "id_rsa", "id_ed25519"}
        for p in Path(path).parts
    )


def manifest(root, packet, editor, *, purpose="model"):
    max_files, max_bytes = INVENTORY_LIMITS[purpose]
    paths, total_bytes, visited = {}, 0, 0
    started = time.monotonic()

    def candidates(target):
        nonlocal visited
        if not target.is_dir():
            yield target
            return
        for current, dirs, files in os.walk(target, followlinks=False):
            visited += 1 + len(dirs) + len(files)
            if visited > 10000 or time.monotonic() - started > 10:
                raise StateError("Manifest traversal resource bound exceeded: " + purpose)
            dirs[:] = [
                d
                for d in dirs
                if d not in EXCLUDED and not W.SAFE_EDIT.is_reparse_point(Path(current) / d)
            ]
            yield from (Path(current) / f for f in files)

    for name in packet["scope"]["read"]:
        if name == "." or forbidden_name(name):
            raise StateError("Approve explicit source/test roots, not project/control roots")
        _, target = editor.resolve(name)
        if not target.exists():
            if name in packet["scope"]["create"]:
                continue
            raise StateError("Approved evidence missing: " + name)
        for path in candidates(target):
            relative = path.relative_to(root).as_posix()
            if forbidden_name(relative) or W.path_matches_any(
                relative, packet["scope"]["forbidden"]
            ):
                continue
            editor.resolve(relative)
            if path.is_file() and path.suffix.lower() in {
                ".py",
                ".toml",
                ".json",
                ".ini",
                ".cfg",
                ".md",
                ".txt",
            }:
                if relative in paths:
                    continue
                if len(paths) >= max_files:
                    raise StateError(
                        f"scope_too_large: {purpose} manifest requires 1..{max_files} files"
                    )
                with path.open("rb") as stream:
                    raw = stream.read(max_bytes - total_bytes + 1)
                total_bytes += len(raw)
                if total_bytes > max_bytes or time.monotonic() - started > 10:
                    raise StateError("Manifest bytes/time resource bound exceeded: " + purpose)
                paths[relative] = hashlib.sha256(raw).hexdigest()
    if not paths:
        raise StateError(
            f"scope_too_large or empty: {purpose} manifest requires 1..{max_files} files"
        )
    if len({p.casefold() for p in paths}) != len(paths):
        raise StateError("Case aliases in evidence manifest")
    return {p: paths[p] for p in sorted(paths)}


def build(root, task, config):
    root = Path(root).resolve(strict=True)
    task, config = copy.deepcopy(task), copy.deepcopy(config)
    from review_impl_binding import validate_profile as validate_review_impl_binding

    validate_review_impl_binding(config, "implement")
    from task_continuation import validate_config

    validate_config(config, "implement")
    from failed_draft_diagnostic import validate_profile

    validate_profile(config, "implement")
    capabilities = task.pop("capabilities", {})
    if config.get("strata_version_references") not in (None, "observed-v1"):
        raise StateError("Unknown Strata version-reference profile")
    from general_editing import validate_profile

    validate_profile(config)
    if config.get("strata_execution_profile") != "strata-unit-v1":
        raise StateError("Explicit strata-unit-v1 opt-in required")
    if config.get("coordinator_enabled") or config.get("coder_single_function"):
        raise StateError("General task cannot mix legacy function/Coordinator modes")
    if config.get("coder_model") != "iq3_s":
        raise StateError("Only current iq3_s qualified for this candidate")
    task_id = identifier(task["task_id"])
    packet = {**task, "schema_version": 2, "run_id": "prepare-" + task_id}
    packet.setdefault("edit_targets", [])
    packet.setdefault("validation_profile", "project-strict")
    packet.setdefault("acceptance_scenarios", task.get("acceptance_criteria", []))
    config.update(
        {
            "invocation_timeout_seconds": 1800,
            "max_model_turns": 24,
            "hard_max_model_turns": 24,
            "command_timeout_seconds": 180,
            "autoformat_on_ruff_failure": False,
            "autoformat_on_diff_whitespace": False,
            "diagnostic_logging": True,
        }
    )
    packet = W.validate_packet(packet)
    from recovery_evidence import validate as validate_recovery_evidence

    validate_recovery_evidence(config, "implement", packet, root)
    writable = packet["scope"]["modify"] + packet["scope"]["create"]
    tests = packet["supplemental_tests"]
    source = set(writable) - set(tests)
    unit_kind = config.get("experimental_strata_unit_kind")
    if unit_kind not in (None, "test-repair-v1"):
        raise StateError("Unknown explicit Strata unit kind")
    if unit_kind == "test-repair-v1":
        if (
            source
            or not 1 <= len(tests) <= 2
            or set(writable) != set(tests)
            or len(writable) != len(set(writable))
            or capabilities
            or config.get("experimental_strata_capabilities") is True
            or any(
                not p.startswith("tests/")
                or not Path(p).name.startswith("test_")
                or not p.endswith(".py")
                for p in tests
            )
        ):
            raise StateError(
                "Test repair requires only1..2 explicitly owned tests/test_*.py files;no source writes or optional capabilities"
            )
    elif not source or len(source) > 4 or len(tests) > 2 or len(writable) != len(set(writable)):
        raise StateError("Approve 1..4 source and at most2 supplemental test files")
    if any(
        not p.endswith(".py") or forbidden_name(p) or Path(p).name in CONTROL_NAMES
        for p in writable
    ):
        raise StateError("Only explicit Python source/supplemental tests writable")
    if len({p.casefold() for p in writable}) != len(writable):
        raise StateError("Writable aliases")
    anchors = {t["path"]: t["anchor"] for t in packet["edit_targets"]}
    runtime = W.WorkerRuntime(root, packet, config, SimpleNamespace())
    facts = manifest(root, packet, runtime.editor)
    from review_impl_binding import require_bound_paths

    require_bound_paths(config, packet, facts, read_source=runtime.editor.read_bytes)
    from capability_policy import validate_capabilities

    capabilities = validate_capabilities(
        {"mode": "implement", "capabilities": capabilities}, config, facts
    )
    if not set(packet["scope"]["modify"]) <= facts.keys():
        raise StateError("Writable existing files absent from source manifest")
    for path in packet["scope"]["modify"]:
        if path not in anchors or anchors[path] not in (root / path).read_text(
            encoding="utf-8-sig"
        ):
            raise StateError("Existing writable file needs real stable anchor: " + path)
    protected_tests = {p.split("::", 1)[0] for p in packet["focused_tests"]} - set(tests)
    if not protected_tests or not protected_tests <= facts.keys() - set(writable):
        raise StateError("Real protected focused tests required")
    for name in CONTROL_NAMES:
        if (root / name).is_file() and name not in facts:
            raise StateError("Explicitly approve project check configuration: " + name)
    profile = runtime.validation_profile()
    commands = profile.get("commands", [])
    ids = [c["id"] for c in commands]
    required = config.get("required_check_ids")
    if not required or set(ids) != set(required) or len(ids) != len(set(ids)):
        raise StateError("Frozen required_check_ids must match all configured checks")
    for c in commands:
        if (
            not isinstance(c.get("argv"), list)
            or not c["argv"]
            or any(not isinstance(a, str) or not a for a in c["argv"])
        ):
            raise StateError("Invalid trusted check argv")
        c["run_on_test_failure"] = True
    check_roots = config.get("check_input_roots", [])
    if not isinstance(check_roots, list) or any(not isinstance(p, str) for p in check_roots):
        raise StateError("check_input_roots must be explicit project-relative roots")
    check_facts = (
        manifest(
            root,
            {
                "scope": {
                    "read": check_roots,
                    "create": [],
                    "forbidden": packet["scope"]["forbidden"],
                }
            },
            runtime.editor,
            purpose="checks",
        )
        if check_roots
        else {}
    )
    all_facts = {**facts, **check_facts}
    for command in commands:
        for argument in command["argv"][1:]:
            if argument.startswith("-") or "{" in argument or Path(argument).is_absolute():
                continue
            candidate = root / argument
            if candidate.is_file() and candidate.suffix == ".py" and argument not in all_facts:
                raise StateError("Check source not bound; approve check_input_roots: " + argument)
            if candidate.is_dir():
                required_paths = {
                    p.relative_to(root).as_posix()
                    for p in candidate.rglob("*.py")
                    if not forbidden_name(p.relative_to(root))
                }
                if not required_paths <= all_facts.keys():
                    raise StateError(
                        "Check directory not fully bound; approve check_input_roots: " + argument
                    )
    if not runtime.python_path().is_file():
        raise StateError("Project interpreter missing")
    # Profile dict is the trusted config's mutable reference, already normalized.
    config["validation_profiles"][packet["validation_profile"]] = profile
    policy = {
        "schema_version": 1,
        "profile": "strata-unit-v1",
        "capabilities": capabilities,
        "task_id": task_id,
        "initial_hashes": facts,
        "check_hashes": check_facts,
        "readonly_hashes": {p: h for p, h in facts.items() if p not in writable},
        "create": packet["scope"]["create"],
        "python": {
            "path": str(runtime.python_path()),
            "sha256": sha(runtime.python_path()),
        },
        "runtime": {
            p.relative_to(RUNTIME).as_posix(): sha(p)
            for p in RUNTIME.rglob("*")
            if p.is_file() and p.suffix in {".py", ".mjs"}
        },
    }
    if unit_kind:
        policy["unit_kind"] = unit_kind
    packet.pop("_source_schema_version", None)
    return {"packet": packet, "config": config, "policy": policy}


def prepare(root, task, config, *, apply=False):
    material = build(root, task, config)
    ledger = TaskLedger(root, material["packet"]["task_id"])
    from review_rework_budget import bind

    bind(ledger, material["config"])
    contract = ledger.path / "contract.json"
    if ledger.path.exists():
        raise StateError("Task identity already prepared; use status/resume")
    approval = {"material": material, "sha256": fingerprint(material)}
    if apply:
        lock = W.RepoWriteLock(Path(root), "prepare-" + material["packet"]["task_id"])
        lock.acquire()
        try:
            save(contract, approval)
            for path in material["packet"]["scope"]["modify"]:
                target = ledger.path / "preimages" / path
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as stream:
                    stream.write((Path(root) / path).read_bytes())
            ledger.record("task_prepared", {"contract_sha256": approval["sha256"]})
        finally:
            lock.release()
    return {
        "status": "prepared" if apply else "preview",
        "contract": str(contract),
        "source_count": len(material["policy"]["initial_hashes"]),
        "material_sha256": approval["sha256"],
    }


def load_contract(root, task_id):
    ledger = TaskLedger(root, task_id)
    value = read(ledger.path / "contract.json")
    if fingerprint(value["material"]) != value["sha256"]:
        raise StateError("Prepared material drift")
    from review_rework_budget import bind

    bind(ledger, value["material"]["config"])
    if value["material"]["config"].get("experimental_native_tools_trial"):
        from native_trial_host import TrialLedger

        ledger.__class__ = TrialLedger
    return ledger, value["material"]
