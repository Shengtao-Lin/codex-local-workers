"""Unchanged deterministic handoff and Reviewer; only replace Coder receiver."""

import subprocess

import capture_unit_entry as UNIT

if __name__ == "__main__":
    original = subprocess.run

    def dispatch(argv, *args, **kwargs):
        argv = [str(a) for a in argv]
        old = str(UNIT.F.KIT / "benchmarks/capture_coder_entry.py")
        if old in argv:
            argv[argv.index(old)] = str(
                UNIT.F.KIT / "benchmarks/feedback_receipt_entry.py"
            )
        return original(argv, *args, **kwargs)

    subprocess.run = dispatch
    raise SystemExit(UNIT.main())
