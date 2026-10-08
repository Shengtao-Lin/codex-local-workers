"""Pinned external wrap repair: three fresh paired rounds, no automatic acceptance."""

import argparse
import copy
import json
import sys
import urllib.request
from pathlib import Path

import coordinator_label_evidence as evidence
import coordinator_label_pilot as pilot
import coordinator_numeric_split as split
from capability_fit import WORK, load_worker, write
from inherited_context_recovery import digest, read

BASE = WORK / "coordinator-quixbugs-wrap-1"
SNAPSHOT = WORK / "coordinator-report-baseline-2"
COMMIT = "4257f44b0ff1181dedaedee6a447e133219fcebf"
UPSTREAM = f"https://raw.githubusercontent.com/jkoppel/QuixBugs/{COMMIT}/"
QUESTION = (
    "Locate wrap in src/product/target.py and its actual contract comment, and the "
    "protected official-case and boundary assertions in tests/test_target.py. Read "
    "these two actual files and cite bounded real definition/test ranges. One "
    "implementation/test localization question only; no repairs or predicted validation."
)
TESTS = """import json
import random
import sys
from pathlib import Path

from product.target import wrap


def bounded_wrap(text, cols):
    previous = sys.gettrace()
    steps = 0
    filename = wrap.__code__.co_filename

    def guard(frame, event, arg):
        nonlocal steps
        if frame.f_code.co_filename == filename and event == "line":
            steps += 1
            if steps > 10000:
                raise RuntimeError("wrap did not make bounded progress")
        return guard

    sys.settrace(guard)
    try:
        return wrap(text, cols)
    finally:
        sys.settrace(previous)


def test_official_cases():
    path = Path(__file__).with_name("official-wrap.json")
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(cases) == 5
    for arguments, expected in cases:
        assert bounded_wrap(*arguments) == expected


def test_empty_and_short():
    assert bounded_wrap("", 4) == [""]
    assert bounded_wrap("cat", 4) == ["cat"]


def test_exact_width():
    assert bounded_wrap("abcd", 4) == ["abcd"]


def test_long_word():
    assert bounded_wrap("abcdefgh", 3) == ["abc", "def", "gh"]


def test_spaces_preserved():
    assert bounded_wrap("ab cd ef", 5) == ["ab cd", " ef"]
    text = "ab  cd  "
    result = bounded_wrap(text, 5)
    assert "".join(result) == text
    assert all(len(line) <= 5 for line in result)


def test_narrow_leading_space_progress():
    assert bounded_wrap(" ab", 1) == [" ", "a", "b"]
    assert bounded_wrap("  abc", 2) == [" ", " a", "bc"]


def test_seeded_invariants():
    rng = random.Random(17)
    for _ in range(80):
        text = "".join(rng.choice("abc  ") for _ in range(rng.randrange(40)))
        cols = rng.randrange(1, 10)
        original = text
        result = bounded_wrap(text, cols)
        assert isinstance(result, list) and result
        assert all(isinstance(line, str) and len(line) <= cols for line in result)
        assert "".join(result) == original and text == original
"""


