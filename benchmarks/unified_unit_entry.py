"""Unchanged canonical unit/review workflow, explicit unified Coder receiver."""

import subprocess

import capture_unit_entry as UNIT

original = subprocess.run


def dispatch(argv, *args, **kwargs):
    argv = [str(x) for x in argv]
    old = str(UNIT.F.KIT / "benchmarks/capture_coder_entry.py")
    if old in argv:
        argv[argv.index(old)] = str(UNIT.F.KIT / "benchmarks/unified_coder_entry.py")
    return original(argv, *args, **kwargs)


if __name__ == "__main__":
    subprocess.run = dispatch
    raise SystemExit(UNIT.main())
