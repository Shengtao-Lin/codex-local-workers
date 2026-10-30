"""Same six contracts/gates, source-authorized evidence pool v3; no reroll."""

import argparse
import os
from pathlib import Path

import strata_native_matrix as M


def main():
    M.BATCH = M.BASE / "strata-native-v3-20261023-1"
    M.ENTRY = Path(__file__).with_name("strata_native_host_v3.py")
    M.SOURCES = [
        *M.SOURCES,
        "strata_native_v3_matrix.py",
        "strata_native_host_v3.py",
        "strata_protected_manifest.py",
    ]
    M.CANDIDATE = "Native v3: same v2 except evidence pool derives from authenticated preparation source manifest"
    M.CHANGES = "Tool-readable pool grows from four hints to all explicitly frozen source_paths, <=125, only inside existing approved packet read scope. Source files already protected/hash-bound; no directory walk or hidden acceptance. Same4 evidence actions/120lines/10matches, no model/writable/test/validation/total budget change. Initial readable-file list is larger; not a same-fact-set format-only A/B. v2 HOLD5/6 preserved."
    M.CONTROL_EXTRA = [
        {
            "name": "kit_read",
            "arguments": {
                "path": "src/evaluation_harness/trace_sources/base.py",
                "start_line": 1,
                "end_line": 60,
            },
        }
    ]
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", *M.CASES])
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if args.mode == "prepare":
        M.prepare(args.weekly_used)
    else:
        # Generic v2 control assertion expects one action; v3 intentionally has
        # a new dependency READ plus SEARCH before edit. Reuse run machinery and
        # check this composition explicitly below, without changing task gates.
        if args.mode == "control":
            root = M.BATCH / "cells/control/isolated"
            reg = M.S.read(M.BATCH / "registration.json")
            assert all(M.S.sha(p) == h for p, h in reg["pins"].items())
            packet = M.S.read(root / ".agent/packet.json")
            prepared = root / ".agent/prepared" / packet["run_id"]
            result = M.command(
                [
                    M.S.PYTHON,
                    "-B",
                    M.ENTRY,
                    "--packet",
                    prepared / "packet.json",
                    "--config",
                    prepared / "config.json",
                    "--program",
                    root.parent / "frontend.json",
                ],
                root,
                timeout=1020,
            )
            M.S.save(root.parent / "process.json", result)
            summary = M.S.read(root / ".agent/native-host-summary.json")
            M.S.save(
                root.parent / "result.json",
                {"exit_code": result["exit_code"], **summary},
            )
            assert result["exit_code"] == 0 and summary["host_handoff_verified"], result
            assert (
                summary["provider_calls"] == 0
                and summary["actual"]["evidence_actions"] == 2
            )
            assert (
                summary["actual"]["native_request_reservations"] == 3
                and summary["actual"]["requests"] == 3
            )
            print(
                "PASS v3 real host dependency READ+manifest SEARCH+edit+checks,6 shared credits,0 HTTP"
            )
        else:
            M.run(args.mode, args.weekly_used)


if __name__ == "__main__":
    main()
