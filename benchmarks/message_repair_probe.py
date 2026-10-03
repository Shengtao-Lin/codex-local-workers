"""Independent message-repair fixtures; never replace frozen cohort results."""

from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
import sys
import uuid
import xml.etree.ElementTree as ET

import stability_e2e as stability
from localization_route_smoke import runtime_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("variant", choices=("mismatch", "no-exception", "duplicate"))
    args = parser.parse_args()
    base = next(c for c in stability.CASES if c.name == "mapping-message-sequence")
    wrong = (
        "Adapter output messages must be a sequence of messages, not a string or bytes"
    )
    if args.variant == "no-exception":
        injected = (
            "    if isinstance(raw_messages, (str, bytes)):\n"
            '        return InvocationOutput(messages=[Message.model_validate({"role": "assistant", '
            '"content": [{"type": "text", "text": "ready"}]})])\n' + base.after
        )
    else:
        injected = (
            "    if isinstance(raw_messages, (str, bytes)):\n"
            f"        raise TypeError({wrong!r})\n" + base.after
        )
        if args.variant == "duplicate":
            injected = (
                f"    if raw_messages is None:\n        raise TypeError({wrong!r})\n"
                + injected
            )
    case = dataclasses.replace(base, after=injected)
    config = json.loads(
        (stability.KIT / ".local-agents/config.json").read_text(encoding="utf-8-sig")
    )
    config["explorer_mode"] = "locate"
    provenance = runtime_manifest(config)
    root = stability.WORK / f"message-probe-{args.variant}-{uuid.uuid4().hex[:12]}"
    config_path, packet_path = stability.prepare(case, root, config)
    test = "tests/test_mapping_message_sequence.py"
    baseline = stability.run_command(
        root,
        [
            sys.executable,
            "-m",
            "pytest",
            test,
            "-q",
            "--junitxml=.agent/probe-baseline.xml",
        ],
        90,
    )
    if baseline.returncode == 0:
        raise ValueError("injected baseline must fail")
    spec = importlib.util.spec_from_file_location(
        "message_probe_worker", stability.KIT / ".local-agents/worker-runtime.py"
    )
    assert spec and spec.loader
    worker = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = worker
    spec.loader.exec_module(worker)
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    local_config = json.loads(config_path.read_text(encoding="utf-8"))
    runtime = worker.WorkerRuntime(root, packet, local_config, None)
    diagnostic = runtime._diagnostic(baseline.stdout)
    diagnostic["failures"] = runtime._junit_failures(
        ET.parse(root / ".agent/probe-baseline.xml").getroot()
    )
    focus = runtime._failed_test_repair_focus({"diagnostic": diagnostic})
    mismatch = [
        f for f in focus if f.get("diagnosis") == "exception_message_regex_mismatch"
    ]
    safety = (
        bool(mismatch) and all(f.get("line") for f in mismatch)
        if args.variant == "mismatch"
        else not mismatch and any("DID NOT RAISE" in f["message"] for f in focus)
        if args.variant == "no-exception"
        else bool(mismatch) and all("line" not in f for f in mismatch)
    )
    if not safety:
        raise ValueError("diagnostic safety expectation failed")
    packet["implementation_guidance"] = [
        (
            "First VALIDATE the current implementation to observe its actual failure, before editing. "
            "Then use repair_focus for a minimal implementation repair preserving all contract branches. "
            "Do not edit protected tests."
        ),
    ]
    stability.write_json(packet_path, packet)
    result = stability.run_command(
        root,
        [
            sys.executable,
            str(root / ".local-agents/local-unit.py"),
            "--packet",
            str(packet_path),
            "--config",
            str(config_path),
        ],
        1000,
    )
    unit = json.loads(result.stdout.strip()) if result.stdout.strip() else {}
    run = (
        root
        / ".agent/tasks/stability-mapping-message-sequence/runs/mapping-message-sequence-a1"
    )
    events = stability.read_events(run / "events.jsonl")
    converted = any(
        e.get("event") == "validation_finished"
        and e.get("facts", {}).get("status") == "failed"
        and e.get("facts", {}).get("edit_revision") == 0
        for e in events
    )
    checks = {}
    for name, argv in {
        "tests": [sys.executable, "-m", "pytest", test, "-q"],
        "lint": [sys.executable, "-m", "ruff", "check", "src", "tests"],
        "format": [sys.executable, "-m", "ruff", "format", "--check", "src", "tests"],
    }.items():
        checks[name] = stability.run_command(root, argv, 90).returncode == 0
    changed = runtime_manifest(config)["runtime_sha256"] != provenance["runtime_sha256"]
    outcome = {
        "workspace": str(root),
        "variant": args.variant,
        "provenance": provenance,
        "baseline_failed": True,
        "diagnostic_safety_pass": safety,
        "baseline_focus": focus,
        "failed_validation_before_edit": converted,
        "unit_exit": result.returncode,
        "unit": unit,
        "independent_checks": checks,
        "runtime_changed": changed,
    }
    stability.write_json(root / "probe-result.json", outcome)
    print(json.dumps(outcome, ensure_ascii=False))
    return (
        0
        if result.returncode == 0 and converted and all(checks.values()) and not changed
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
