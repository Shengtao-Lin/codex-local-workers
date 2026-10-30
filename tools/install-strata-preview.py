"""Create-only preview installer. Does not alter models, Git or dependencies."""

import argparse
import hashlib
import json
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
NATIVE = [
    "strata_artifacts.py",
    "strata_bridge_host.py",
    "strata_subagent_rules.py",
    "approved_evidence.py",
    "strata_manifest_search.py",
    "strata_protected_manifest.py",
    "strata_native_agent_host.py",
    "strata_native_host_v2.py",
    "strata_native_host_v4.py",
    "strata_native_feedback.py",
    "strata_native_agent.mjs",
    "strata_native_agent_core.mjs",
    "strata_kit_tool_bridge.mjs",
]


def install(target):
    target = Path(target).resolve(strict=True)
    if not target.is_dir():
        raise ValueError("Existing explicit project directory required")
    destination = target / ".local-agents"
    if destination.exists():
        raise FileExistsError("Create-only installation refuses existing .local-agents")
    files = {}
    # Shared safety kernel, not a fork. Legacy transports are inert dependencies;
    # this entry never loads their models, lms CLI or default configuration.
    core = KIT / ".local-agents"
    for path in [*core.glob("*.py"), *(core / "bounded").glob("*.py")]:
        files[path.relative_to(core).as_posix()] = path
    for name in NATIVE:
        files["strata/" + name] = KIT / "benchmarks" / name
    for source in files.values():
        if not source.is_file():
            raise FileNotFoundError(source)
    # Read all bytes before the first write; missing source never half-installs.
    material = {name: path.read_bytes() for name, path in files.items()}
    destination.mkdir()  # Exclusive root; do not merge with an existing install.
    for name, raw in material.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
    receipt = {
        "version": "0.1.0-preview-candidate.4.1",
        "production_default": False,
        "files": {
            name: hashlib.sha256(raw).hexdigest() for name, raw in material.items()
        },
        "requires": "existing Strata harness0.2.1-alpha.3, local iq3_s, configured project Python/checks",
        "permissions": "approved manifest READ/SEARCH, one function edit, trusted host checks; no model shell/web/Git/recursion",
        "acceptance": "host pending review -> independent Primary only; not an autoaccept",
    }
    path = destination / "strata/installation.json"
    with path.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2)
    return {
        "installed": str(destination),
        "files": len(material),
        "version": receipt["version"],
    }


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--target", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(install(args.target), indent=2))


if __name__ == "__main__":
    main()
