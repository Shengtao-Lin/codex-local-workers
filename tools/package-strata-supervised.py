"""Create a portable supervised candidate from frozen runtime and reviewed support."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
BASE = KIT / "releases/strata-task34/product"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def material():
    files = {}
    manifest = json.loads((BASE / "manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest.items():
        path = BASE / name
        if not path.resolve().is_relative_to(BASE.resolve()) or path.is_symlink():
            raise ValueError("Invalid frozen path: " + name)
        raw = path.read_bytes()
        if digest(raw) != expected:
            raise ValueError("Frozen runtime drift: " + name)
        files[name] = raw
    for name in ("README.md", "AGENTS.strata.md", "PROFILES.md"):
        files[name] = (KIT / "strata-product" / name).read_bytes()
    files["CONTRACT.md"] = (KIT / "docs/strata-practical-contract.md").read_bytes()
    files["tools/prepare-strata-return.py"] = (
        KIT / "tools/prepare-strata-return.py"
    ).read_bytes()
    files["tools/strata-setup.py"] = (KIT / "tools/strata-setup.py").read_bytes()
    files["SETUP.md"] = (KIT / "strata-product/SETUP.md").read_bytes()
    files["VERSION"] = (KIT / "strata-product/VERSION").read_bytes()
    for name in (
        "trace-behavior",
        "summarize-structured-data",
        "source-backed-handoff",
    ):
        files[f"skills/{name}/SKILL.md"] = (
            KIT / "strata-skills" / name / "SKILL.md"
        ).read_bytes()
    for name in ("coding", "investigation", "investigation-followup", "capabilities"):
        config = json.loads(
            (KIT / "strata-product/examples" / f"config.{name}.json").read_text(
                encoding="utf-8"
            )
        )
        # Examples do not grant skill access by default. Caller may explicitly opt in.
        config.pop("experimental_strata_skills", None)
        files[f"examples/config.{name}.json"] = (
            json.dumps(config, indent=2) + "\n"
        ).encode()
    return files


def package(destination):
    destination = Path(destination).resolve()
    archive = destination.with_name(destination.name + ".zip")
    if destination.exists() or archive.exists():
        raise FileExistsError("Create-only package output")
    files = material()
    evidence = {
        "product": "Strata supervised subagent release candidate",
        "version": (KIT / "strata-product/VERSION").read_text(encoding="utf-8").strip(),
        "runtime": "unchanged 0.3.0-task.34-binding-preflight-candidate",
        "runtime_manifest_sha256": digest((BASE / "manifest.json").read_bytes()),
        "production_enabled": False,
        "readiness": "LOCAL_VALIDATED_REMOTE_RELEASE_REPLAY_PENDING",
        "qualification": "Primary-supervised work; not autonomous final acceptance",
        "qualification_details": json.loads(
            (KIT / "strata-product/qualification.json").read_text(encoding="utf-8")
        ),
        "limits": [
            "Reviewer and investigation reports may contain incorrect extra claims",
            "coding and automatic Reviewer skills are not enabled",
            "no arbitrary shell, model-written scripts or deep recursion",
            "no continuation with optional capabilities",
            "cloud savings and Primary active time unknown",
        ],
    }
    files["release-evidence.json"] = (json.dumps(evidence, indent=2) + "\n").encode()
    pins = {name: digest(raw) for name, raw in files.items()}
    files["manifest.json"] = (json.dumps(pins, indent=2) + "\n").encode()
    destination.mkdir(parents=True)
    for name, raw in files.items():
        p = destination / name
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("xb") as stream:
            stream.write(raw)
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name in sorted(files):
            # Stable archive metadata: identical source bytes produce identical ZIPs.
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(info, files[name], compresslevel=9)
    return {
        "folder": str(destination),
        "archive": str(archive),
        "sha256": digest(archive.read_bytes()),
        "files": len(files),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--output", type=Path, required=True)
    print(json.dumps(package(parser.parse_args().output), indent=2))
