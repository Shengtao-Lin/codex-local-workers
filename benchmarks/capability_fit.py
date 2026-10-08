"""Isolated, versioned capability-fit experiments; never accepts a feature."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import mixed_feature_benchmark as MIXED
from capability_transfer_cases import (
    ACTION_EXAMPLES,
    EXAMPLES,
    TRANSACTION_GUIDANCE,
    transfer_cases,
)
from complex_fixture_cases import extend

KIT = Path(__file__).resolve().parents[1]
WORK = KIT / "benchmarks/work/capability-fit"


def cases():
    corpus = extend(
        json.loads(
            (KIT / "benchmarks/fixtures/mixed-features-v1.json").read_text(
                encoding="utf-8"
            )
        )
    )
    transfer, _ = transfer_cases(corpus["cases"][0])
    corpus["cases"].extend(transfer)
    return {case["case_id"]: case for case in corpus["cases"]}


def load_worker(snapshot):
    spec = importlib.util.spec_from_file_location(
        "capability_worker", snapshot / ".local-agents/worker-runtime.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_case(
    case_id,
    arm,
    repetition,
    snapshot_label,
    trial="run",
    retention="recent",
    packet_style=None,
    repair_focus="all",
    validation_id_skeleton=False,
    inline_repair_analysis=False,
    failed_test_diagnostics=False,
):
    snapshot = WORK / snapshot_label
    manifest = json.loads((snapshot / "freeze.json").read_text(encoding="utf-8"))
    for relative, digest in manifest["files"].items():
        if hashlib.sha256((snapshot / relative).read_bytes()).hexdigest() != digest:
            raise ValueError("snapshot drift: " + relative)
    if arm not in {"direct", "current", "candidate", "fewshot", "fewshot-actions"}:
        raise ValueError("invalid arm")
    if retention not in {"recent", "budgeted"}:
        raise ValueError("invalid context retention")
    if repair_focus not in {"all", "latest"}:
        raise ValueError("invalid repair focus retention")
    if packet_style is not None and (
        packet_style not in TRANSACTION_GUIDANCE
        or case_id != "transfer-transaction-save"
        or arm != "candidate"
    ):
        raise ValueError("packet style requires candidate transaction cohort")
    if arm == "direct" and repair_focus != "all":
        raise ValueError("repair focus applies only to tool-loop arms")
    if arm == "direct" and retention != "recent":
        raise ValueError("context retention applies only to tool-loop arms")
    if arm in {"fewshot", "fewshot-actions"} and not case_id.startswith("transfer-"):
        raise ValueError("few-shot transfer cohort only")
    if not trial or any(
        c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in trial
    ):
        raise ValueError("invalid trial identity")
    if validation_id_skeleton:
        if arm != "candidate":
            raise ValueError("validation ID skeleton requires candidate arm")
        source = snapshot / ".local-agents/worker-runtime.py"
        if not source.is_file() or "VALIDATION_ID_SKELETON" not in source.read_text(
            encoding="utf-8"
        ):
            raise ValueError("snapshot does not implement validation ID skeleton")
    if inline_repair_analysis:
        if arm != "candidate" or validation_id_skeleton:
            raise ValueError(
                "inline repair analysis requires candidate with no skeleton"
            )
        source = snapshot / ".local-agents/worker-runtime.py"
        if not source.is_file() or "INLINE_REPAIR_ANALYSIS" not in source.read_text(
            encoding="utf-8"
        ):
            raise ValueError("snapshot does not implement inline repair analysis")
    if case_id.startswith("diag-"):
        if arm not in {"current", "candidate"} or failed_test_diagnostics != (
            arm == "candidate"
        ):
            raise ValueError("diagnostic cohort requires current/off or candidate/on")
    elif failed_test_diagnostics:
        raise ValueError("failed-test diagnostics requires diagnostic cohort")
    if failed_test_diagnostics:
        source = snapshot / ".local-agents/worker-runtime.py"
        if not source.is_file() or "run_on_test_failure" not in source.read_text(
            encoding="utf-8"
        ):
            raise ValueError("snapshot does not implement failed-test diagnostics")
    case = cases()[case_id]
    label = f"{snapshot_label}-{case_id}-{arm}-r{repetition}-{trial}"
    run_id = f"mixed-complex-v2-{label}-{case_id}-r{repetition}-{case['units'][0]['unit_id']}-a1"
    if len(run_id) > 128:
        raise ValueError(
            "diagnostic run identity exceeds runtime limit; shorten snapshot/trial label"
        )
    # Reuse the trusted schema-v2 materializer but keep this diagnostic workspace
    # separate from the Coordinator cohorts. No Coordinator/Explorer credit.
    MIXED.WORK = WORK / "runs"
    corpus_path = WORK / f"corpus-{label}.json"
    corpus = json.loads(
        (KIT / "benchmarks/fixtures/mixed-features-v1.json").read_text(encoding="utf-8")
    )
    transfer, _ = transfer_cases(corpus["cases"][0])
    corpus["cases"].extend(transfer)
    # The common materializer verifies clean protected inputs first. Introduce
    # the intentional source-only defect afterwards, before hashing/model calls.
    if case_id.startswith("diag-"):
        materialized = next(c for c in corpus["cases"] if c["case_id"] == case_id)
        materialized["files"]["src/product/target.py"] = materialized["files"][
            "src/product/target.py"
        ].removeprefix("import math\n\n")
    write(corpus_path, corpus)
    MIXED.CORPUS = corpus_path
    prepared = MIXED.prepare(
        case_id, repetition, KIT / ".local-agents/config.json", label, "complex-v2"
    )
    root = Path(prepared["root"])
    if case_id.startswith("diag-"):
        source_path = root / "src/product/target.py"
        source_path.write_text(
            "import math\n\n" + source_path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    unit = case["units"][0]
    packet_path = root / f".agent/{unit['unit_id']}-reference.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    examples = (
        ACTION_EXAMPLES
        if arm == "fewshot-actions"
        else EXAMPLES
        if arm == "fewshot"
        else ""
    )
    if packet_style is not None:
        examples = TRANSACTION_GUIDANCE[packet_style]
    if examples:
        packet["implementation_guidance"] = [examples]
        packet_path = root / ".agent/fewshot-packet.json"
        write(packet_path, packet)
    config_path = root / ".agent/config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if case_id.startswith("diag-"):
        commands = config["validation_profiles"][packet["validation_profile"]][
            "commands"
        ]
        if not commands:
            raise ValueError("diagnostic cohort requires trusted static commands")
        for command in commands:
            command["run_on_test_failure"] = failed_test_diagnostics
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    if (
        retention != "recent"
        or repair_focus != "all"
        or validation_id_skeleton
        or inline_repair_analysis
    ):
        config["coder_context_retention"] = retention
        config["coder_repair_focus_retention"] = repair_focus
        config["coder_validation_id_skeleton"] = validation_id_skeleton
        config["coder_inline_repair_analysis"] = inline_repair_analysis
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    initial_hashes = {
        p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in case["files"]
    }
    worker = load_worker(snapshot)
    write(
        root / "experiment.json",
        {
            "case": case_id,
            "arm": arm,
            "context_retention": retention,
            "packet_style": packet_style,
            "repair_focus_retention": repair_focus,
            "validation_id_skeleton": validation_id_skeleton,
            "inline_repair_analysis": inline_repair_analysis,
            "failed_test_diagnostics": failed_test_diagnostics,
            "snapshot": snapshot_label,
            "runtime_sha256": manifest["files"][".local-agents/worker-runtime.py"],
            "runtime_manifest_sha256": hashlib.sha256(
                (snapshot / "freeze.json").read_bytes()
            ).hexdigest(),
            "fixture_driver_sha256": hashlib.sha256(
                Path(MIXED.__file__).read_bytes()
            ).hexdigest(),
            "transfer_definition_sha256": hashlib.sha256(
                (KIT / "benchmarks/capability_transfer_cases.py").read_bytes()
            ).hexdigest(),
            "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
            "project_configuration_sha256": hashlib.sha256(
                (root / "pyproject.toml").read_bytes()
            ).hexdigest(),
            "repetition": repetition,
            "trial": trial,
            "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "initial_hashes": initial_hashes,
            "examples_sha256": hashlib.sha256(examples.encode()).hexdigest()
            if examples
            else None,
            "examples_estimated_tokens": (len(examples) + 3) // 4 if examples else 0,
            "coordinator_invoked": False,
            "explorer_invoked": False,
            "primary_accepted": False,
            "information": "same packet and scoped source/tests; direct receives all scoped text up front, tool loop obtains it through reads",
            "case_sha256": hashlib.sha256(
                json.dumps(case, sort_keys=True).encode()
            ).hexdigest(),
        },
    )
    started = time.monotonic()
    raw = ""
    if arm == "direct":
        schema = {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["path", "content"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["files"],
            "additionalProperties": False,
        }
        client = worker.LMStudioClient(
            config["lmstudio_base_url"],
            config["coder_model"],
            config.get("model_request_timeout_seconds", 180),
            max_tokens=config["coder_max_tokens"],
            temperature=config["coder_temperature"],
            top_p=config["coder_top_p"],
            top_k=config["coder_top_k"],
            min_p=config["coder_min_p"],
            repeat_penalty=config["coder_repeat_penalty"],
            action_schema=schema,
            schema_name="bounded_direct_patch",
            context_length=config["coder_context_length"],
        )
        messages = [
            {
                "role": "system",
                "content": "Implement the hard contract. Return only JSON files with complete new contents for the authorized writable paths. Tests are protected. No commands or extra paths. Preserve all independent contract branches.",
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "packet": packet,
                        "project_configuration": (root / "pyproject.toml").read_text(
                            encoding="utf-8"
                        ),
                        "files": {
                            p: (root / p).read_text(encoding="utf-8")
                            for p in case["files"]
                        },
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        direct_error = None
        try:
            with worker.MODEL_RESIDENCY.role_model_lease(client, config):
                raw = client.complete(messages)
            result = json.loads(raw)
            if (
                not isinstance(result, dict)
                or set(result) != {"files"}
                or not isinstance(result["files"], list)
            ):
                raise ValueError("invalid direct patch object")
            seen = set()
            for item in result["files"]:
                if (
                    not isinstance(item, dict)
                    or set(item) != {"path", "content"}
                    or not isinstance(item["path"], str)
                    or item["path"] not in packet["scope"]["modify"]
                    or item["path"] in seen
                    or not isinstance(item["content"], str)
                ):
                    raise ValueError("invalid or out-of-scope direct patch")
                seen.add(item["path"])
            for path, digest in initial_hashes.items():
                if hashlib.sha256((root / path).read_bytes()).hexdigest() != digest:
                    raise ValueError("direct patch baseline drift: " + path)
            for item in result["files"]:
                (root / item["path"]).write_text(item["content"], encoding="utf-8")
        except Exception as error:  # noqa: BLE001 -- archive isolated diagnostic failures, never accept them
            direct_error = f"{type(error).__name__}: {error}"
        write(
            root / ".agent/direct-diagnostic.json",
            {
                "error": direct_error,
                "response_sha256": hashlib.sha256(raw.encode()).hexdigest(),
                "request_stats": client.last_request_stats,
                "coder_invoked": False,
            },
        )
        return_code = 0 if direct_error is None else 2
        coder = {}
        reviewer = {}
    else:
        invocation = subprocess.run(
            [
                sys.executable,
                "-B",
                str(snapshot / ".local-agents/local-unit.py"),
                "--packet",
                str(packet_path),
                "--config",
                str(config_path),
                "--coder-report",
                str(root / ".agent/coder.json"),
                "--review-report",
                str(root / ".agent/reviewer.json"),
            ],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=1200,
        )
        return_code = invocation.returncode
        raw = invocation.stdout + invocation.stderr
        coder = (
            json.loads((root / ".agent/coder.json").read_text(encoding="utf-8"))
            if (root / ".agent/coder.json").exists()
            else {}
        )
        reviewer = (
            json.loads((root / ".agent/reviewer.json").read_text(encoding="utf-8"))
            if (root / ".agent/reviewer.json").exists()
            else {}
        )
    validations = []
    for command in (
        [
            sys.executable,
            "-B",
            "-m",
            "pytest",
            *packet["focused_tests"],
            "-q",
            "-p",
            "no:cacheprovider",
            f"--junitxml={root / '.agent/primary-validation.xml'}",
        ],
        [sys.executable, "-m", "ruff", "format", "--check", "src", "tests"],
        [sys.executable, "-m", "ruff", "check", "src", "tests"],
    ):
        process = subprocess.run(
            command, cwd=root, capture_output=True, text=True, check=False, timeout=180
        )
        validations.append(
            {
                "argv": command,
                "exit": process.returncode,
                "output": process.stdout + process.stderr,
            }
        )
    junit_path = root / ".agent/primary-validation.xml"
    junit_cases = (
        list(ET.parse(junit_path).getroot().iter("testcase"))
        if junit_path.exists()
        else []
    )
    executed = sum(not list(item.iter("skipped")) for item in junit_cases)
    protected_unchanged = all(
        hashlib.sha256((root / path).read_bytes()).hexdigest() == digest
        for path, digest in initial_hashes.items()
        if path not in packet["scope"]["modify"]
    )
    summary = {
        "case": case_id,
        "arm": arm,
        "repetition": repetition,
        "snapshot": snapshot_label,
        "workspace": str(root),
        "worker_exit": return_code,
        "coder_status": coder.get("status"),
        "reviewer_decision": reviewer.get("decision"),
        "implementation_passed": return_code == 0
        and all(check["exit"] == 0 for check in validations)
        and executed > 0
        and protected_unchanged,
        "focused_tests_passed": validations[0]["exit"] == 0 and executed > 0,
        "focused_tests_executed": executed,
        "static_checks_passed": all(check["exit"] == 0 for check in validations[1:]),
        "protected_inputs_unchanged": protected_unchanged,
        "primary_accepted": False,
        "feature_complete": False,
        "seconds": round(time.monotonic() - started, 2),
        "validations": validations,
        "worker_output_tail": raw[-1800:],
        "cloud_tokens": None,
    }
    write(root / "result.json", summary)
    return summary


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)


def freeze(label):
    if not label or any(
        c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in label
    ):
        raise ValueError("invalid snapshot label")
    root = WORK / label
    root.mkdir(parents=True, exist_ok=False)
    hashes = {}
    paths = [
        p
        for p in (KIT / ".local-agents").rglob("*")
        if p.is_file()
        and "__pycache__" not in p.parts
        and p.suffix in {".py", ".ps1", ".toml", ".json"}
    ]
    paths += [
        KIT / "AGENTS.md",
        KIT / "benchmarks/fixtures/mixed-features-v1.json",
        KIT / "benchmarks/complex_fixture_cases.py",
        KIT / "benchmarks/mixed_feature_benchmark.py",
        KIT / "benchmarks/complex_reviewer_challenge.py",
        KIT / "benchmarks/capability_transfer_cases.py",
        Path(__file__),
        KIT / "benchmarks/v13_diagnostic_compat.py",
        KIT / "benchmarks/v13_scoped_audit.py",
        KIT / "benchmarks/v13_diagnostic_checks.py",
        KIT / "tests/test_v13_scoped_audit.py",
        KIT / "docs/stability-plan-v1.3.md",
    ]
    for path in paths:
        relative = path.relative_to(KIT).as_posix()
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        hashes[relative] = hashlib.sha256(target.read_bytes()).hexdigest()
    metadata = {}
    for endpoint in ("/v1/models", "/api/v1/models"):
        try:
            with urllib.request.urlopen(
                "http://127.0.0.1:12345" + endpoint, timeout=15
            ) as response:
                metadata[endpoint] = json.load(response)
        except (OSError, ValueError) as error:
            metadata[endpoint] = {"unavailable": str(error)}
    status = subprocess.run(
        ["git", "status", "--short"],
        cwd=KIT,
        capture_output=True,
        text=True,
        check=True,
    )
    write(
        root / "freeze.json",
        {
            "label": label,
            "files": hashes,
            "git_status": status.stdout,
            "python": sys.executable,
            "python_version": sys.version,
            "models": metadata,
            "primary_accepted": False,
            "cloud_tokens": None,
        },
    )
    return str(root)


def summarize(label, weekly_used):
    if not label or any(
        c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in label
    ):
        raise ValueError("invalid summary label")
    trials = []
    for path in sorted((WORK / "runs").rglob("experiment.json")):
        result_path = path.parent / "result.json"
        experiment = json.loads(path.read_text(encoding="utf-8"))
        if not result_path.exists():
            known_pre_model_failure = (
                experiment.get("case") == "bounded-report"
                and experiment.get("arm") == "direct"
                and "trial" not in experiment
            )
            trials.append(
                {
                    "workspace": str(path.parent),
                    "experiment": experiment,
                    "infrastructure_failure_before_model": known_pre_model_failure,
                    "unfinished": not known_pre_model_failure,
                    "reason": "Initial Windows GBK decode failure; no model call; retained original workspace."
                    if known_pre_model_failure
                    else "No final result; classification unknown; do not count as worker-quality failure.",
                }
            )
            continue
        result = json.loads(result_path.read_text(encoding="utf-8"))
        result["experiment"] = experiment
        coder_path = path.parent / ".agent/coder.json"
        if coder_path.exists():
            coder_report = json.loads(coder_path.read_text(encoding="utf-8"))
            events = list((path.parent / ".agent/tasks").glob("*/runs/*/events.jsonl"))
            if (
                not coder_report.get("identity", {}).get("run_id")
                and coder_report.get("failure_reason")
                and not events
            ):
                result["infrastructure_failure_before_model"] = True
                result["infrastructure_reason"] = coder_report["failure_reason"]
        result["legacy_fixture_config_confounded"] = any(
            token in str(path) for token in ("utf8-1", "paired-1")
        )
        reviews = []
        for review_path in (path.parent / ".agent/tasks").glob("*/runs/*/review.json"):
            reviews.append(json.loads(review_path.read_text(encoding="utf-8")))
        result["primary_decisions"] = reviews
        trials.append(result)
    controls = []
    for path in sorted(
        (KIT / "benchmarks/work/mixed-v1/reviewer-controls").glob(
            "review-*/challenge-result.json"
        )
    ):
        item = json.loads(path.read_text(encoding="utf-8"))
        item.setdefault("structural_outcome", item.get("expected_outcome"))
        item.setdefault("effective_detection", None)
        item.setdefault(
            "requires_primary_adjudication", item.get("variant") == "hidden"
        )
        if item.get("family"):
            item["freeze"] = json.loads(
                (path.parent / "freeze.json").read_text(encoding="utf-8")
            )
            controls.append(item)
    context = {}
    for path in (WORK / "runs").rglob("events.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            facts = event.get("facts", {})
            stats = (
                facts
                if event.get("event") == "model_request"
                else facts.get("model_request", {})
            )
            if not stats.get("model"):
                continue
            model = stats["model"]
            entry = context.setdefault(
                model,
                {
                    "observed_requests": 0,
                    "maximum_reported_context_utilization": None,
                    "reported_local_tokens": 0,
                },
            )
            entry["observed_requests"] += 1
            utilization = stats.get("reported_context_utilization")
            if utilization is not None:
                entry["maximum_reported_context_utilization"] = max(
                    entry["maximum_reported_context_utilization"] or 0, utilization
                )
            entry["reported_local_tokens"] += stats.get("response_usage", {}).get(
                "total_tokens", 0
            )
    result = {
        "weekly_used_last_observed": weekly_used,
        "cloud_tokens": None,
        "trials": trials,
        "reviewer_controls": controls,
        "local_request_statistics": context,
        "local_request_statistics_scope": "Tool-loop cohort events only; includes confounded early runs, excludes direct solver and independent reviewer controls; never cloud token accounting.",
        "explorer_invocations_this_cohort": 0,
        "coordinator_invocations_this_cohort": 0,
        "mixed_features_accepted": 0,
        "v2_1_released": False,
        "excluded_regressions": [
            "test_static_fixture_baseline_is_lint_only",
            "test_sample_identity_protected_metadata_boundary",
        ],
    }
    target = WORK / f"summary-{label}.json"
    write(target, result)
    return str(target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze")
    parser.add_argument("--summarize")
    parser.add_argument("--weekly-used", type=float)
    parser.add_argument("--case", choices=tuple(cases()))
    parser.add_argument(
        "--arm",
        choices=("direct", "current", "candidate", "fewshot", "fewshot-actions"),
    )
    parser.add_argument("--snapshot")
    parser.add_argument("--retention", choices=("recent", "budgeted"), default="recent")
    parser.add_argument("--packet-style", choices=("prose", "matrix"))
    parser.add_argument("--repair-focus", choices=("all", "latest"), default="all")
    parser.add_argument("--repetition", type=int, choices=(1, 2), default=1)
    parser.add_argument("--trial", default="run")
    parser.add_argument("--validation-id-skeleton", action="store_true")
    parser.add_argument("--inline-repair-analysis", action="store_true")
    parser.add_argument("--failed-test-diagnostics", action="store_true")
    args = parser.parse_args()
    if args.summarize:
        print(summarize(args.summarize, args.weekly_used))
    elif args.freeze:
        print(freeze(args.freeze))
    elif args.case and args.arm and args.snapshot:
        result = run_case(
            args.case,
            args.arm,
            args.repetition,
            args.snapshot,
            args.trial,
            args.retention,
            args.packet_style,
            args.repair_focus,
            args.validation_id_skeleton,
            args.inline_repair_analysis,
            args.failed_test_diagnostics,
        )
        print(
            json.dumps(
                {
                    key: value
                    for key, value in result.items()
                    if key not in {"validations", "worker_output_tail"}
                },
                indent=2,
            )
        )
    else:
        parser.error("use --freeze or --case --arm --snapshot")
