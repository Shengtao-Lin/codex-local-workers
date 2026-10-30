"""Explicit local-only Strata preview entry. No installation/model fallback."""

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "strata"))


def checked_config(config):
    for key in ("strata_node_path", "strata_harness_root", "strata_base_url"):
        if not isinstance(config.get(key), str) or not config[key]:
            raise ValueError("Explicit trusted configuration required: " + key)
    endpoint = urlsplit(config["strata_base_url"])
    if (
        endpoint.scheme != "http"
        or endpoint.hostname != "127.0.0.1"
        or endpoint.path != "/v1"
        or endpoint.username
        or endpoint.password
        or endpoint.query
        or endpoint.fragment
    ):
        raise ValueError("Only explicit http://127.0.0.1:<port>/v1 accepted")
    node, harness = Path(config["strata_node_path"]), Path(config["strata_harness_root"])
    if not node.is_absolute() or not node.is_file() or not harness.is_absolute():
        raise ValueError("Existing absolute Node and harness paths required")
    bundle = json.loads((harness / "BUNDLE.json").read_text(encoding="utf-8"))
    if bundle.get("component") != "deepseek-harness" or bundle.get("version") != "0.2.1-alpha.3":
        raise ValueError("Unqualified Strata harness version; no silent fallback")
    if config.get("experimental_strata_subagent") is not True or config.get("coordinator_enabled"):
        raise ValueError("Explicit subagent opt-in and Coordinator disabled required")
    if config.get("coder_model") != "iq3_s":
        raise ValueError("Only the recorded iq3_s model is qualified in this preview")
    return {
        "node": str(node),
        "harness": str(harness),
        "bundle": bundle,
        "base_url": config["strata_base_url"],
        "model": "iq3_s",
    }


def verify_installation():
    path = ROOT / "strata/installation.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    for name, expected in receipt["files"].items():
        file = ROOT / name
        if not file.resolve().is_relative_to(ROOT) or not file.is_file():
            raise ValueError("Installed runtime file missing or escaped: " + name)
        if hashlib.sha256(file.read_bytes()).hexdigest() != expected:
            raise ValueError("Installed runtime drift: " + name)
    return receipt


def residency(config):
    base = config["strata_base_url"].removesuffix("/v1")

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *_args, **_kwargs):
            raise ValueError("Local provider redirect refused")

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(base + "/api/native", timeout=20) as response:
        native = json.load(response)
    instances = native.get("instances", [])
    if len(instances) != 1:
        raise ValueError("Exactly one resident Strata model required")
    instance = instances[0]
    if (
        instance.get("model") != "iq3_s"
        or instance.get("status") != "ready"
        or instance.get("parallel") != 1
        or instance.get("context", 0) < 65536
    ):
        raise ValueError("Resident model/context/parallelism differs; no reload performed")
    return instance


def main():
    general_commands = {"prepare", "resume", "status", "cancel", "export"}
    if (len(sys.argv) > 1 and sys.argv[1] in general_commands) or "--task-id" in sys.argv:
        from general_cli import main as general_main

        return general_main()
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("mode", choices=["doctor", "run"])
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--packet", type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8-sig"))
    facts = checked_config(config)
    receipt = verify_installation()
    instance = residency(config)
    if args.mode == "doctor":
        print(
            json.dumps(
                {
                    "status": "ready",
                    "runtime_version": receipt["version"],
                    "provider": facts,
                    "resident": instance,
                    "lmstudio_required": False,
                    "acceptance": False,
                },
                indent=2,
            )
        )
        return 0
    if args.packet is None:
        parser.error("run requires --packet")
    # No new task planning, permission inference or implicit budget reset.
    packet = json.loads(args.packet.read_text(encoding="utf-8-sig"))
    run_id = packet.get("run_id")
    if (
        not isinstance(run_id, str)
        or not run_id
        or any(
            c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
            for c in run_id
        )
    ):
        raise ValueError("Safe unique run_id required")
    from strata_artifacts import save
    from strata_native_host_v4 import HOST, NativeV4Client, rules

    program = Path.cwd() / ".agent" / ("strata-program-" + run_id + ".json")
    save(program, {"mode": "live", "instance_id": instance["id"]})
    sys.argv = [
        sys.argv[0],
        "--packet",
        str(args.packet.resolve()),
        "--config",
        str(args.config.resolve()),
        "--program",
        str(program),
    ]
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    return HOST.main(client_type=NativeV4Client, rules_selector=rules)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError) as exc:
        print(
            json.dumps({"status": "blocked", "reason": str(exc), "acceptance": False}),
            file=sys.stderr,
        )
        raise SystemExit(2) from exc
