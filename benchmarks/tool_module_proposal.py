"""Non-executing whole-module capability diagnostic; not an agent success."""

import argparse
import difflib
import json
import time

import tool_awaitable_trial as trial
from capability_fit import WORK, load_worker, write
from inherited_context_recovery import digest, read
from layer_isolation import verify_hashes

BASE = WORK / "tool-module-proposal-1"
SNAPSHOT = WORK / "tool-reviewer-runtime-5"
ARMS = ("proposal-1", "proposal-2")
BASELINE_COMPACTOR = None
PAYLOAD_TRANSFORM = None


def configure():
    trial.BASE, trial.SNAPSHOT, trial.ARMS = BASE, SNAPSHOT, ARMS


def register():
    write(
        BASE / "registration.json",
        {
            "arms": list(ARMS),
            "weekly_ceiling": 23,
            "purpose": "Separate async semantic capability from multi-turn action selection and patch matching",
            "model": "Same Qwen/sampling/context/max output; one structured complete-module proposal each",
            "input": "Frozen hard contract, actual source and all protected focused tests; no oracle or exact solution",
            "comparison": "Diagnostic only; source/tests supplied together unlike sequential agent reads, not matched latency",
            "safety": "No source execution during proposal; actual Primary diff inspection and exact proposal hash authorization before isolated application",
            "credit": "No Coder agent, Explorer, Reviewer, automatic handoff, stable-release or savings credit",
        },
    )


def checked_proposal(value):
    if not isinstance(value, dict) or set(value) != {"path", "content"}:
        raise ValueError("proposal requires only path/content")
    if value["path"] != trial.TARGET or not isinstance(value["content"], str):
        raise ValueError("proposal path/content invalid")
    if not value["content"] or len(value["content"]) > 20000:
        raise ValueError("empty or oversized proposal")
    return value


def propose(arm):
    if arm not in ARMS or not (BASE / "registration.json").exists():
        raise ValueError("registered diagnostic arm required")
    root = BASE / arm
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    manifest = read(root / ".agent/manifest.json")
    verify_hashes(root, manifest["files"])
    config = read(root / ".agent/config.json")
    worker = load_worker(SNAPSHOT)
    packet = read(root / ".agent/packet.json")
    schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "enum": [trial.TARGET]},
            "content": {"type": "string"},
        },
        "required": ["path", "content"],
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
        context_length=config["coder_context_length"],
        action_schema=schema,
        schema_name="isolated_tool_module_proposal",
    )
    paths = [
        trial.TARGET,
        "src/agent_runtime/tools/models.py",
        "src/agent_runtime/errors.py",
        "src/agent_runtime/models.py",
        *packet["focused_tests"],
    ]
    payload = {
        "packet": packet,
        "baseline": read(root / ".agent/baseline.json"),
        "project_configuration": (root / "pyproject.toml").read_text(encoding="utf-8"),
        "files": {path: (root / path).read_text(encoding="utf-8") for path in paths},
    }
    if BASELINE_COMPACTOR is not None:
        payload["baseline"] = BASELINE_COMPACTOR(payload["baseline"], root)
    if PAYLOAD_TRANSFORM is not None:
        payload = PAYLOAD_TRANSFORM(payload)
    write(root / ".agent/proposal-input.json", payload)
    started = time.monotonic()
    error, raw = None, ""
    try:
        with worker.MODEL_RESIDENCY.role_model_lease(client, config):
            raw = client.complete(
                [
                    {
                        "role": "system",
                        "content": "Implement the complete hard contract. Return JSON path/content with the COMPLETE authorized module. Preserve unrelated behavior. Protected tests cannot change. No tools, commands or acceptance claims. This is a non-executing diagnostic proposal.",
                    },
                    {
                        "role": "user",
                        "content": json.dumps(payload, ensure_ascii=False),
                    },
                ]
            )
        proposal = checked_proposal(json.loads(raw))
        write(root / ".agent/proposal.json", proposal)
        difference = "".join(
            difflib.unified_diff(
                (root / trial.TARGET).read_text(encoding="utf-8").splitlines(True),
                proposal["content"].splitlines(True),
                fromfile="a/" + trial.TARGET,
                tofile="b/" + trial.TARGET,
            )
        )
        with (root / ".agent/proposal.diff").open("x", encoding="utf-8") as stream:
            stream.write(difference)
    except Exception as exc:  # noqa: BLE001 -- preserve diagnostic failures
        error = f"{type(exc).__name__}: {exc}"
    facts = {
        "error": error,
        "seconds": time.monotonic() - started,
        "stats": dict(client.last_request_stats),
        "response_chars": len(raw),
        "source_unchanged": digest(root / trial.TARGET)
        == manifest["files"][trial.TARGET],
        "actions_executed": False,
        "coder_success_credit": False,
    }
    write(root / ".agent/proposal-facts.json", facts)
    print(json.dumps({"arm": arm, **facts}))


def apply_reviewed(arm):
    if arm not in ARMS:
        raise ValueError("registered diagnostic arm required")
    root = BASE / arm
    manifest = read(root / ".agent/manifest.json")
    verify_hashes(root, manifest["files"])
    proposal_path = root / ".agent/proposal.json"
    approval = read(root / ".agent/primary-proposal-review.json")
    if (
        approval.get("proposal_sha256") != digest(proposal_path)
        or approval.get("safe_to_validate") is not True
    ):
        raise ValueError("Primary review required for this exact proposal")
    proposal = checked_proposal(read(proposal_path))
    worker = load_worker(SNAPSHOT)
    editor = worker.SafeEditor(root, allowed_modify=[trial.TARGET], allowed_create=[])
    result = editor.replace(
        trial.TARGET,
        (root / trial.TARGET).read_text(encoding="utf-8"),
        proposal["content"],
        manifest["files"][trial.TARGET],
    )
    write(root / ".agent/proposal-apply.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "action", choices=("register", "prepare", "propose", "apply-reviewed", "verify")
    )
    parser.add_argument("--arm", choices=ARMS)
    args = parser.parse_args()
    configure()
    if args.action == "register":
        register()
    else:
        {
            "prepare": trial.prepare,
            "propose": propose,
            "apply-reviewed": apply_reviewed,
            "verify": trial.verify,
        }[args.action](args.arm)
