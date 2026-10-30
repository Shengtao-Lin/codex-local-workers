"""Supply sealed observations for exact source versions; no model execution tool."""

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import reviewer_observation_probe as OBS
import reviewer_semantic_policy as BASE

PROTOCOL = "reviewer-sealed-observations-v1"
SEAL = OBS.BATCH / "observation-seal-v2.json"


def facts(runtime, error):
    binding = runtime.config.get("coder_single_function", {})
    if binding.get("path") != OBS.TARGET or binding.get("symbol") != "collect_tools":
        return [], None
    seal = OBS.B.read(SEAL)
    for path, digest in seal["pins"].items():
        if OBS.B.sha(Path(path)) != digest:
            raise error("approved observation artifact changed: " + path)
    runtime._assert_inputs_current()
    for source in seal["sources"]:
        current = {}
        for path in source["source_manifest"]:
            relative, resolved = runtime._assert_read_allowed(path)
            current[relative] = OBS.B.sha(resolved)
        if current != source["source_manifest"]:
            continue
        result = OBS.B.read(Path(source["observation"]))
        request = OBS.B.read(Path(source["request"]))
        OBS.validate_request(request)
        if not result["execution_completed"] or result["semantic_verdict"] is not None:
            raise error("observation is incomplete or contains a semantic verdict")
        if result["source"]["sha256"] != current[OBS.TARGET]:
            raise error("observation source binding disagrees")
        if len(request["cases"]) != len(result["observations"]):
            raise error("observation case count changed")
        examples = [
            {
                "input": case,
                "outcome": observation["outcome"],
                "input_unchanged": observation["input_before"]
                == observation["input_after"],
            }
            for case, observation in zip(
                request["cases"], result["observations"], strict=True
            )
        ]
        manifest_digest = hashlib.sha256(
            json.dumps(current, sort_keys=True).encode()
        ).hexdigest()
        provenance = {
            "cached": True,
            "source_manifest_sha256": manifest_digest,
            "observation_sha256": OBS.B.sha(Path(source["observation"])),
            "profile_id": result["profile_id"],
            "source": result["source"],
            "count": len(examples),
            "projection": result["projection"],
            "runtime_scope": seal["runtime_scope"],
        }
        runtime._assert_inputs_current()
        return [
            {
                "profile_id": result["profile_id"],
                "source": result["source"],
                "projection": result["projection"],
                "examples": examples,
                "meaning": "Actual cached outcomes of this exact source/module version in the fixed evaluation environment. These are observations, not expected outcomes or a contract verdict.",
            }
        ], provenance
    raise error("no approved observations for the current source/module version")


def install(module):
    base = BASE.install(module)

    class ObservationReviewer(base):
        def bundle(self):
            result = super().bundle()
            observations, self.observation_provenance = facts(self, module.ReviewError)
            result["approved_observations"] = observations
            return result

        def validate_report(self, args):
            report = super().validate_report(args)
            report["approved_observation_protocol"] = PROTOCOL
            report["approved_observation_provenance"] = self.observation_provenance
            return report

    module.ReviewerRuntime = ObservationReviewer
    return ObservationReviewer


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--runtime-dir", required=True)
    args, remaining = parser.parse_known_args()
    path = Path(args.runtime_dir) / "reviewer-runtime.py"
    spec = importlib.util.spec_from_file_location("observed_facts_runtime", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    install(module)
    sys.argv = [str(path), *remaining]
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
