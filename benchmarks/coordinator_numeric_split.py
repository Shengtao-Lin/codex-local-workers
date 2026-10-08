"""Unit-relevant focused Explorers, not a synthetic six-file success report."""

import argparse
import copy
import json
import sys
from pathlib import Path

import coordinator_numeric_candidate as candidate
from capability_fit import WORK, write
from inherited_context_recovery import digest, read

BASE = WORK / "coordinator-numeric-pilot-4"
SNAPSHOT = WORK / "coordinator-report-baseline-2"
QUESTIONS = {
    "flow": (
        [
            "src/product/entry.py",
            "src/product/target.py",
            "src/product/collector.py",
            "tests/test_target.py",
        ],
        "Locate the current run_batch public function, labelled_receipt and collect_values definitions, and the protected test_batch_error assertion. Likely exact paths are src/product/entry.py, src/product/target.py, src/product/collector.py and tests/test_target.py. One current async call-chain question only. Read those four actual files, cite small real function/assertion ranges, and return locations only, not a semantic diagnosis or predicted validation. No need to investigate normalization or schema in this question.",
    ),
    "parse": (
        ["src/product/schema.py", "src/product/labels.py", "tests/test_target.py"],
        "Locate parse_code in src/product/schema.py, normalize_labels in src/product/labels.py, and the actual integer conversion and malformed-code acceptance assertions in tests/test_target.py test_normalize/test_empty_labels. One parser-definition-and-tests question only. The functions may currently be separate; do not invent a call relationship or assess repairs. Read those three actual files and cite bounded actual definition/assertion ranges. Locations only, no predicted validation. Prefer one reference per path, using one bounded test range containing the relevant assertions.",
    ),
}


def configure():
    original = candidate.numeric.pilot.matrix.MIXED.prepare

    def fresh(case, repetition, config, batch, suite="v1"):
        return original(
            case, repetition, config, batch.replace("numeric2-", "numeric4-"), suite
        )

    candidate.numeric.pilot.matrix.MIXED.prepare = fresh
    candidate.BASE, candidate.SNAPSHOT = BASE, SNAPSHOT
    return candidate.configure()


def root_for(identity):
    return Path(
        next(
            c
            for c in candidate.numeric.pilot.matrix.verify()["cells"]
            if c["id"] == identity
        )["root"]
    )


def explore(identity, mode):
    root = root_for(identity)
    required, question = QUESTIONS[mode]
    config = copy.deepcopy(read(root / ".agent/config.json"))
    config["explorer_required_citation_paths"] = required
    config_path = root / f".agent/{mode}-explorer-config.json"
    write(config_path, config)
    packet = read(root / ".agent/normalize-unit-bound.json")
    candidate.numeric.pilot.matrix.SCOPE.invoke(
        root,
        "explorer",
        [
            sys.executable,
            str(SNAPSHOT / ".local-agents/local-explore.py"),
            "--task",
            question,
            "--task-id",
            packet["task_id"],
            "--config",
            str(config_path),
            "--report",
            str(root / f".agent/{mode}-explorer.json"),
            "--full-report",
        ],
    )
    print(json.dumps(read(root / f".agent/{mode}-explorer.json")))


def adjudicate(identity, mode, summary):
    root = root_for(identity)
    report_path = root / f".agent/{mode}-explorer.json"
    report = read(report_path)
    if (
        report["status"] != "success"
        or report.get("cache", {}).get("hit")
        or report.get("uncertainties")
    ):
        raise ValueError("fresh qualified evidence required")
    paths = set()
    for ref in report["source_refs"]:
        source = root / ref["path"]
        lines = source.read_text(encoding="utf-8").splitlines()
        start, end = ref["start_line"], ref["end_line"]
        if (
            digest(source) != ref["source_hash"]
            or not 1 <= start <= end <= len(lines)
            or ref["quote"] != "\n".join(lines[start - 1 : end])
        ):
            raise ValueError("unverified citation")
        paths.add(ref["path"])
    if not set(QUESTIONS[mode][0]) <= paths or not summary:
        raise ValueError("missing required evidence or Primary semantic adjudication")
    write(
        root / f".agent/{mode}-explorer-primary.json",
        {
            "success": True,
            "report_sha256": digest(report_path),
            "paths": sorted(paths),
            "primary_summary": summary,
            "source": "Primary checked actual source/test quotes",
            "six_file_single_call_credit": False,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "action",
        choices=(
            "prepare",
            "explore",
            "adjudicate",
            "run",
            "check",
            "record",
            "integrate",
        ),
    )
    parser.add_argument("identity", nargs="?")
    parser.add_argument("--mode", choices=("flow", "parse"))
    parser.add_argument("--unit", default="normalize-unit")
    parser.add_argument("--summary")
    args = parser.parse_args()
    configure()
    if args.action == "prepare":
        candidate.numeric.prepare()
        write(
            BASE / "split-registration.json",
            {
                "driver_sha256": digest(Path(__file__)),
                "weekly_used_ceiling": 15,
                "snapshot": str(SNAPSHOT),
                "questions": QUESTIONS,
                "scope_change": "Two distinct unit-relevant questions, both require actual tests; union still covers all six files. No aggregate synthetic Explorer success. One real report selected per unit.",
                "previous_failed_cohorts": [
                    "coordinator-numeric-pilot-1",
                    "coordinator-numeric-pilot-2",
                    "coordinator-numeric-pilot-3",
                ],
                "per_call_limits_changed": False,
                "fixture_model_coder_reviewer_contract_changes": False,
                "readiness": "Four fresh focused Explorer accepts, direct three-unit control chain and seven-test integration before Coordinator mixed testing. Does not qualify single six-path Explorer calls.",
            },
        )
    else:
        if (
            digest(Path(__file__))
            != read(BASE / "split-registration.json")["driver_sha256"]
        ):
            raise ValueError("driver drift")
        if args.action == "explore":
            explore(args.identity, args.mode)
        elif args.action == "adjudicate":
            adjudicate(args.identity, args.mode, args.summary)
        elif args.action == "run":
            for cell in candidate.numeric.pilot.matrix.verify()["cells"]:
                root = Path(cell["root"])
                for mode in QUESTIONS:
                    p = root / f".agent/{mode}-explorer-primary.json"
                    accepted = read(p)
                    if (
                        not accepted["success"]
                        or digest(root / f".agent/{mode}-explorer.json")
                        != accepted["report_sha256"]
                    ):
                        raise ValueError(
                            "four intact accepted Explorer reports required"
                        )
            root = root_for(args.identity)
            mode = "parse" if args.unit == "normalize-unit" else "flow"
            original = candidate.numeric.pilot.read

            def selected(path):
                if Path(path) == root / ".agent/explorer.json":
                    return original(root / f".agent/{mode}-explorer.json")
                return original(path)

            candidate.numeric.pilot.read = selected
            candidate.numeric.pilot.run(args.identity, args.unit)
        elif args.action == "check":
            candidate.numeric.evidence.unit_check(args.identity, args.unit)
        elif args.action == "integrate":
            candidate.numeric.evidence.integrate(args.identity)
        else:
            import qualification_controls as evidence

            evidence.record(args.identity, args.unit, "accept", args.summary)
