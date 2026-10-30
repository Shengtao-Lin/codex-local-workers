"""Freeze the published Strata baseline in an isolated, explicitly new clone."""

import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEV = ROOT / "benchmarks/work/strata-general-dev/repository"
OUT = ROOT / "benchmarks/work/harness-convergence/strata-general-s0-20261023-2"
ZIP = ROOT / "benchmarks/work/releases/strata-worker-0.1.0-preview.1-final.zip"
COMMIT = "0f7fe1c08df0d38db8f7b57426582088ab0322cc"
EXPECTED = "75f68311641fa727e8220fbeec571c7d33650560390c5c702ebd1bf887f10095"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def git(cwd, *args):
    return subprocess.check_output(["git", *args], cwd=cwd).decode("utf-8").strip()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    if git(DEV, "rev-parse", "HEAD") != COMMIT or git(DEV, "branch", "--show-current") != "strata-dev":
        raise ValueError("Only the explicitly isolated new clone is eligible")
    if digest(ZIP.read_bytes()) != EXPECTED:
        raise ValueError("Published ZIP drift")
    with zipfile.ZipFile(ZIP) as archive:
        material = {name: archive.read(name) for name in archive.namelist()}
    manifest = json.loads(material["manifest.json"])
    if set(material) != set(manifest) | {"manifest.json"}:
        raise ValueError("ZIP inventory differs")
    for name, expected in manifest.items():
        if digest(material[name]) != expected:
            raise ValueError("Published manifest drift: " + name)
    save(OUT / "registration.json", {
        "stage": "S0", "live": 0, "published_commit": COMMIT,
        "zip_sha256": EXPECTED, "weekly_used_start": 3, "weekly_stop": 50,
        "model": "iq3_s", "instance": "2b1266cf-c609-421d-a538-19bfd4f7ea73",
        "context": 131072, "parallel": 1, "lmstudio_loaded": 0,
        "feature_id": "strata-general-core", "feature_risk": "high", "integration_risk": "high",
        "units": [
            {"id": "task-lifecycle", "risk": "high", "contracts": ["identity", "persistent-budget", "cancel-resume"], "depends": []},
            {"id": "general-unit", "risk": "high", "contracts": ["scope-version", "batch-edit", "current-complete-checks"], "depends": ["task-lifecycle"]},
            {"id": "native-context", "risk": "high", "contracts": ["local-only", "state-evidence", "no-autoaccept"], "depends": ["general-unit"]},
        ],
        "rationale": "Permissions, recovery and public runtime validation remain indivisible high-risk invariants",
    })
    save(OUT / "original-worktree.json", {
        "head": git(ROOT, "rev-parse", "HEAD"),
        "branch": git(ROOT, "branch", "--show-current"),
        "status": git(ROOT, "status", "--porcelain=v1"),
    })
    # This newly created clone alone receives the exact verified published bytes.
    # No existing user work is reset; do not repeat bootstrap after development.
    for name, raw in material.items():
        path = DEV / name
        if not path.resolve().is_relative_to(DEV.resolve()):
            raise ValueError("ZIP path escaped")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    # The product branch has one additional publication note outside the ZIP.
    note = subprocess.check_output(["git", "show", "HEAD:RELEASE_NOTES.md"], cwd=DEV)
    (DEV / "RELEASE_NOTES.md").write_bytes(note)
    if git(DEV, "status", "--porcelain=v1"):
        raise ValueError("Published package is not byte-identical to committed tree")
    files = {}
    for name, raw in material.items():
        source = name.removeprefix("runtime/")
        if name.startswith("runtime/.local-agents/strata/"):
            source = "benchmarks/" + Path(name).name
        files[name] = {"sha256": digest(raw), "historical_source": source}
    save(OUT / "source-map.json", {"canonical_root": str(DEV), "files": files})
    save(OUT / "decision.json", {"status": "PASS_S0_BYTE_BASELINE", "live": 0, "files": len(material), "original_worktree_untouched": True})
    plan = ROOT / "docs/strata-general-stable-plan.md"
    destination = DEV / "docs/strata-general-stable-plan.md"
    with destination.open("xb") as stream:
        stream.write(plan.read_bytes())
    print(json.dumps({"status": "PASS_S0_BYTE_BASELINE", "files": len(material), "developer_root": str(DEV)}))


if __name__ == "__main__":
    main()
