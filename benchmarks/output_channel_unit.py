"""Original automatic unit orchestration, explicit experimental Coder entry."""

import subprocess

import capture_unit_entry as UNIT

original_run = subprocess.run


def dispatch(argv, *args, **kwargs):
    argv = [str(x) for x in argv]
    original = str(UNIT.F.KIT / "benchmarks/capture_coder_entry.py")
    if original in argv:
        argv[argv.index(original)] = str(
            UNIT.F.KIT / "benchmarks/coder_output_channel.py"
        )
    return original_run(argv, *args, **kwargs)


if __name__ == "__main__":
    subprocess.run = dispatch
    raise SystemExit(UNIT.main())