def case():
    source = (BASE / "upstream/python_programs/wrap.py").read_text(encoding="utf-8")
    cases = (BASE / "upstream/json_testcases/wrap.json").read_text(encoding="utf-8")
    return {
        "case_id": "quixbugs-wrap",
        "origin": "pinned QuixBugs wrap with separately labelled supplemental boundaries",
        "goal": "Repair bounded text wrapping while preserving every input character and the original benchmark outcomes.",
        "feature_risk": "medium",
        "integration_risk": "medium",
        "files": {
            "src/product/target.py": source,
            "tests/test_target.py": TESTS,
            "tests/official-wrap.json": cases,
        },
        "units": [
            {
                "unit_id": "normalize-unit",
                "risk": "medium",
                "dependencies": [],
                "path": "src/product/target.py",
                "anchor": "wrap",
                "tests": [
                    f"tests/test_target.py::{name}"
                    for name in (
                        "test_official_cases",
                        "test_empty_and_short",
                        "test_exact_width",
                        "test_long_word",
                        "test_spaces_preserved",
                        "test_narrow_leading_space_progress",
                        "test_seeded_invariants",
                    )
                ],
                "contract": (
                    "For text string and positive integer cols, wrap returns a nonempty ordered list "
                    "of strings of length at most cols, preserving all original characters/spaces "
                    "when concatenated. Match all five protected official vectors. Use spaces as "
                    "word boundaries where possible, splitting a word only when necessary. "
                    "Empty text returns ['']; text at or below cols returns [text]. Never discard "
                    "the final remainder. Always make progress, including leading spaces and "
                    "cols=1; no unbounded loop. Preserve input and do not change the test tracer "
                    "or host tracing state. Nonpositive width is outside the upstream precondition; "
                    "no new public API/security/persistence/dependency changes. Existing source "
                    "is the real benchmark defect, not a Primary-injected mutation."
                ),
                "acceptance_scenarios": [
                    {
                        "id": "normal",
                        "text": "All official vectors plus space-preserving short wrapping.",
                        "observables": {"official_vectors": 5, "lossless": True},
                    },
                    {
                        "id": "boundary",
                        "text": "Empty, exact width, long word, leading spaces and narrow width terminate.",
                        "observables": {
                            "empty": [""],
                            "narrow_input": " ab",
                            "cols": 1,
                        },
                    },
                    {
                        "id": "progress",
                        "text": "Deterministic generated valid inputs terminate and preserve characters.",
                        "observables": {"seed": 17, "samples": 80},
                    },
                ],
            }
        ],
    }


def configure():
    pilot.BASE, pilot.SNAPSHOT, pilot.fixture = BASE, SNAPSHOT, sys.modules[__name__]
    split.BASE, split.SNAPSHOT = BASE, SNAPSHOT
    split.QUESTIONS = {
        "flow": (["src/product/target.py", "tests/test_target.py"], QUESTION)
    }
    return pilot.configure()


