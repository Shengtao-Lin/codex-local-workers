"""Explicit experiment receiver; preflight never enters a model lease."""

import argparse
import json
import sys
from pathlib import Path

import bounded_evidence_candidate as C
import capture_fixture_support as F


def install(worker, config, policy_sha):
    C.install_binding(worker, F.POLICY_PATH, policy_sha)
    host = F.load(Path(worker.__file__).with_name("host-proposal.py"), "bounded_host")
    cls = C.make_runtime(worker, host)
    original_client = worker.LMStudioClient
    whole_schema = C.UNIFIED.SPAN.D.INTERFACE.WHOLE_SCHEMA

    def client(*args, **kwargs):
        kwargs.update(action_schema=whole_schema, schema_name="bounded_evidence_v1")
        return original_client(*args, **kwargs)

    worker.LMStudioClient = client
    original_spec = worker.importlib.util.spec_from_file_location

    def spec(name, path, *args, **kwargs):
        result = original_spec(name, path, *args, **kwargs)
        if name == "local_host_proposal":
            worker.importlib.util.spec_from_file_location = original_spec
            loader = result.loader

            class Loader:
                def create_module(self, spec):
                    return loader.create_module(spec)

                def exec_module(self, module):
                    module.make_runtime_class = lambda _worker: cls

            result.loader = Loader()
        return result

    worker.importlib.util.spec_from_file_location = spec
    return cls


def main():
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--runtime-dir", type=Path, required=True)
    parser.add_argument("--capture-policy-sha256", required=True)
    parser.add_argument("--capture-policy", default=F.POLICY_PATH)
    parser.add_argument("--preflight-only", action="store_true")
    args, rest = parser.parse_known_args()
    if args.capture_policy != F.POLICY_PATH:
        raise ValueError("Unregistered policy path")
    config = json.loads(
        Path(rest[rest.index("--config") + 1]).read_text(encoding="utf-8")
    )
    worker = F.load(args.runtime_dir / "worker-runtime.py", "bounded_worker")
    cls = install(worker, config, args.capture_policy_sha256)
    if args.preflight_only:
        packet = worker.resolve_inherited_packet(
            Path.cwd(),
            worker.load_json(Path(rest[rest.index("--packet") + 1]).resolve()),
        )
        client = worker.LMStudioClient(
            config["lmstudio_base_url"], config["coder_model"], structured_output=True
        )
        runtime = cls(Path.cwd(), packet, config, client)
        try:
            runtime.preflight()
            print(
                json.dumps(
                    {
                        "preflight": "passed",
                        "arm": runtime.arm,
                        "budget": C.BUDGET,
                        "model_calls": 0,
                    }
                )
            )
        finally:
            runtime.close()
        return 0
    sys.argv = [worker.__file__, *rest]
    return worker.main()


if __name__ == "__main__":
    raise SystemExit(main())
