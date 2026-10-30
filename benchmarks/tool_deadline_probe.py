"""Primary-only CPython deadline-registration probe, with source provenance."""

import argparse
import os

from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest
from layer_isolation import command
from tool_awaitable_trial import PYTHON, TARGET
from tool_primary_verification import junit_counts


def probe(root, label):
    root = root.resolve()
    root.relative_to(WORK.resolve())
    if not label or any(
        c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in label
    ):
        raise ValueError("unique safe label required")
    output = root / ".agent" / label
    if output.with_suffix(".json").exists():
        raise ValueError("immutable probe already exists")
    test = (
        KIT / "benchmarks/fixtures/tool-awaitable-extra/test_deadline_registration.py"
    )
    source_hash = digest(root / TARGET)
    test_hash = digest(test)
    old_value = os.environ.get("LW_DEADLINE_CODE_ROOT")
    os.environ["LW_DEADLINE_CODE_ROOT"] = str(root)
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
                str(test),
                "-q",
                "-p",
                "no:cacheprovider",
                "--basetemp=.agent/" + label + "-temp",
                "--junitxml=.agent/" + label + ".xml",
            ],
        )
    finally:
        if old_value is None:
            del os.environ["LW_DEADLINE_CODE_ROOT"]
        else:
            os.environ["LW_DEADLINE_CODE_ROOT"] = old_value
    if digest(root / TARGET) != source_hash or digest(test) != test_hash:
        raise ValueError("source or probe drift")
    counts = junit_counts(output.with_suffix(".xml"))
    write(
        output.with_suffix(".json"),
        {
            "invocation": invoked,
            "junit": counts,
            "source_sha256": source_hash,
            "probe_sha256": test_hash,
            "source_unchanged": True,
            "primary_only": True,
            "limitations": "CPython 3.12 public asyncio.Timeout registration on the existing wait_for deadline. Not a cross-interpreter guarantee, source-shape check, duration-extension claim or worker credit.",
        },
    )
    print({"root": str(root), "junit": counts, "primary_only": True})


if __name__ == "__main__":
    from pathlib import Path

    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("root", type=Path)
    parser.add_argument("label")
    args = parser.parse_args()
    probe(args.root, args.label)
