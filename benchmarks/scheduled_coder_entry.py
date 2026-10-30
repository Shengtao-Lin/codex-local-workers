"""Explicit live receiver for the approved, frozen scheduling candidate."""

import argparse
import json
import sys
from pathlib import Path

import coder_output_channel as OUTPUT
import coder_prevalidation_format as PREPARE


def configure(worker, config):
    enabled = config.get("experimental_prevalidation_format")
    if type(enabled) is not bool:
        raise worker.WorkerError("Scheduling mode must be explicit boolean")
    if config.get("experimental_output_channel") != "schema":
        raise worker.WorkerError("Scheduling trial requires the frozen schema channel")
    original = OUTPUT.make_runtime

    def factory(worker, host, arm):
        base = original(worker, host, arm)
        return PREPARE.make_runtime(worker, base) if enabled else base

    OUTPUT.make_runtime = factory
    try:
        OUTPUT.install(worker, "schema")
    finally:
        OUTPUT.make_runtime = original


def main():
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--preflight-only", action="store_true")
    args, remaining = parser.parse_known_args()
    # Reuse the exact frozen entry: it binds canonical capture inputs and
    # invokes original worker.main with truthful config/client/wire settings.
    original = OUTPUT.install

    def install(worker, arm):
        config_path = Path(remaining[remaining.index("--config") + 1])
        config = json.loads(config_path.read_text(encoding="utf-8"))
        # configure uses OUTPUT.install; temporarily restore to avoid recursion.
        OUTPUT.install = original
        configure(worker, config)
        if args.preflight_only:

            def preflight():
                packet_path = Path(remaining[remaining.index("--packet") + 1])
                packet = worker.resolve_inherited_packet(
                    Path.cwd(), worker.load_json(packet_path.resolve())
                )
                client = worker.LMStudioClient(
                    config["lmstudio_base_url"],
                    config["coder_model"],
                    structured_output=config["coder_structured_output"],
                )
                spec = worker.importlib.util.spec_from_file_location(
                    "local_host_proposal",
                    Path(worker.__file__).with_name("host-proposal.py"),
                )
                adapter = worker.importlib.util.module_from_spec(spec)
                spec.loader.exec_module(adapter)
                runtime = adapter.make_runtime_class(worker)(
                    Path.cwd(), packet, config, client
                )
                try:
                    runtime.preflight()
                    assert runtime.host_request_cap == 6 and runtime.host_check_cap == 3
                    print(
                        json.dumps(
                            {
                                "preflight": "passed",
                                "model_calls": 0,
                                "prepared": config["experimental_prevalidation_format"],
                            }
                        )
                    )
                finally:
                    runtime.close()
                return 0

            worker.main = preflight

    OUTPUT.install = install
    sys.argv = [sys.argv[0], *remaining]
    return OUTPUT.main()


if __name__ == "__main__":
    raise SystemExit(main())