def prepare():
    contract = configure()
    pilot.matrix.SCOPE.FA.LAYER.verify_hashes(
        SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"]
    )
    BASE.mkdir(exist_ok=False)
    files = (
        "python_programs/wrap.py",
        "correct_python_programs/wrap.py",
        "python_testcases/test_wrap.py",
        "python_testcases/load_testdata.py",
        "json_testcases/wrap.json",
        "conftest.py",
        "LICENSE",
        "README.md",
    )
    hashes = {}
    for relative in files:
        with urllib.request.urlopen(UPSTREAM + relative, timeout=40) as response:
            data = response.read()
        path = BASE / "upstream" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(data)
        hashes[relative] = digest(path)
    definition = (BASE / "upstream/correct_python_programs/wrap.py").read_text(
        encoding="utf-8"
    )
    reference = definition.replace("if end == -1:", "if end <= 0:")
    write(
        BASE / "upstream-provenance.json",
        {
            "commit": COMMIT,
            "url": UPSTREAM,
            "files": hashes,
            "official_correct_code_hidden": True,
            "official_expected_vectors": 5,
            "license": "upstream/LICENSE",
            "supplemental_reference_change": "Primary progress fix when rfind returns zero; not upstream benchmark ground truth",
            "score_claim": "task-level diagnostic only, no benchmark leaderboard/generalization claim",
        },
    )
    write(BASE / "corpus.json", {"cases": [case()]})
    write(
        BASE / "primary-oracles.json",
        {
            "quixbugs-wrap": {
                "reference": {"src/product/target.py": reference},
                "mutants": [
                    {"src/product/target.py": case()["files"]["src/product/target.py"]},
                    {"src/product/target.py": definition},
                ],
            }
        },
    )
    config = read(
        WORK
        / "coordinator-datetime-transfer-2/runs/v1/datetime1-control/private-datetime-round-1/.agent/config.json"
    )
    cells, checks = [], []
    for round_number in (1, 2, 3):
        for arm in ("control", "coordinator"):
            settings = copy.deepcopy(config)
            settings["coordinator_enabled"] = arm == "coordinator"
            settings["explorer_required_citation_paths"] = split.QUESTIONS["flow"][0]
            config_path = BASE / f"{arm}-r{round_number}-config.json"
            write(config_path, settings)
            # Distinct batch encodes all three rounds; MIXED's existing two-round
            # helper is reused without editing its frozen registration contract.
            root = Path(
                pilot.matrix.MIXED.prepare(
                    "quixbugs-wrap", 1, config_path, f"quixwrap1-r{round_number}-{arm}"
                )["root"]
            )
            plan = read(root / ".agent/feature-plan.json")
            packet = read(root / ".agent/normalize-unit-reference.json")
            packet["primary_plan_sha256"] = contract.authority_fingerprint(plan)
            packet = contract.validate_unit_packet(plan, packet)
            load_worker(SNAPSHOT).validate_packet(packet)
            write(root / ".agent/normalize-unit-bound.json", packet)
            paths = [
                *case()["files"],
                "pyproject.toml",
                ".agent/config.json",
                ".agent/feature-plan.json",
                ".agent/normalize-unit-bound.json",
            ]
            cells.append(
                {
                    "id": f"{arm}-r{round_number}",
                    "arm": arm,
                    "round": round_number,
                    "case": "quixbugs-wrap",
                    "root": str(root),
                    "units": ["normalize-unit"],
                    "hashes": {p: digest(root / p) for p in paths},
                }
            )
            checks.append(
                pilot.matrix.SCOPE.FA.LAYER.command(
                    root, [sys.executable, "-m", "ruff", "check", "src", "tests"]
                )
            )
    write(
        BASE / "manifest.json",
        {
            "runtime": str(SNAPSHOT),
            "cells": cells,
            "drivers": {
                str(Path(p).resolve()): digest(Path(p))
                for p in (__file__, pilot.__file__, evidence.__file__, split.__file__)
            },
        },
    )
    write(
        BASE / "registration.json",
        {
            "weekly_used_start": 7,
            "weekly_used_ceiling": 15,
            "primary_active_seconds": None,
            "order": [
                "control-r1",
                "coordinator-r1",
                "coordinator-r2",
                "control-r2",
                "control-r3",
                "coordinator-r3",
            ],
            "functional_risk": "medium",
            "qualification_risk": "high",
            "risk_rationale": "Isolated algorithm benchmark, no public compatibility deployment; Primary owns qualification authority and contracts",
            "models_and_budgets_changed": False,
            "initial_static_checks": checks,
            "project_check_policy": "upstream has no required Ruff policy; explicit fixture E4/E7/E9/F+format, not fabricated project requirements",
            "official_test_adapter": "five original JSON vectors retained byte-for-byte, equivalent loop assertions in protected test_official_cases; original test/loader/config archived separately",
            "extra_fixture_checker": "bounded CPython line tracing prevents bad benchmark/reference loops; readonly tests restore prior tracing state",
            "explorer_success_required_separately": True,
            "measurements": "local elapsed measured; no exact cloud tokens or whole-session Primary active time claimed; manual review observations recorded by Primary",
        },
    )
    if not all(item["exit"] == 0 for item in checks):
        raise ValueError("fixture baseline static checks failed")
    pilot.matrix.preflight()
    print(
        json.dumps({"prepared_cells": len(cells), "commit": COMMIT, "base": str(BASE)})
    )


def run(identity):
    configure()
    root = split.root_for(identity)
    adjudication = read(root / ".agent/flow-explorer-primary.json")
    if (
        not adjudication["success"]
        or digest(root / ".agent/flow-explorer.json") != adjudication["report_sha256"]
    ):
        raise ValueError("fresh Explorer requires Primary acceptance")
    original = pilot.read

    def selected(path):
        return original(
            root / ".agent/flow-explorer.json"
            if Path(path) == root / ".agent/explorer.json"
            else path
        )

    pilot.read = selected
    pilot.run(identity, "normalize-unit")


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
    parser.add_argument("--summary")
    args = parser.parse_args()
    configure()
    if args.action == "prepare":
        prepare()
    else:
        pilot.matrix.verify()
        if args.action == "explore":
            split.explore(args.identity, "flow")
        elif args.action == "adjudicate":
            split.adjudicate(args.identity, "flow", args.summary)
        elif args.action == "run":
            run(args.identity)
        elif args.action == "check":
            evidence.unit_check(args.identity, "normalize-unit")
        elif args.action == "integrate":
            evidence.integrate(args.identity)
        else:
            import qualification_controls

            qualification_controls.record(
                args.identity, "normalize-unit", "accept", args.summary
            )
