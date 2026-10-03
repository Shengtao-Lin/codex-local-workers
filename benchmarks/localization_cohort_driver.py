"""Serial frozen standard cells; never infer Primary acceptance from workers."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import stability_e2e as stability
from localization_route_smoke import runtime_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--round", type=int, choices=(1, 2), required=True)
    parser.add_argument("--supervised-entry", action="store_true")
    args = parser.parse_args()
    config = json.loads(
        (stability.KIT / ".local-agents/config.json").read_text(encoding="utf-8-sig")
    )
    config["explorer_mode"] = "locate"
    manifest = json.loads(
        (stability.KIT / "benchmarks/localization-cohort-v2.1.json").read_text()
    )
    candidate = args.candidate.resolve()
    if candidate.parent != stability.WORK.resolve():
        raise ValueError("candidate must be a direct stability work directory")
    freeze = candidate / "freeze.json"
    provenance = {
        "runtime": runtime_manifest(config),
        "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "cohort": manifest,
        "entry_mode": "model-supervised-managed-exploration"
        if args.supervised_entry
        else "primary-packet-localization",
    }
    if freeze.exists():
        if json.loads(freeze.read_text()) != provenance:
            raise ValueError("candidate runtime/config/driver/cohort changed")
    else:
        if args.round != 1:
            raise ValueError("round 1 must freeze candidate first")
        stability.write_json(freeze, provenance)
    for case in manifest["standard_cases"]:
        destination = candidate / f"round-{args.round}" / f"{case}.json"
        if destination.exists():
            raise ValueError("existing cell cannot be replayed or overwritten")
        if runtime_manifest(config) != provenance["runtime"]:
            raise ValueError("runtime changed during candidate")
        result = stability.run_command(
            stability.KIT,
            [
                sys.executable,
                str(stability.KIT / "benchmarks/localization_route_smoke.py"),
                "--case",
                case,
                "--unknown-location",
                *(["--managed-exploration"] if args.supervised_entry else []),
            ],
            1900,
        )
        try:
            cell = json.loads(result.stdout)
        except ValueError:
            stability.write_json(
                destination,
                {
                    "unparseable": True,
                    "exit": result.returncode,
                    "stderr": result.stderr[-2000:],
                    "stdout": result.stdout[-2000:],
                },
            )
            return 2
        stability.write_json(destination, cell)
        print(
            json.dumps(
                {
                    "round": args.round,
                    "case": case,
                    "workspace": cell["workspace"],
                    "qualified_pass": cell.get("qualified_pass"),
                    "stage": cell.get("stage"),
                }
            ),
            flush=True,
        )
        # A failed cell is retained. Primary decides whether a fresh bounded
        # candidate can continue; this driver never replays a failed worker.
        if not cell.get("qualified_pass"):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
