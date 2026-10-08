"""Recover exact pinned source bytes from read-only Git history into kit cache."""

import hashlib
import json
import subprocess

import stability_e2e as S


def recover():
    cache = S.KIT / "benchmarks/fixtures/pinned-sources"
    records = []
    sources = {
        (s.repository, s.relative, s.sha256): s for c in S.CASES for s in c.copies
    }
    for source in sources.values():
        origin = S.SOURCES[source.repository]
        live = (origin / source.relative).read_bytes()
        if hashlib.sha256(live).hexdigest() == source.sha256:
            continue
        target = cache / source.sha256
        if target.exists():
            assert hashlib.sha256(target.read_bytes()).hexdigest() == source.sha256
            continue
        revisions = (
            subprocess.run(
                ["git", "log", "--format=%H", "--", source.relative],
                cwd=origin,
                capture_output=True,
                check=True,
            )
            .stdout.decode()
            .splitlines()
        )
        found = False
        for revision in revisions:
            result = subprocess.run(
                ["git", "show", f"{revision}:{source.relative}"],
                cwd=origin,
                capture_output=True,
                check=False,
            )
            if result.returncode:
                continue
            for raw in (
                result.stdout,
                result.stdout.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"),
            ):
                if hashlib.sha256(raw).hexdigest() != source.sha256:
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as stream:
                    stream.write(raw)
                records.append(
                    {
                        "repository": source.repository,
                        "path": source.relative,
                        "revision": revision,
                        "sha256": source.sha256,
                    }
                )
                found = True
                break
            if found:
                break
        if not found:
            records.append(
                {
                    "repository": source.repository,
                    "path": source.relative,
                    "sha256": source.sha256,
                    "unavailable": True,
                }
            )
    output = S.WORK / "pinned-recovery-roleq1.json"
    with output.open("x", encoding="utf-8") as stream:
        json.dump(records, stream, indent=2)
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    recover()
