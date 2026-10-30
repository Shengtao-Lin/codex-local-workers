"""Independent audit collector; original batch runner and errors remain intact."""

import argparse
import sys
from pathlib import Path

from capability_fit import write
from fixed_candidate_repeat import verify
from inherited_context_recovery import digest, read
from supervised_scope_check import invoke


def audit(cell):
    root = Path(cell["root"])
    archive = root / ".agent/tasks" / cell["task_id"] / "runs" / cell["run_id"]
    for path, sha in cell["paths"].items():
        if path != cell["source"]:
            assert digest(root / path) == sha, path
    assert digest(root / ".agent/packet.json") == cell["packet_sha256"]
    assert digest(root / ".agent/config.json") == cell["config_sha256"]
    coder = read(archive / "handoff.json")
    compact = read(root / ".agent/coder.json")
    reviewer = read(root / ".agent/reviewer.json")
    assert coder["status"] == "ready_for_review"
    assert reviewer["decision"] == "pass_to_primary"
    assert compact["validation_summary"]["executed"] == cell["expected_tests"]
    assert compact["validation_summary"]["inputs_unchanged"]
    assert reviewer["runtime_facts"]["inputs_unchanged"]
    assert [c["path"] for c in coder["changed_files"]] == [cell["source"]]
    checks = [
        ("tests", ["-m", "pytest", "-q", "--junitxml=.agent/primary-repeat.xml"]),
        ("lint", ["-m", "ruff", "check", "src", "tests"]),
        ("format", ["-m", "ruff", "format", "--check", "src", "tests"]),
    ]
    if cell["id"].startswith("timestamp"):
        checks.append(
            ("types", ["-m", "pyright", "--pythonpath", sys.executable, "src"])
        )
    else:
        probe = (
            "import asyncio,sys;sys.path.insert(0,'src');from product.entry import read_batch\n"
            "calls=[];keys=[0,1,2,3,4];values=[0,False,'',None,99]\n"
            "async def fetch(key):\n calls.append(key);return values[key]\n"
            "result=asyncio.run(read_batch(fetch,keys))\n"
            "assert result==[0,False,''] and result[0] is not False and result[1] is False\n"
            "assert calls==[0,1,2,3] and keys==[0,1,2,3,4]\n"
        )
        checks.append(("entry", ["-c", probe]))
    for name, argv in checks:
        prior = root / f".agent/primary-{name}-invocation.json"
        result = (
            read(prior)
            if prior.exists()
            else invoke(root, "primary-" + name, [sys.executable, "-B", *argv])
        )
        assert result["exit"] == 0, result
    output = root / ".agent/independent-repeat-audit.json"
    assert not output.exists()
    facts = {
        "protected_unchanged": True,
        "tests": cell["expected_tests"],
        "coder_protocol_errors": coder["protocol_error_count"],
        "reviewer_protocol_errors": reviewer["runtime_facts"]["protocol_error_count"],
        "reviewer_decision": reviewer["decision"],
        "seconds": read(root / ".agent/repeat-live-invocation.json")["seconds"],
        "primary_diff_review_pending": True,
    }
    write(output, facts)
    print(cell["id"], facts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("cell")
    args = parser.parse_args()
    audit(next(c for c in verify()["cells"] if c["id"] == args.cell))
