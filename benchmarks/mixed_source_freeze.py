"""Read-only source acquisition for mixed goals; outputs only under kit work.

Real-task replays are adapted: current read-only context/tests plus verified
archived writable preimages. Never claim an exact historical replay. Public
reference solutions are not written into worker snapshots.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import tarfile
import urllib.request
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
HARNESS = Path("F:/ChatGPT/agent-evaluation-harness")
WORK = KIT / "benchmarks/work/mixed-v1/candidate-1/sources"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def destination(root, relative):
    path = root / relative
    path.resolve().relative_to(root.resolve())
    return path


def write_json(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)


def freeze_real(case):
    root = WORK / case["case_id"]
    root.mkdir(parents=True, exist_ok=False)
    for relative in ("src", "tests", "docs"):
        source = HARNESS / relative
        # Exclude links and generated state; only source/context is copied.
        for path in sorted(source.rglob("*")):
            if (
                not path.is_file()
                or path.is_symlink()
                or any(
                    part in {"__pycache__", ".pytest_cache", ".agent"}
                    for part in path.parts
                )
            ):
                continue
            target = destination(root, path.relative_to(HARNESS))
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    for relative in ("pyproject.toml", "README.md"):
        shutil.copyfile(HARNESS / relative, root / relative)
    archive = (
        HARNESS / ".agent/tasks" / case["archive_task"] / "runs" / case["archive_run"]
    )
    preimages = read(archive / "preimages.json")
    for item in preimages:
        target = destination(root, item["path"])
        if item["existed"]:
            source = destination(HARNESS, item["archive_path"])
            if sha(source.read_bytes()) != item["sha256"]:
                raise ValueError("archived preimage hash mismatch")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        elif target.exists():
            raise ValueError("unexpected current file in historical create scope")
    if case["case_id"] == "score-summary":
        shutil.copyfile(
            HARNESS
            / ".agent/tasks/score-summary-20261003/pre-write-checkpoint/test_evaluation_score_summary.py",
            root / "tests/unit/test_evaluation_score_summary.py",
        )
    control = root / ".agent"
    control.mkdir()
    write_json(control / "historical-packet.json", read(archive / "packet.json"))
    return root, {
        "archive": str(archive),
        "preimages": preimages,
        "replay_kind": "adapted-current-readonly-context-not-exact-historical",
    }


def download(url):
    request = urllib.request.Request(
        url, headers={"User-Agent": "local-worker-kit-fixture"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def freeze_public(case, task):
    root = WORK / case["case_id"]
    root.mkdir(parents=True, exist_ok=False)
    raw = download(
        f"https://codeload.github.com/{case['repo']}/tar.gz/{case['base_commit']}"
    )
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        for member in archive:
            relative = Path(*Path(member.name).parts[1:])
            if not relative.parts:
                continue
            target = destination(root, relative)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as stream, target.open("xb") as output:
                    shutil.copyfileobj(stream, output)
            else:
                raise ValueError("links/special files not allowed in public snapshot")
    control = root / ".agent"
    control.mkdir()
    # Explicit field allowlist: do not forward patch, hints_text, test_patch.
    write_json(
        control / "public-task.json",
        {
            key: task[key]
            for key in (
                "instance_id",
                "repo",
                "base_commit",
                "problem_statement",
                "FAIL_TO_PASS",
                "PASS_TO_PASS",
            )
        },
    )
    return root, {
        "download_sha256": sha(raw),
        "base_commit": case["base_commit"],
        "official_score": False,
        "environment_status": "native-preflight-required-docker-not-running",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=("real", "public"), required=True)
    args = parser.parse_args()
    cases = read(KIT / "benchmarks/fixtures/mixed-features-v1.json")["external_cases"]
    tasks = {}
    if args.kind == "public":
        for offset in (0, 100, 200):
            payload = json.loads(
                download(
                    "https://datasets-server.huggingface.co/rows?dataset=SWE-bench%2FSWE-bench_Lite"
                    f"&config=default&split=test&offset={offset}&length=100"
                )
            )
            for row in payload["rows"]:
                task = row["row"]
                tasks[task["instance_id"]] = task
    for case in cases:
        is_public = case["origin"] == "SWE-bench-Lite"
        if is_public != (args.kind == "public"):
            continue
        if is_public:
            task = tasks[case["case_id"]]
            if (
                task["base_commit"] != case["base_commit"]
                or task["repo"] != case["repo"]
            ):
                raise ValueError("dataset provenance changed")
            root, provenance = freeze_public(case, task)
        else:
            root, provenance = freeze_real(case)
        files = {
            path.relative_to(root).as_posix(): sha(path.read_bytes())
            for path in sorted(root.rglob("*"))
            if path.is_file()
        }
        write_json(
            root / "source-freeze.json",
            {
                "case": case,
                "files": files,
                "provenance": provenance,
                "worker_result": "not_run",
                "feature_accepted": False,
            },
        )
        print(
            json.dumps(
                {
                    "case": case["case_id"],
                    "root": str(root),
                    "files": len(files),
                    **provenance,
                },
                default=str,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
