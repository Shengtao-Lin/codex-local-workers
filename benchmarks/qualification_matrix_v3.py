"""Known-task requalification with concrete contracts, unchanged protected tests."""

import argparse
import copy
import json
from pathlib import Path

import qualification_controls as CONTROLS
import qualification_matrix as MATRIX
import qualification_matrix_status as STATUS
from capability_fit import WORK, write
from inherited_context_recovery import digest, read

BASE = WORK / "qualification-matrix-3"
SNAPSHOT = WORK / "qualification-matrix-baseline-3"


def scenarios(data):
    improved = copy.deepcopy(data)
    values = {
        "display-default": [
            (
                "named",
                "Present ordinary name returns unchanged.",
                {"input": {"name": "Ada"}, "return_value": "Ada"},
            ),
            (
                "present-empty",
                "A present empty string is NOT absence.",
                {"input": {"name": ""}, "key_present": True, "return_value": ""},
            ),
            (
                "present-none",
                "A present None is NOT absence; return None, never unnamed.",
                {"input": {"name": None}, "key_present": True, "return_value": None},
            ),
            (
                "absent",
                "Only a missing key uses the default; no mutation.",
                {
                    "input": {},
                    "key_present": False,
                    "return_value": "unnamed",
                    "input_unchanged": True,
                },
            ),
        ],
        "public-fields": [
            (
                "filter",
                "Exclude leading-underscore keys, not false-valued public values.",
                {
                    "input": {
                        "_secret": 2,
                        "a": 0,
                        "b": False,
                        "c": None,
                        "": 3,
                        "x_y": 4,
                    },
                    "result": {"a": 0, "b": False, "c": None, "": 3, "x_y": 4},
                },
            ),
            (
                "identity",
                "A new shallow dict retains nested value identity and leaves source unchanged.",
                {
                    "new_mapping": True,
                    "nested_identity_preserved": True,
                    "input_unchanged": True,
                },
            ),
            (
                "empty",
                "Empty mapping returns new empty mapping.",
                {"input": {}, "result": {}},
            ),
        ],
        "lookup-fallback": [
            (
                "successful-none",
                "fetch returns None normally: this is a successful return, not a missing-key exception. Return None unchanged, even when default differs.",
                {
                    "fetch_return_value": None,
                    "exception_raised": False,
                    "return_value": None,
                    "default_used": False,
                    "fetch_calls": 1,
                },
            ),
            (
                "successful-false-values",
                "Successful 0, False, empty string and 7 retain identity, no default.",
                {
                    "fetch_return_values": [0, False, "", 7],
                    "same_result_identity": True,
                    "default_used": False,
                    "fetch_calls": 1,
                },
            ),
            (
                "key-error",
                "A raised KeyError alone selects the supplied default.",
                {
                    "exception_type": "KeyError",
                    "result_is_supplied_default": True,
                    "fetch_calls": 1,
                },
            ),
            (
                "other-error",
                "RuntimeError must propagate as the exact same object, no fallback.",
                {
                    "exception_type": "RuntimeError",
                    "raised_same_instance": True,
                    "default_used": False,
                    "fetch_calls": 1,
                },
            ),
        ],
        "async-first-present": [
            (
                "first",
                "After a None result, False/0/empty string are present and stop later calls.",
                {
                    "preceding_result": None,
                    "present_values": [False, 0, ""],
                    "later_calls": 0,
                    "result_identity_preserved": True,
                },
            ),
            (
                "empty-or-missing",
                "Empty keys or all None return None; retain input and call order.",
                {"result": None, "calls_in_input_order": True, "input_unchanged": True},
            ),
            (
                "error",
                "Propagate the same error and do not visit later keys.",
                {"raised_same_instance": True, "later_calls": 0},
            ),
        ],
        "label-rollup": [
            (
                "normalize",
                "Strip whitespace and remove only resulting empty strings; preserve duplicates/case.",
                {
                    "input": [" A ", "", "  ", "A", "b\t", "0"],
                    "result": ["A", "A", "b", "0"],
                    "input_unchanged": True,
                },
            ),
            (
                "roundtrip",
                "Summary count belongs to normalized labels, not original length.",
                {
                    "input": [" X ", " ", "X"],
                    "result": {"labels": ["X", "X"], "count": 2},
                },
            ),
            (
                "empty",
                "Empty labels yield empty list and count zero.",
                {"input": [], "result": {"labels": [], "count": 0}},
            ),
        ],
    }
    for case in improved["cases"]:
        for unit in case["units"]:
            rows = values.get(case["case_id"])
            if case["case_id"] == "async-receipt":
                if unit["unit_id"] == "collect-unit":
                    unit["contract"] += (
                        " This producer unit owns only collect_values. The unchanged read-only receipt belongs to the separately planned dependent qual-unit and is not yet implemented. A missing receipt count is not a collector violation; genuine collector regressions still require rework. Final consumer and feature integration remain mandatory."
                    )
                    rows = [
                        (
                            "all-values",
                            "Collect every fetched value in order, including None; None is data in this unit, NOT a stop sentinel.",
                            {
                                "fetched_values": [None, False, 0, "", 9],
                                "result": [None, False, 0, "", 9],
                                "types_preserved": True,
                                "input_unchanged": True,
                            },
                        ),
                        (
                            "error",
                            "Error at key one after key zero propagates unchanged, key two not visited.",
                            {
                                "keys": [0, 1, 2],
                                "error_at_key": 1,
                                "call_order": [0, 1],
                                "raised_same_instance": True,
                            },
                        ),
                    ]
                else:
                    rows = [
                        (
                            "roundtrip",
                            "Public run_receipt delegates through receipt to the accepted collector once, retaining all values and matching count.",
                            {
                                "fetched_values": [None, False, 0, ""],
                                "result": {"values": [None, False, 0, ""], "count": 4},
                                "types_preserved": True,
                                "no_retries": True,
                            },
                        ),
                        (
                            "empty",
                            "Empty keys produce count zero and empty values.",
                            {"keys": [], "result": {"values": [], "count": 0}},
                        ),
                        (
                            "error",
                            "Collector error propagates through public entry unchanged; no later calls.",
                            {"raised_same_instance": True, "later_calls": 0},
                        ),
                    ]
            unit["acceptance_scenarios"] = [
                {"id": identity, "text": text, "observables": observables}
                for identity, text, observables in rows
            ]
    return improved


