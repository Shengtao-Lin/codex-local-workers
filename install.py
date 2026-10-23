"""Install the adjacent frozen runtime into a trusted project, never overwrite."""

import argparse
import hashlib
import json
from pathlib import Path


def install(source, target):
    source = Path(source).resolve(strict=True)
    original = Path(target)
    if original.is_symlink():
        raise ValueError("Target must be an ordinary explicit directory")
    target = original.resolve(strict=True)
    destination = target / ".local-agents"
    if not target.is_dir() or destination.exists():
        raise FileExistsError(
            "Target must exist and have no .local-agents; no merge/overwrite"
        )
    receipt_path = source / "strata/installation.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    material = {}
    for name, expected in receipt["files"].items():
        path = source / name
        if not path.resolve().is_relative_to(source) or path.is_symlink():
            raise ValueError("Invalid packaged path")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("Packaged runtime drift: " + name)
        material[name] = raw
    material["strata/installation.json"] = receipt_path.read_bytes()
    destination.mkdir()
    for name, raw in material.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
    return {
        "installed": str(destination),
        "build": receipt["version"],
        "files": len(material),
        "acceptance": False,
    }


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--target", type=Path, required=True)
    args = parser.parse_args()
    source = Path(__file__).resolve().parent / "runtime/.local-agents"
    print(json.dumps(install(source, args.target), indent=2))


if __name__ == "__main__":
    main()
