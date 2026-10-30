"""One-shot capability isolation, NOT Coder/handoff/acceptance evidence.

Proposal generation never edits source. Primary inspects the preserved diff
before the separate hash-checked apply step; protected tests stay read-only.
"""

import argparse
import difflib
import json
import time

import limit_recipe_trial as recipe
from capability_fit import WORK, load_worker, write
from inherited_context_recovery import digest, read
from layer_isolation import verify_hashes

trial = recipe.trial
trial.BASE = WORK / "limit-direct-1"
trial.SNAPSHOT = WORK / "limit-echo-runtime-1"
trial.ARMS = ("semantic-direct-1", "semantic-direct-2", "semantic-direct-3")


def checked_proposal(value):
    if not isinstance(value, dict) or set(value) != {"path", "content"}:
        raise ValueError("proposal requires only path and content")
    if value["path"] != trial.COMMON or not isinstance(value["content"], str):
        raise ValueError("out-of-scope or malformed proposal")
    if not value["content"] or len(value["content"]) > 20_000:
        raise ValueError("empty or oversized proposal")
    return value


def propose(arm):
    root = trial.BASE / arm
    manifest = read(root / ".agent/manifest.json")
    verify_hashes(root, manifest["files"])
    config = read(root / ".agent/config.json")
    worker = load_worker(trial.SNAPSHOT)
    schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "enum": [trial.COMMON]},
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
        action_schema=schema,
        schema_name="isolated_module_proposal",
        context_length=config["coder_context_length"],
    )
    # Same hard contract and advisory example; no oracle/reference implementation.
    paths = [trial.COMMON, "src/evaluation_harness/contracts.py"]
    paths += read(root / ".agent/packet.json")["focused_tests"]
    payload = {
        "packet": read(root / ".agent/packet.json"),
        "project_configuration": (root / "pyproject.toml").read_text(encoding="utf-8"),
        "baseline": read(root / ".agent/baseline.json"),
        "files": {path: (root / path).read_text(encoding="utf-8") for path in paths},
    }
    messages = [
        {
            "role": "system",
            "content": "Implement the provided hard contract. Return JSON path/content with the COMPLETE updated authorized module. Preserve other branches. Tests are protected. No tools or commands. This is a diagnostic proposal, not acceptance.",
        },
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
    write(root / ".agent/direct-input.json", payload)
    started = time.monotonic()
    error = None
    raw = ""
    try:
        with worker.MODEL_RESIDENCY.role_model_lease(client, config):
            raw = client.complete(messages)
        proposal = checked_proposal(json.loads(raw))
        write(root / ".agent/direct-proposal.json", proposal)
        before = (root / trial.COMMON).read_text(encoding="utf-8")
        difference = "".join(
            difflib.unified_diff(
                before.splitlines(keepends=True),
                proposal["content"].splitlines(keepends=True),
                fromfile="a/" + trial.COMMON,
                tofile="b/" + trial.COMMON,
            )
        )
        with (root / ".agent/direct-proposal.diff").open(
            "x", encoding="utf-8"
        ) as stream:
            stream.write(difference)
    except Exception as exc:  # noqa: BLE001 -- preserve isolated diagnostic failure
        error = f"{type(exc).__name__}: {exc}"
    write(
        root / ".agent/direct-facts.json",
        {
            "error": error,
            "seconds": time.monotonic() - started,
            "stats": client.last_request_stats,
            "response_chars": len(raw),
            "source_unchanged": digest(root / trial.COMMON)
            == manifest["files"][trial.COMMON],
            "coder_success_credit": False,
            "primary_assistance": "Frozen packet, protected acceptance tests and executable unrelated recipe",
        },
    )
    print(json.dumps({"error": error, "seconds": time.monotonic() - started}))


def apply_reviewed(arm):
    root = trial.BASE / arm
    manifest = read(root / ".agent/manifest.json")
    verify_hashes(root, manifest["files"])
    proposal_path = root / ".agent/direct-proposal.json"
    approval = read(root / ".agent/direct-primary-review.json")
    if (
        approval.get("proposal_sha256") != digest(proposal_path)
        or approval.get("safe_to_validate") is not True
    ):
        raise ValueError("Primary review required for this exact proposal")
    proposal = checked_proposal(read(proposal_path))
    worker = load_worker(trial.SNAPSHOT)
    editor = worker.SafeEditor(root, allowed_modify=[trial.COMMON], allowed_create=[])
    before = (root / trial.COMMON).read_text(encoding="utf-8")
    result = editor.replace(
        trial.COMMON, before, proposal["content"], manifest["files"][trial.COMMON]
    )
    write(root / ".agent/direct-apply.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "propose", "apply-reviewed"))
    parser.add_argument("--arm", choices=trial.ARMS, required=True)
    args = parser.parse_args()
    if args.action == "prepare":
        trial.prepare(args.arm, clean_start=True)
        if not (trial.BASE / "registration.json").exists():
            write(
                trial.BASE / "registration.json",
                {
                    "arms": list(trial.ARMS),
                    "weekly_ceiling": 23,
                    "purpose": "Isolate one-shot algorithm capability from multi-turn protocol/context burden",
                    "not_matched_latency": "Direct input includes all focused tests rather than sequential reads; no agent/handoff credit",
                    "gate": "Primary actual diff inspection then independent protected closure/static checks",
                },
            )
    elif args.action == "propose":
        propose(args.arm)
    else:
        apply_reviewed(args.arm)
