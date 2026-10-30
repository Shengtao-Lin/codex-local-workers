"""No-op recovery changes wire once, not authority, validation or credits."""

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / ".local-agents"))
sys.path.insert(0, str(KIT / "benchmarks"))
import noop_block_recovery as R
from bounded import compatibility_profile as C
from bounded import consolidated_harness as H
from bounded import static_focus_rules as BASE
from test_host_block_proposal import proposal
from test_installable_bounded import L, S, archive, project


def runtime():
    facts = {"source.py": {"sha256": "observed"}}
    return SimpleNamespace(
        noops=2,
        ledger={"requests": 2, "edits": 1, "post_edit_checks": 1},
        budget=dict(H.BUDGET),
        deadline=time.monotonic() + 10,
        validation=SimpleNamespace(
            status="failed",
            focused_tests={"inputs_unchanged": True, "input_facts": facts},
        ),
        _validation_facts=lambda: facts,
    )


def test_eligibility_preserves_all_budget_objects():
    r = runtime()
    before = (dict(r.ledger), dict(r.budget), r.deadline)
    assert H.noop_recovery_allowed(r)
    assert before == (r.ledger, r.budget, r.deadline)


@pytest.mark.parametrize(
    "case",
    [
        "noops",
        "switched",
        "passed",
        "unchanged",
        "drift",
        "requests",
        "edits",
        "checks",
        "deadline",
    ],
)
def test_no_recovery_without_current_failure_and_remaining_credits(case):
    r = runtime()
    if case == "noops":
        r.noops = 1
    elif case == "switched":
        r.ledger["proposal_profile_switches"] = 1
    elif case == "passed":
        r.validation.status = "passed"
    elif case == "unchanged":
        r.validation.focused_tests["inputs_unchanged"] = False
    elif case == "drift":
        r._validation_facts = lambda: {"source.py": {"sha256": "external-change"}}
    elif case in {"requests", "edits", "checks"}:
        key = "post_edit_checks" if case == "checks" else case
        r.ledger[key] = r.budget[key]
    else:
        r.deadline = time.monotonic() - 1
    assert H.noop_recovery_allowed(r) is False


def test_codec_switch_changes_actual_client_schema_once_only():
    base = C.proposal_rules({"bounded_compatibility_profile": "flat-v1"}, BASE)
    selected = R.adapt(base)
    client = SimpleNamespace(action_schema=base.SCHEMA)
    assert selected.PROMPT == base.PROMPT
    assert selected.recover_noop(client) is True
    assert selected.SCHEMA == client.action_schema == R.BLOCK.SCHEMA
    assert selected.decode is R.BLOCK.decode
    assert base.SCHEMA != selected.SCHEMA
    for key in ("render", "guard", "diagnostics", "shape"):
        assert getattr(selected, key) is getattr(base, key)
    assert selected.recover_noop(client) is False


@pytest.mark.parametrize(
    "case",
    [
        "default",
        "repair",
        "prior-edit",
        "block-noops",
        "request-limit",
        "protocol-limit",
        "passing",
    ],
)
def test_installed_controller_accounting_and_archive(case):
    with tempfile.TemporaryDirectory(prefix="noop-block-control-") as directory:
        root = Path(directory)
        project(root, "labels", "noop-block-" + case)
        config = S.read(root / ".agent/config.json")
        config["bounded_compatibility_profile"] = "flat-v1"
        if case == "request-limit":
            config["experimental_recovery_credits"] = {"requests": 2}
        (root / ".agent/config.json").write_text(json.dumps(config), encoding="utf-8")
        path = root / "src/product/code.py"
        original = path.read_text(encoding="utf-8")
        tree = R.BLOCK.ast.parse(original)
        target = next(n for n in tree.body if isinstance(n, R.BLOCK.ast.FunctionDef))
        old = "".join(
            original.splitlines(keepends=True)[target.lineno - 1 : target.end_lineno]
        )
        correct = L.TASKS["labels"]["reference"]
        bad = correct.replace(
            "    result = dict(defaults)", "    unused = 1\n    result = dict(defaults)"
        )
        whole = lambda text: {"kind": "replacement", "content": text}
        first = original
        actions = []
        if case == "prior-edit":
            actions.append(whole(bad))
            first = bad
        elif case == "protocol-limit":
            actions.extend([{"invalid": True}, {"invalid": True}])
        elif case == "passing":
            path.write_text(
                original.replace(old, correct.rstrip() + "\n"), encoding="utf-8"
            )
            first = path.read_text(encoding="utf-8")
        actions.extend([whole(first), whole(first)])
        if case == "block-noops":
            actions.extend([proposal((old, old)), proposal((old, old))])
        elif case == "prior-edit":
            actions.append(proposal(("    unused = 1\n", "")))
        elif case == "protocol-limit":
            actions.append({"invalid": True})
        else:
            actions.append(proposal((old, correct)))
        replay = root / ".agent/replay.json"
        S.save(replay, actions)
        args = [S.PYTHON, "-B", str(KIT / "benchmarks/noop_block_recovery.py")]
        if case != "default":
            args.append("--noop-block-recovery")
        args += [
            "--mode",
            "unit",
            "--packet",
            ".agent/packet.json",
            "--config",
            ".agent/config.json",
            "--report",
            ".agent/report.json",
            "--review-report",
            ".agent/reviewer.json",
            "--summary",
            ".agent/summary.json",
            "--replay",
            str(replay),
        ]
        result = subprocess.run(
            args, cwd=root, capture_output=True, text=True, timeout=180, check=False
        )
        report = S.read(root / ".agent/report.json")
        ledger = report["consolidated_harness"]
        actual = ledger["actual"]
        assert actual["model_requests"] == 0
        assert actual["initial_checks"] == 1
        assert actual["edits"] == actual["post_edit_checks"]
        assert ledger["budget"]["edits"] == 3
        success = case in {"repair", "prior-edit"}
        assert result.returncode == (0 if success else 2), result.stdout + result.stderr
        if success:
            expected = 2 if case == "prior-edit" else 1
            assert actual["edits"] == expected
            assert actual["requests"] == expected + 2
            assert (
                S.read(root / ".agent/summary.json")["reviewer_input_authenticated"]
                is True
            )
        else:
            assert S.read(root / ".agent/summary.json")["reviewer_started"] is False
        if case in {"default", "request-limit", "passing"}:
            assert not actual.get("proposal_profile_switches")
            assert actual["requests"] == 2
        else:
            assert actual["proposal_profile_switches"] == 1
            requests = [
                S.read(p) for p in sorted(archive(root).glob("proposal-request-*.json"))
            ]
            switched = next(
                i
                for i, p in enumerate(requests)
                if "edits" in p["schema"]["properties"]
            )
            assert switched >= 2
            assert all(
                "content" in p["schema"]["properties"] for p in requests[:switched]
            )
        if case == "block-noops":
            assert actual["noops"] == actual["requests"] == 4
        if case == "protocol-limit":
            assert actual["protocol_recoveries"] == 2
            assert actual["requests"] == 5
