"""Fixed four-cell Reviewer-only diagnostic; no Coder live credit or rerolls."""

import argparse
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import prepared_task_matrix as M
import reviewer_input_observation as C
import stream_slice_transfer_v3 as TASKS

S, T, P = M.S, M.T, M.P
BATCH = P.I.BASE / "reviewer-input-observation-20261022-2"
CONTROLS = P.I.BASE / "reviewer-input-observation-20261022-1/controls.xml"
ORDER = ["correct-A", "defect-B", "correct-B", "defect-A"]
EXTRA = """
@pytest.mark.parametrize("event", ["{", "}", "{}", "{missing}", "{0!r}", "{value:{width}}", "雪{}"])
@pytest.mark.parametrize("data", ["", "x", "{}\\ny"])
def test_literal_braces_are_data(event, data):
    expected = "event: " + event + "\\n" + "\\n".join("data: " + part for part in data.split("\\n")) + "\\n\\n"
    assert _sse(event, data) == expected
"""


def archive(root, identity):
    return root / ".agent/tasks" / identity["task_id"] / "runs" / identity["run_id"]


def offline_capture(root, row):
    sys.path.insert(0, str(root / ".local-agents"))
    from bounded import capture_fixture_support as F

    entry = F.load(
        root / ".local-agents/local-bounded-review.py", "offline_observation_entry"
    )
    module = F.load(
        root / ".local-agents/reviewer-runtime.py", "offline_observation_runtime"
    )
    run = archive(root, row["identity"])
    config = S.read(run / "review-config.json")
    cls = entry.CAPTURE.install(
        module,
        F.POLICY_PATH,
        config["experimental_capture_policy_sha256"],
        forward_reasoning_effort=True,
    )
    runtime = cls(root, S.read(run / "review-request.json"), config, object())
    runtime.bundle()
    runtime.review_root = root / ".agent/offline-input-control"
    runtime.review_root.mkdir(parents=True, exist_ok=False)
    runtime.deadline = time.monotonic() + 30
    cases = [
        {"args": ["{missing}", "x"], "kwargs": {}},
        {"args": ["", ""], "kwargs": {}},
    ]
    result = C.observe(runtime, cases, module)
    S.save(BATCH / "offline-observations" / (row["label"] + ".json"), result)
    outcomes = [e["outcome"] for e in result["observations"][0]["examples"]]
    assert outcomes[1]["kind"] == "returned"
    assert outcomes[0]["kind"] == (
        "returned" if row["truth"] == "correct" else "raised"
    )
    # No prepare(), no review record and no actual model call during this control.
    assert not (root / ".agent/tasks" / row["identity"]["task_id"] / "reviews").exists()