def configure():
    MATRIX.BASE, MATRIX.SNAPSHOT = BASE, SNAPSHOT
    CONTROLS.BASE = WORK / "qualification-controls-3"
    original_corpus = MATRIX.CASES.corpus
    original_prepare = MATRIX.MIXED.prepare
    original_verify = MATRIX.verify

    def new_corpus(template):
        data, oracles = original_corpus(template)
        return scenarios(data), oracles

    def new_prepare(case_id, repetition, config_path, batch, suite="v1"):
        config = read(config_path)
        if case_id in ("label-rollup", "async-receipt"):
            paths = ["tests/test_target.py"]
            paths += (
                ["src/product/labels.py", "src/product/target.py"]
                if case_id == "label-rollup"
                else [
                    "src/product/entry.py",
                    "src/product/target.py",
                    "src/product/collector.py",
                ]
            )
            config["explorer_required_citation_paths"] = paths
        path = BASE / "primary-configs" / f"{case_id}-{batch}-r{repetition}.json"
        write(path, config)
        return original_prepare(
            case_id,
            repetition,
            path,
            "qualification3" if batch == "qualification" else batch + "3",
            suite,
        )

    def new_verify():
        manifest = original_verify()
        policy = read(BASE / "presentation-policy.json")
        for path, sha in policy["drivers"].items():
            if digest(Path(path)) != sha:
                raise ValueError("presentation-policy driver drift")
        return manifest

    MATRIX.CASES.corpus = new_corpus
    MATRIX.MIXED.prepare = new_prepare
    MATRIX.verify = new_verify


def prepare():
    configure()
    MATRIX.prepare()
    previous = read(WORK / "qualification-matrix-2/corpus.json")
    current = read(BASE / "corpus.json")
    same_files = all(
        a["files"] == b["files"]
        for a, b in zip(previous["cases"], current["cases"], strict=True)
    )
    if not same_files:
        raise ValueError("protected fixtures changed")
    write(
        BASE / "presentation-policy.json",
        {
            "classification": "Known-task requalification of a revised Primary packet protocol, not unseen transfer or recovery of original scores",
            "same_sources_and_protected_tests": same_files,
            "scope_or_risk_lowered": False,
            "reference_code_forwarded": False,
            "runtime_changes": "Accepted exact CLI and cache-contract fixes; neither claimed to improve semantics",
            "input_changes": "Concrete normal/error/boundary observables; explicit producer/consumer ownership; existing required-citation mechanism enabled",
            "drivers": {
                str(p): digest(p)
                for p in (
                    Path(__file__).resolve(),
                    Path(MATRIX.MIXED.__file__),
                    Path(STATUS.__file__),
                )
            },
            "weekly_used_ceiling": 70,
            "criterion": "Same six fixed tasks, two fresh rounds, 14 accepted initial units, four independent Explorer successes, both integration chains, eight fresh Reviewer controls. Old failures remain separate and cannot count as candidate success.",
        },
    )
    print(
        json.dumps(
            {
                "same_sources_and_protected_tests": same_files,
                "new_task_batch": "qualification3",
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument(
        "action",
        choices=(
            "prepare",
            "preflight",
            "explore",
            "unit",
            "controls-prepare",
            "control",
            "status",
        ),
    )
    parser.add_argument("identity", nargs="?")
    parser.add_argument("unit", nargs="?", default="qual-unit")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    else:
        configure()
        if args.action == "preflight":
            MATRIX.preflight()
        elif args.action == "explore":
            MATRIX.explore(args.identity)
        elif args.action == "unit":
            MATRIX.run(args.identity, args.unit)
        elif args.action == "controls-prepare":
            CONTROLS.prepare()
        elif args.action == "control":
            CONTROLS.run(args.identity)
        else:
            print(json.dumps(STATUS.status(), indent=2))
