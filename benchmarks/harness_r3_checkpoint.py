"""Preserve the dirty R3 starting point without Git mutations or model calls."""

import shutil
import subprocess
from pathlib import Path

import harness_convergence as base


def main():
    previous = base.KIT / "benchmarks/work/harness-convergence/r2-boundary-20261014-1"
    batch = base.KIT / "benchmarks/work/harness-convergence/r3-host-20261015-1"
    batch.mkdir(parents=True, exist_ok=False)
    paths = set(map(Path, base.read(previous / "baseline.json")))
    paths.update(base.files(previous))
    listed = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=base.KIT,
        text=True,
        encoding="utf-8",
    ).splitlines()
    paths.update(base.KIT / name for name in listed if (base.KIT / name).is_file())
    hashes = {}
    for index, path in enumerate(sorted(paths), 1):
        hashes[str(path)] = base.sha(path)
        if index % 20000 == 0:
            print(f"Checkpoint {index}/{len(paths)}", flush=True)
    base.save(batch / "baseline.json", hashes)
    for name in listed:
        path = base.KIT / name
        if path.is_file():
            target = batch / "checkpoint" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    base.save(
        batch / "environment.json",
        {
            "weekly_used": 0,
            "weekly_stop": 30,
            "observation": "Actual account read 2026-10-15; window reset, not inferred from previous 11%",
            "git_status": base.command(["git", "status", "--short"]),
            "git_head": base.command(["git", "rev-parse", "HEAD"]),
            "models": base.command(["C:/Users/Lin/.lmstudio/bin/lms.exe", "ps"]),
            "siblings": {
                name: base.command(
                    ["git", "-C", str(base.KIT.parent / name), "status", "--short"]
                )
                for name in ("agent-runtime-kit", "agent-evaluation-harness")
            },
        },
    )
    print(f"Saved {len(hashes)} paths: {batch}", flush=True)


if __name__ == "__main__":
    main()