def prepare(used):
    suites = ET.parse(CONTROLS).getroot().findall("testsuite")
    assert sum(int(s.get("tests", 0)) for s in suites) == 17
    assert all(
        int(s.get(k, 0)) == 0 for s in suites for k in ("errors", "failures", "skipped")
    )
    old = S.read(TASKS.BATCH / "cells.json")["frame-2"]
    origin = Path(old["root"]) / M.TARGET
    assert (
        S.sha(origin)
        == S.read(TASKS.BATCH / "live-results/frame-2/result.json")[
            "final_source_sha256"
        ]
    )
    correct = T.extract(origin, "_sse")
    assert (
        'return "event: {}\\n{}\\n\\n".format(event, "\\n".join(data_lines))' in correct
    )
    defect = correct.replace(
        '.format(event, "\\n".join(data_lines))',
        '.format(event, "\\n".join(data_lines)).format()',
    )
    spec = TASKS.tasks()["frame"]
    spec["reference"] = correct
    spec["private"] += EXTRA
    spec["risk_rationale"] = (
        "Reviewer-only known-correct/seeded-defect controls; event compatibility is high risk. No Coder competence credit."
    )
    material = M.template(BATCH, "frame", spec)
    rows = {}
    for label in ORDER:
        row = M.cell(BATCH, label, "frame", spec, material, Path(__file__))
        root = Path(row["root"])
        row.update(label=label, truth=label.split("-")[0], arm=label[-1])
        proposed = correct if row["truth"] == "correct" else defect
        replay = BATCH / "scripted-coder" / (label + ".json")
        S.save(replay, [{"kind": "replacement", "content": proposed}])
        process = T.run(P.command(root, replay=replay), root, timeout=180)
        S.save(BATCH / "scripted-coder" / (label + "-process.json"), process)
        assert process["exit_code"] == 0, process
        report = S.read(root / ".agent/unit-report.json")
        assert report["consolidated_harness"]["actual"]["model_requests"] == 0
        row["files"][M.TARGET] = S.sha(root / M.TARGET)
        run = archive(root, row["identity"])
        for name in (
            "handoff.json",
            "validation.json",
            "review-request.json",
            "review-config.json",
            "cumulative.diff",
        ):
            row["files"][(run / name).relative_to(root).as_posix()] = S.sha(run / name)
        checks = M.L.checks(root, material[1])
        S.save(BATCH / "truth-checks" / (label + ".json"), checks)
        assert all(c["exit_code"] == 0 for c in checks[1:])
        assert checks[0]["exit_code"] == (0 if row["truth"] == "correct" else 1)
        if row["truth"] == "defect":
            assert "21 failed, 15 passed" in checks[0]["stdout"]
        offline_capture(root, row)
        rows[label] = row
    assert rows["correct-A"]["files"][M.TARGET] == rows["correct-B"]["files"][M.TARGET]
    assert rows["defect-A"]["files"][M.TARGET] == rows["defect-B"]["files"][M.TARGET]
    S.save(BATCH / "cells.json", rows)
    S.save(
        BATCH / "registration.json",
        {
            "feature_id": "reviewer-bounded-input-observation",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "owned_contract_ids": [
                "unchanged-frame-contract",
                "fixed-execution-authority",
                "shared-reviewer-budget",
                "no-semantic-reroll",
            ],
            "dependencies": [
                "stream-slice-transfer-20261022-3/frame-2",
                "checked-research-20261022-1",
            ],
            "registered": 4,
            "order": ORDER,
            "question": "Does one bounded model-selected actual-input observation phase reduce a concrete false-positive without hiding a real defect?",
            "A": "Unchanged installed flat-v1 contract-first Reviewer.",
            "B": "Same Reviewer plus one SELECT_CASES phase, at most two two-string calls to the same pinned _sse, automatically executed using existing capture producer. Evidence appended before first final report; no adjudicator/gold answer.",
            "exposure": "Historical correct frame2 plus controlled double-format defect. Known diagnostic controls, not holdout/migration or Coder/full-chain success.",
            "common_budget": "Muse ctx24576, max16 total requests/4 shared errors/4096 output per request/600s, load outside invocation but outer1080s per cell; batch5400s. Selection and protocol recovery charged. No semantic report rerolls.",
            "additional_B_execution": "Zero to two fixed calls in one pinned subprocess, timeout20s within same600s, strings<=128; no arbitrary shell/code/paths/functions. Original configured observations and checks unchanged.",
            "gate": "Report verdict plus concrete supporting finding must match both truths. Any false acceptance fails candidate. Benefit requires improvement over A; equal scores do not establish benefit. Four cells are feasibility only, no production qualification.",
            "continue_rule": "Ordinary incorrect verdict/protocol failure retains failure and continues remaining fixed cells. Safety, input drift, infrastructure or deadline stops; remaining NOT_RUN. No additional draws on same evidence.",
            "controls": "17 offline protocol/one-shot controls, installed scripted archive/authentication for4cells, real capture checked against known returned/raised behavior, source/protected hash verification. Zero live Coder calls.",
            "worker_isolation": "Private21 brace cases and expected control labels/results are outside Worker read scope and input. No old false-positive report or successful answer supplied to Reviewer.",
            "Primary_cost": "One-time prototype and fixture preparation; repeated task cost includes contract/tests and final adjudication. Cloud tokens and active time unknown. No savings claim.",
            "model": "meta/muse-glimmer",
            "single_residency": True,
            "weekly_used_start": used,
            "weekly_cap": None,
            "pins": M.pins(
                BATCH,
                Path(__file__),
                Path(C.__file__),
                CONTROLS,
                material[1],
            ),
            "not_changed": "Production runtime/defaults, acceptance policy, model, Coder/Explorer/Coordinator, previous results; no sibling writes/commit/push.",
        },
    )
    print("Four Reviewer-only paired cells frozen; zero live calls")


def run(used):
    reg, rows = S.read(BATCH / "registration.json"), S.read(BATCH / "cells.json")
    assert all(S.sha(p) == digest for p, digest in reg["pins"].items())
    S.save(BATCH / "live-start.json", {"weekly_used": used, "epoch": time.time()})
    started = time.monotonic()
    for label in ORDER:
        assert time.monotonic() - started < 5400
        row, dest = rows[label], BATCH / "live-results" / label
        root = Path(row["root"])
        assert all(S.sha(root / p) == d for p, d in row["files"].items())
        run_root = archive(root, row["identity"])
        entry = (
            root / ".local-agents/local-bounded-review.py"
            if row["arm"] == "A"
            else Path(C.__file__)
        )
        command = [
            S.PYTHON,
            "-B",
            entry,
            "--request",
            run_root / "review-request.json",
            "--config",
            run_root / "review-config.json",
            "--report",
            root / ".agent/live-reviewer-report.json",
        ]
        cell_start = time.monotonic()
        process = T.run(command, root, timeout=1080)
        S.save(
            dest / "process.json", {**process, "seconds": time.monotonic() - cell_start}
        )
        changed = [p for p, d in row["files"].items() if S.sha(root / p) != d]
        report_path = root / ".agent/live-reviewer-report.json"
        report = S.read(report_path) if report_path.exists() else {}
        review_root = (
            root
            / ".agent/tasks"
            / row["identity"]["task_id"]
            / "reviews"
            / ("auto-" + row["identity"]["run_id"])
        )
        budget = (
            S.read(review_root / "contract-first-budget.json")
            if (review_root / "contract-first-budget.json").exists()
            else None
        )
        S.save(
            dest / "result.json",
            {
                "decision": report.get("decision", "NOT_REPORTED"),
                "findings": report.get("findings"),
                "budget": budget,
                "protected_drift": changed,
                "truth": row["truth"],
                "arm": row["arm"],
                "model": "meta/muse-glimmer",
                "primary_judgment": "PENDING",
                "coder_model_calls": 0,
                "strict_full_chain_credit": False,
            },
        )
        print(
            label,
            report.get("decision", "NOT_REPORTED"),
            "Primary judgment pending",
            flush=True,
        )
        if changed or report.get("infra_failure") or not report:
            print("Stop on drift/infrastructure/missing report; no rerun", flush=True)
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "run"])
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    prepare(args.weekly_used) if args.mode == "prepare" else run(args.weekly_used)
