"""Two frozen semantic controls; scripted Coder, unchanged fresh Reviewer."""

import argparse
import time
from pathlib import Path

import bounded_evidence_readiness as READY
import bounded_evidence_support as S
import bounded_evidence_tasks as T
import capture_fixture_support as F
from feedback_recovery_trial import BATCH, OLD


def prepare():
    cells = S.read(OLD / "cells-v4.json")
    seed = cells["T3-A2"]
    old = Path(seed["root"])
    archive = old / ".agent/tasks/evidence-T3/runs/bounded-20261018-T3-A2"
    preimages = {r["path"]: r for r in S.read(archive / "preimages.json")}
    rows = {}
    for label in ("negative", "positive"):
        root = BATCH / "reviewer-controls" / label / "isolated"
        for name, sha in seed["files"].items():
            source = old / name
            if S.sha(source) != sha:
                source = old / preimages[name]["archive_path"]
            assert S.sha(source) == sha
            dest = root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(source.read_bytes())
        identity = {
            "task_id": "receipt-review-T3",
            "unit_id": "receipt-review-T3",
            "run_id": "receipt-review-" + label,
        }
        for relative in (".agent/packet.json", F.POLICY_PATH):
            path = root / relative
            value = S.read(path)
            if relative == F.POLICY_PATH:
                value["identity"] = identity
            else:
                value.update(identity)
            path.write_text(__import__("json").dumps(value, indent=2), encoding="utf-8")
        target = (
            old / "src/product/code.py"
            if label == "negative"
            else OLD / "task-preparation-v4/private/T3/reference.py"
        )
        worker = F.load(
            root / ".local-agents/worker-runtime.py", "review_control_symbol"
        )
        block = worker.SINGLE_FUNCTION.target(
            target.read_text(encoding="utf-8"), "_usage"
        )[3]
        runtime, _host = READY.runtime_at(root, [{"replacement": block}])
        report = runtime.run()
        assert report["status"] == "validation_passed_pending_review", report
        gate = F.load(root / ".local-agents/local-unit.py", "review_control_gate")
        authenticated = gate.verify_handoff(root, report, config=runtime.config)
        request = {
            "schema_version": 1,
            **authenticated,
            "review_id": "control-" + label,
            "execution_protocol": report["execution_protocol"],
        }
        config = {
            **runtime.config,
            "reviewer_compact_report": True,
            "reviewer_evidence_state": True,
        }
        S.save(root / ".agent/control-request.json", request)
        S.save(root / ".agent/control-config.json", config)
        command = [
            S.PYTHON,
            "-B",
            S.KIT / "benchmarks/reviewer_capture_entry.py",
            "--runtime-dir",
            root / ".local-agents",
            "--capture-policy",
            F.POLICY_PATH,
            "--capture-policy-sha256",
            S.sha(root / F.POLICY_PATH),
            "--request",
            root / ".agent/control-request.json",
            "--config",
            root / ".agent/control-config.json",
            "--report",
            root / ".agent/control-report.json",
        ]
        inspection = T.run([*command, "--inspect-only"], root)
        # inspect-only writes the selected report path; use distinct live output.
        command[-1] = root / ".agent/control-live-report.json"
        assert inspection["exit_code"] == 0, inspection
        S.save(root.parent / "inspection.json", inspection)
        rows[label] = {
            "root": str(root),
            "argv": [str(x) for x in command],
            "files": {
                p.relative_to(root).as_posix(): S.sha(p)
                for p in root.rglob("*")
                if p.is_file()
            },
            "expected": "rework/escalate with null-conversion evidence"
            if label == "negative"
            else "pass_to_primary",
            "scripted_coder": True,
            "model_coder_calls": 0,
        }
    S.save(
        BATCH / "reviewer-controls/registration.json",
        {
            "order": ["negative", "positive"],
            "rows": rows,
            "pins": {
                str(Path(__file__)): S.sha(__file__),
                **S.read(OLD / "registration-v2-draft.json")["pins"],
            },
            "no_resampling": True,
            "weekly_stop": 20,
            "seconds_each": 900,
            "scope": "Exposed controls only; no new Reviewer candidate, no new holdout credit",
        },
    )


def run(label, used, at):
    assert 0 <= used < 20 and 0 <= time.time() - at <= 120
    reg = S.read(BATCH / "reviewer-controls/registration.json")
    assert all(S.sha(p) == sha for p, sha in reg["pins"].items())
    row = reg["rows"][label]
    root = Path(row["root"])
    assert all(S.sha(root / p) == sha for p, sha in row["files"].items())
    start = BATCH / "reviewer-controls" / label / "start.json"
    S.save(start, {"epoch": time.time(), "weekly_used": used, "observed_at": at})
    result = T.run(row["argv"], root, timeout=900)
    S.save(start.with_name("result.json"), result)
    print(label, "exit", result["exit_code"])


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["prepare", "run"])
    p.add_argument("--label", choices=["negative", "positive"])
    p.add_argument("--weekly-used", type=int)
    p.add_argument("--usage-observed-at", type=float)
    args = p.parse_args()
    if args.mode == "prepare":
        prepare()
        print("Two authenticated controls prepared; zero model requests")
    else:
        run(args.label, args.weekly_used, args.usage_observed_at)
