"""Prospective contract clarity, same fixed tests; never rewrites prior scores."""

import argparse
import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import exception_reasoning_diagnostic as R

C, T, KIT, M = R.C, R.T, R.KIT, R.M
BATCH = KIT / "benchmarks/work/harness-convergence/exception-contract-20261018-1"
ORDER = [
    f"{a}-{n}"
    for n in (1, 2, 3)
    for a in (("original", "explicit") if n != 2 else ("explicit", "original"))
]
OLD = "Missing messages or unsupported scalar/string/bytes messages remain TypeError; invalid canonical messages remain rejected."
NEW = (
    "A Mapping in messages is in the singleton-message input domain regardless of whether required fields are present. "
    "Its success and exception category must equal passing that same Mapping as the sole element of the existing messages sequence. "
    "Invalid mappings, including empty mappings, missing fields, unknown fields and invalid role/content, retain the real model validation error (a ValueError), not TypeError. "
    "Missing messages and unsupported non-Mapping/non-Message scalar/string/bytes messages remain TypeError."
)


def prepare(used):
    assert 0 <= used < 15
    assert (
        T.read(R.BATCH / "decision.json")["status"] == "NO_DIAGNOSIS_ONLY_QUALIFICATION"
    )
    pins = T.read(R.BATCH / "freeze.json")["pins"]
    assert all(T.sha(p) == sha for p, sha in pins.items())
    BATCH.mkdir(exist_ok=False)
    fixture = T.read(C.BATCH / "fixture.json")
    original = fixture["facts"]
    assert OLD in original["goal"] and OLD in original["required_behavior"][0]["text"]
    explicit = copy.deepcopy(original)
    explicit["goal"] = explicit["goal"].replace(OLD, NEW, 1)
    explicit["required_behavior"][0]["text"] = explicit["required_behavior"][0][
        "text"
    ].replace(OLD, NEW, 1)
    fixture["explicit_user_message"] = R.D.INTERFACE.literal_input(explicit)
    T.save(BATCH / "fixture.json", fixture)
    T.save(
        BATCH / "registration.json",
        {
            "authorization": "Primary owns test contract design; user delegated routine same-boundary diagnosis. Explicit prospective packet meaning, not acceptance/test relaxation or retroactive interpretation of old failures",
            "feature_id": "mapping-input-domain-clarity",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "owned_contract_ids": ["messages_output"],
            "dependencies": ["closed-exception-reasoning"],
            "risk_rationale": "Input domain/exception compatibility must match protected acceptance; no production API edits",
            "order": ORDER,
            "registered": 6,
            "fresh_holdout": False,
            "old_wording": OLD,
            "prospective_wording": NEW,
            "Primary_responsibility": "Original natural-language contract left all-Mapping domain implicit in singleton-sequence equivalence; current error type alone is not enough to label every old failure an unambiguous model reasoning defect",
            "unchanged": "All25 acceptance tests/private tests, original full dependencies, failure/source/hash, system/schema, model/sampling, edit guards and static checks",
            "budget": {
                "proposals_per_cell": 1,
                "total_requests": 6,
                "output_tokens": 4096,
                "formatter_commands": 0,
                "retries": 0,
                "extra_probes": 0,
            },
            "criterion": "Explicit3/3 applied with all25 tests and strict checks; score behavior/static separately. Compare original contemporaneous3. No model/code example/gold/algorithm assistance, no Reviewer/full-chain/fresh credit. Stop at fixed6 or infra/drift/budget15.",
            "weekly_used_start": used,
            "weekly_used_ceiling": 15,
            "models": {
                "coder": "qwen/qwen3-coder-30b",
                "context": 24576,
                "parallel": 1,
            },
            "production_changes": False,
            "siblings": "read-only",
            "commit_push": False,
        },
    )
    shutil.copyfile(C.BATCH / "snapshot.py", BATCH / "snapshot.py")
    old = T.read(R.BATCH / "cells.json")["direct-1"]
    rows = {}
    for name in ORDER:
        root = BATCH / "cases" / name / "isolated"
        root.mkdir(parents=True)
        for p, sha in old["files"].items():
            source = (
                BATCH / "snapshot.py"
                if p == fixture["binding"]["path"]
                else Path(old["root"]) / p
            )
            assert T.sha(source) == sha
            target = root / p
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        rows[name] = {"root": str(root), "files": M.source_map(root)}
    T.save(BATCH / "cells.json", rows)


def freeze():
    import xml.etree.ElementTree as ET

    tree = ET.parse(BATCH / "controls-v1.xml")
    assert len(tree.findall(".//testcase")) == 3
    assert not any(tree.findall(".//" + k) for k in ("failure", "error", "skipped"))
    pins = T.read(R.BATCH / "freeze.json")["pins"]
    assert all(T.sha(p) == sha for p, sha in pins.items())
    paths = [
        Path(__file__),
        KIT / "tests/test_exception_contract.py",
        *[
            BATCH / p
            for p in (
                "registration.json",
                "fixture.json",
                "snapshot.py",
                "cells.json",
                "controls-v1.xml",
            )
        ],
    ]
    T.save(
        BATCH / "freeze.json", {"pins": {**pins, **{str(p): T.sha(p) for p in paths}}}
    )


def sample(name, used):
    original_read = T.read

    def read(path):
        value = original_read(path)
        if Path(path) == BATCH / "fixture.json" and name.startswith("explicit-"):
            value["user_message"] = value["explicit_user_message"]
        return value

    C.BATCH, C.ORDER = BATCH, ORDER
    R.D.PROMPTS.update(original=R.D.PROMPTS["whole"], explicit=R.D.PROMPTS["whole"])
    T.read = read
    try:
        C.sample(name, used)
    finally:
        T.read = original_read


def run_all(used):
    assert 0 <= used < 15
    for name in ORDER:
        cell = BATCH / "cases" / name
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(KIT / "benchmarks/r3_capture"),
            "R3_WIRE_DIR": str(cell / "wire"),
        }
        p = subprocess.run(
            [
                sys.executable,
                "-B",
                str(Path(__file__)),
                "sample",
                "--case",
                name,
                "--used",
                str(used),
            ],
            env=env,
            cwd=KIT,
            check=False,
        )
        assert p.returncode == 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["prepare", "freeze", "sample", "run-all"])
    p.add_argument("--used", type=int, required=True)
    p.add_argument("--case")
    args = p.parse_args()
    {
        "prepare": lambda: prepare(args.used),
        "freeze": freeze,
        "sample": lambda: sample(args.case, args.used),
        "run-all": lambda: run_all(args.used),
    }[args.action]()
