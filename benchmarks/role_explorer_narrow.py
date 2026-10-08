"""Read-only narrower question after archived broad-query failure; no score overwrite."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import mixed_feature_benchmark as MIXED
from capability_fit import KIT, WORK, write


def run(case, repetition):
    base = WORK / "roleq-six-1"
    MIXED.CORPUS = base / "corpus.json"
    MIXED.WORK = base / "explorer-narrow"
    prepared = MIXED.prepare(
        case, repetition, KIT / ".local-agents/config.json", "narrow1"
    )
    root = Path(prepared["root"])
    config_path = root / ".agent/config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config.update(
        explorer_required_citation_paths=["tests/test_target.py"],
        explorer_require_test_assertion_citation=True,
    )
    # Separate trusted diagnostic config; preserve prepared original.
    config_path = root / ".agent/explorer-narrow-config.json"
    write(config_path, config)
    packet = json.loads(
        (root / ".agent/qual-unit-reference.json").read_text(encoding="utf-8")
    )
    if case == "timeout-roundtrip":
        question = "Locate parse_timeout in src/product/options.py and the protected assertion rejecting explicit None in tests/test_target.py. Read both and return exact implementation/test ranges. No repair prediction."
    else:
        question = "Locate decode_query in src/product/codec.py and the protected special-character roundtrip assertion in tests/test_target.py. Read both and return exact implementation/test ranges. No repair prediction."
    snapshot = WORK / "roleq-six-runtime-1"
    result = subprocess.run(
        [
            sys.executable,
            str(snapshot / ".local-agents/local-explore.py"),
            "--task",
            question,
            "--task-id",
            packet["task_id"],
            "--config",
            str(config_path),
            "--report",
            str(root / ".agent/explorer.json"),
            "--full-report",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=900,
    )
    report = json.loads((root / ".agent/explorer.json").read_text(encoding="utf-8"))
    refs = report.get("source_refs", [])
    verified = []
    for ref in refs:
        path = ref.get("path")
        if path not in packet["scope"]["modify"] + packet["scope"]["readonly"]:
            raise ValueError("unexpected citation")
        quote = ref.get("quote")
        verified.append(
            bool(quote and quote in (root / path).read_text(encoding="utf-8"))
        )
    summary = {
        "classification": "narrowed diagnostic call; original broad question results retained",
        "case": case,
        "repetition": repetition,
        "exit": result.returncode,
        "status": report.get("status"),
        "failure": report.get("failure_reason"),
        "verified_quotes": verified,
        "relevant_test_read": any(
            r.get("path") == "tests/test_target.py" for r in refs
        ),
        "source_refs": refs,
        "workspace": str(root),
    }
    write(root / "narrow-result.json", summary)
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case", choices=("timeout-roundtrip", "case-preserving-query"), required=True
    )
    parser.add_argument("--repetition", type=int, choices=(1, 2), required=True)
    args = parser.parse_args()
    run(args.case, args.repetition)
