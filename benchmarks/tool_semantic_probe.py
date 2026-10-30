"""Primary-only identity controls, with explicit code provenance and immutable facts."""

import argparse
import os
import shutil
from pathlib import Path

from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest
from layer_isolation import command
from tool_awaitable_trial import PYTHON, TARGET
from tool_primary_verification import junit_counts


def probe(root, label, probe_file="primary_async_identity.py"):
    if probe_file not in {
        "primary_async_identity.py",
        "primary_context_identity.py",
        "primary_plain_mapping.py",
    }:
        raise ValueError("registered probe required")
    root = root.resolve()
    root.relative_to(WORK.resolve())
    if not label or any(
        c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in label
    ):
        raise ValueError("safe unique label required")
    out = root / ".agent" / label
    if out.with_suffix(".json").exists():
        raise ValueError("immutable probe exists")
    source = digest(root / TARGET)
    old = os.environ.get("LW_COMPAT_CODE_ROOT")
    os.environ["LW_COMPAT_CODE_ROOT"] = str(root)
    try:
        invoked = command(
            root,
            [
                str(PYTHON),
                "-B",
                "-m",
                "pytest",
                "-c",
                str(root / "pyproject.toml"),
                "--rootdir=" + root.as_posix(),
                "-o",
                "pythonpath=" + (root / "src").as_posix(),
                str(KIT / "benchmarks/fixtures/tool-awaitable-extra" / probe_file),
                "-q",
                "-p",
                "no:cacheprovider",
                "--basetemp=.agent/" + label + "-temp",
                "--junitxml=.agent/" + label + ".xml",
            ],
        )
    finally:
        if old is None:
            del os.environ["LW_COMPAT_CODE_ROOT"]
        else:
            os.environ["LW_COMPAT_CODE_ROOT"] = old
    if digest(root / TARGET) != source:
        raise ValueError("source drift during probe")
    counts = junit_counts(out.with_suffix(".xml"))
    write(
        out.with_suffix(".json"),
        {
            "invocation": invoked,
            "junit": counts,
            "source_sha256": source,
            "primary_only": True,
            "source_unchanged": True,
        },
    )
    print({"root": str(root), "junit": counts})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("root", type=Path)
    parser.add_argument("label")
    parser.add_argument("--copy-original", action="store_true")
    parser.add_argument("--probe-file", default="primary_async_identity.py")
    args = parser.parse_args()
    if args.copy_original:
        args.root.resolve().relative_to(WORK.resolve())
        shutil.copytree(KIT / "benchmarks/fixtures/tool-awaitable-v8", args.root)
    probe(args.root, args.label, args.probe_file)
