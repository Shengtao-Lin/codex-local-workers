"""Restore original typed event inputs; no new facts, outputs or expected values."""

import argparse
import copy
import importlib.util
import json
import sys
from pathlib import Path

import reviewer_observation_accounting as BASE
import reviewer_observed_facts as REAL

PROTOCOL = "lossless-typed-observation-input-v1"


def restore(runtime, profiles, error):
    profiles = copy.deepcopy(profiles)
    provenance = []
    for profile in profiles:
        if profile["profile_id"] != "collect-tools-json-observation-v1":
            continue
        seal = REAL.OBS.B.read(REAL.SEAL)
        for path, sha in seal["pins"].items():
            if REAL.OBS.B.sha(Path(path)) != sha:
                raise error("typed observation input artifact changed: " + path)
        source = next(
            (
                s
                for s in seal["sources"]
                if s["source_manifest"]
                == runtime.observation_provenance["source_manifest"]
            ),
            None,
        )
        if source is None:
            raise error("no sealed typed input for current source manifest")
        request = REAL.OBS.B.read(Path(source["request"]))
        observed = REAL.OBS.B.read(Path(source["observation"]))
        REAL.OBS.validate_request(request)
        if len(profile["examples"]) != len(request["cases"]):
            raise error("typed observation case count changed")
        for i, (example, case) in enumerate(
            zip(profile["examples"], request["cases"], strict=True)
        ):
            if (
                json.dumps(example.pop("result_input"), sort_keys=True)
                != json.dumps(case["parts"][1]["result"], sort_keys=True)
                or example["outcome"] != observed["observations"][i]["outcome"]
            ):
                raise error("typed input projection disagrees with sealed observation")
            example["input"] = case
        profile.pop("shared_setup")
        provenance.append(
            {
                "request_sha256": REAL.OBS.B.sha(Path(source["request"])),
                "observation_sha256": REAL.OBS.B.sha(Path(source["observation"])),
                "source": profile["source"],
                "model_semantics_supplied": False,
            }
        )
    runtime._assert_inputs_current()
    return profiles, provenance


def install(module):
    base = BASE.install(module)

    class TypedObservationReviewer(base):
        def bundle(self):
            result = super().bundle()
            result["approved_observations"], self.typed_input_provenance = restore(
                self, result["approved_observations"], module.ReviewError
            )
            return result

        def validate_report(self, args):
            report = super().validate_report(args)
            report["typed_observation_input"] = {
                "protocol": PROTOCOL,
                "provenance": self.typed_input_provenance,
            }
            return report

    module.ReviewerRuntime = TypedObservationReviewer
    return TypedObservationReviewer


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--runtime-dir", required=True)
    args, remaining = parser.parse_known_args()
    path = Path(args.runtime_dir) / "reviewer-runtime.py"
    spec = importlib.util.spec_from_file_location("typed_observation_runtime", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    install(module)
    sys.argv = [str(path), *remaining]
    raise SystemExit(module.main())
