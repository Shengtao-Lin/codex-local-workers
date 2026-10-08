"""Fresh replay after user corrected that prior instance was not reloaded."""

import argparse
from pathlib import Path

import vcache_current_probe as probe
from capability_fit import WORK


def configure():
    probe.BASE = WORK / "roleq-vcache-f16-user-2"
    probe.FA.DRIVERS.append(Path(__file__))
    original_write = probe.write

    def write(path, value):
        if path == probe.BASE / "manifest.json":
            value = dict(value)
            value["weekly_used_start"] = 52
            value["retry_reason"] = (
                "User explicitly corrected that the previous cohort's V-cache "
                "setting was not loaded; retry on the now user-reloaded instance. "
                "Previous cohort is not valid evidence of F16 performance."
            )
            value["previous_cohort"] = "roleq-vcache-f16-user-1"
        original_write(path, value)

    probe.write = write


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "r1", "r2"))
    args = parser.parse_args()
    configure()
    if args.action == "prepare":
        probe.prepare()
    else:
        probe.run(int(args.action[-1]))
