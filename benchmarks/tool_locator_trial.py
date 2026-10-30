"""Matched lexical locator obligations, independent of semantic Coder success."""

import argparse
import json
import shutil

from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read
from layer_isolation import command, verify_hashes
from tool_awaitable_trial import EXTRA, PYTHON, SOURCE, TARGET, role_overrides

BASE = WORK / "tool-locator-1"
FROZEN = KIT / "benchmarks/fixtures/tool-awaitable-v5"
SNAPSHOT = WORK / "tool-awaitable-runtime-4"
ARMS = ("control-1", "anchors-1", "anchors-2", "control-2")
ANCHORS = [
    {"path": TARGET, "text": "return await asyncio.to_thread(tool.handler, **values)"},
    {
        "path": "src/agent_runtime/adapters/native.py",
        "text": "result=tool_result.output",
    },
    {"path": EXTRA, "text": "time.sleep(0.08)"},
    {"path": EXTRA, "text": "await asyncio.sleep(0.08)"},
    {"path": EXTRA, "text": "timeout_seconds=0.12"},
    {
        "path": EXTRA,
        "text": 'assert events == ["before_tool", "factory", "await", "finalized"]',
    },
]
TASK = "Locate the controlling execute branch in src/agent_runtime/tools/registry.py, the ToolResultContent construction containing result=tool_result.output in src/agent_runtime/adapters/native.py, and the COMPLETE test_factory_and_await_share_one_deadline in tests/unit/test_awaitable.py (include both delays, configured timeout and final assertion). Cite these three bounded ranges, total <=80 lines; do not substitute the outer invoke call for the output consumer. Return only read source_refs; no semantic verdict."


def register():
    write(
        BASE / "registration.json",
        {
            "arms_in_order": list(ARMS),
            "weekly_ceiling": 23,
            "axis": "Only trusted literal anchor obligations on/off; same three required paths, question, source, OSS and budgets",
            "scope": "Location completeness, never semantic verification or feature acceptance",
            "anchors": ANCHORS,
            "runtime": str(SNAPSHOT),
            "coordinator": False,
        },
    )


def prepare(arm):
    if not (BASE / "registration.json").exists():
        raise ValueError("register first")
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    provenance = read(FROZEN / "provenance.json")
    verify_hashes(SOURCE, provenance["original_files"])
    verify_hashes(FROZEN, provenance["files"])
    root = BASE / arm
    root.mkdir(parents=True, exist_ok=False)
    for path in provenance["files"]:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FROZEN / path, target)
    config = read(KIT / ".local-agents/config.json")
    config.update(role_overrides())
    config["explorer_required_citation_paths"] = list(
        dict.fromkeys(anchor["path"] for anchor in ANCHORS)
    )
    if arm.startswith("anchors"):
        config["explorer_required_source_anchors"] = ANCHORS
    write(root / ".agent/config.json", config)


def run(arm):
    root = BASE / arm
    result = command(
        root,
        [
            str(PYTHON),
            "-B",
            str(SNAPSHOT / ".local-agents/local-explore.py"),
            "--config",
            str(root / ".agent/config.json"),
            "--task-id",
            "tool-locator-" + arm,
            "--task",
            TASK,
            "--report",
            str(root / ".agent/explorer.json"),
            "--full-report",
        ],
        timeout=900,
    )
    write(root / ".agent/invocation.json", result)
    report = read(root / ".agent/explorer.json")
    missing = [
        anchor
        for anchor in ANCHORS
        if not any(
            ref["path"] == anchor["path"] and anchor["text"] in ref["quote"]
            for ref in report.get("source_refs", [])
        )
    ]
    provenance = read(FROZEN / "provenance.json")
    verify_hashes(root, provenance["files"])
    facts = {
        "runtime_status": report["status"],
        "missing_lexical_targets": missing,
        "exact_locator_targets_complete": report["status"] == "success" and not missing,
        "protocol_errors": report["budget_usage"]["protocol_errors"],
        "semantic_verification": False,
        "source_unchanged": True,
        "report_sha256": digest(root / ".agent/explorer.json"),
        "seconds": result["seconds"],
        "primary_semantic_adjudication": None,
    }
    write(BASE / (arm + ".json"), facts)
    print(json.dumps({"arm": arm, **facts}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("register", "prepare", "run"))
    parser.add_argument("--arm", choices=ARMS)
    args = parser.parse_args()
    if args.action == "register":
        register()
    else:
        (prepare if args.action == "prepare" else run)(args.arm)
