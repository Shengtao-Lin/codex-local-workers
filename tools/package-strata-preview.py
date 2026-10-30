"""Package exact tested installed bytes, not the dirty repository or history."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
BASE = KIT / "benchmarks/work/harness-convergence"
BATCH = BASE / "strata-release-v4-20261023-2"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def package(destination):
    decision = read(BATCH / "decision.json")
    if decision["accepted"] != 6 or decision["executed"] != 6:
        raise ValueError("Fixed6/6 independent acceptance required; no partial release")
    if (
        read(BASE / "strata-release-faults-20261023-2/decision.json")["status"]
        != "PASS_OFFLINE_FAULTS"
    ):
        raise ValueError("Fault controls required")
    if (
        read(BASE / "strata-doc-example-20261023-3/decision.json")["status"]
        != "PASS_DOCUMENTED_CONFIG_OFFLINE"
    ):
        raise ValueError("Documented configuration control required")
    seed = BATCH / "cells/raw-1/isolated/.local-agents"
    receipt = read(seed / "strata/installation.json")
    material = {}
    for name, expected in receipt["files"].items():
        path = seed / name
        if (
            not path.resolve().is_relative_to(seed)
            or hashlib.sha256(path.read_bytes()).hexdigest() != expected
        ):
            raise ValueError("Frozen runtime drift: " + name)
        material["runtime/.local-agents/" + name] = path.read_bytes()
    material["runtime/.local-agents/strata/installation.json"] = (
        seed / "strata/installation.json"
    ).read_bytes()
    for name, source in {
        "install.py": KIT / "tools/install-strata-release.py",
        "docs/strata-preview.md": KIT / "docs/strata-preview.md",
        "examples/strata-preview/config.example.json": KIT
        / "examples/strata-preview/config.example.json",
    }.items():
        material[name] = source.read_bytes()
    material["README.md"] = (
        "# Strata Worker — limited supervised preview\n\n"
        "A local implementation subagent with host-owned scoped edits, checks, finite repair and canonical evidence. "
        "Primary still plans and independently accepts. Not general autonomous coding.\n\n"
        "One fresh isolated project copy per unit. Fixed create-only run material is not a reusable task queue; "
        "do not clear history or reset budgets to rerun. Primary reviews any diff before transferring it.\n\n"
        "Install into a trusted project without an existing `.local-agents`: `python -B install.py --target C:/work/my-project`. "
        "See [usage and safety](docs/strata-preview.md) and [configuration](examples/strata-preview/config.example.json).\n\n"
        "Requires an existing Strata harness0.2.1-alpha.3, Node, iq3_s model and project checks. "
        "No LM Studio service/lms, bundled model, upstream SDK defaults, shell/Web/skills or recursive agent. "
        "Shared safety-kernel legacy modules are inert dependencies, not enabled roles.\n\n"
        "Six independently accepted runs cover three exposed single-function contracts, not holdout or universal capability. "
        "Semantic repair passed offline, not exercised by first-pass live successes. Cloud savings unknown.\n"
    ).encode()
    metrics = read(BATCH / "metrics.json")
    evidence = {
        "version": "0.1.0-preview.1",
        "documentation_revision": 2,
        "runtime_build": receipt["version"],
        "status": "LIMITED_SUPERVISED_PREVIEW_CANDIDATE",
        "matrix": BATCH.name,
        "accepted": 6,
        "executed": 6,
        "not_run": 0,
        "families": [
            "strict UTF8 mapping_raw",
            "chronological collect_tools",
            "top-level request_hash transient keys",
        ],
        "live_http_requests": sum(
            r["actual"]["native_http_requests"] for r in metrics["rows"]
        ),
        "host_seconds": sum(r["host_seconds"] for r in metrics["rows"]),
        "historical_holds": [
            "strata-native-v2-20261023-1:5/6",
            "strata-native-v3-20261023-1:5/6",
            "strata-release-v4-20261023-1:0executed,6NOT_RUN,offline fault",
        ],
        "no_claims": [
            "general coding",
            "multifile",
            "unseen-repo transfer",
            "live semantic recovery",
            "cloud usage savings",
            "Coordinator",
            "fresh Local Reviewer",
        ],
        "primary": "Detailed frozen contracts/tests reused, independent complete diff/checks on each task; no live guidance or takeover; preparation/final-review active time and cloud tokens unknown",
        "upstream": "Strata/harness/Node/model not redistributed; configured local existing dependencies only",
    }
    material["release-evidence.json"] = (json.dumps(evidence, indent=2) + "\n").encode()
    manifest = {name: hashlib.sha256(raw).hexdigest() for name, raw in material.items()}
    material["manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError("Create-only package output")
    destination.mkdir(parents=True)
    for name, raw in material.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
    archive = destination.with_name(destination.name + ".zip")
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name in sorted(material):
            bundle.write(destination / name, name)
    return {
        "folder": str(destination),
        "archive": str(archive),
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "files": len(material),
    }


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(package(args.output), indent=2))


if __name__ == "__main__":
    main()
