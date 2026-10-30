"""Frozen real-task fixture qualification without depending on ignored live logs."""

import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "benchmarks/fixtures/limit-recovery-v3"


def test_limit_recovery_frozen_closure_and_protected_tests():
    provenance = json.loads((FROZEN / "provenance.json").read_text(encoding="utf-8"))
    assert len(provenance["sibling_current_hashes"]) == 29
    assert len(provenance["files"]) == 31
    for path, expected in provenance["files"].items():
        assert hashlib.sha256((FROZEN / path).read_bytes()).hexdigest() == expected
    assert "tests/unit/test_limit_selection_acceptance.py" in provenance["files"]
    assert "tests/unit/test_limit_recovery.py" in provenance["files"]


def test_additional_tests_cover_equal_occurrences_and_position_cost():
    text = (FROZEN / "tests/unit/test_limit_recovery.py").read_text(encoding="utf-8")
    tree = ast.parse(text)
    functions = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(functions) == 2
    assert "8192" in text and "512" in text
    assert "oldest" in text and "newest" in text
    assert "eq=False" in text
    assert "__eq__" in text


def test_static_recovery_is_not_algorithm_credit():
    text = (ROOT / "benchmarks/limit_static_trial.py").read_text(encoding="utf-8")
    assert (
        "Static recovery only, never original clean-start optimization success" in text
    )
    assert "start_source=START" in text
    assert "semantic-shaped-1" in text


def test_reference_is_not_in_frozen_worker_readable_closure():
    paths = json.loads((FROZEN / "provenance.json").read_text(encoding="utf-8"))[
        "files"
    ]
    assert not any("oracle" in path or "reference" in path for path in paths)


def test_executable_recipe_matches_legacy_on_unrelated_jobs():
    tree = ast.parse(
        (ROOT / "benchmarks/limit_recipe_trial.py").read_text(encoding="utf-8")
    )
    example = next(
        n.value.value
        for n in tree.body
        if isinstance(n, ast.Assign)
        and isinstance(n.value, ast.Constant)
        and any(isinstance(t, ast.Attribute) and t.attr == "EXAMPLE" for t in n.targets)
    )
    code = (
        "import heapq\n"
        + example.split("import heapq\n", 1)[1].split("This evaluates", 1)[0]
    )
    namespace = {}
    # Compile only the checked-in literal example, not model or log output.
    exec(compile(code, "unrelated-worked-example", "exec"), namespace)  # noqa: S102
    jobs = [(-2, "b", "red"), (-2, "a", "blue"), (-2, "b", "green"), (3, "a", "yellow")]
    for newest in (False, True):
        for count in (1, 2, 4, 20):
            events = []

            def priority(job, events=events):
                events.append(("priority", job[2]))
                return job[0]

            def queue(job, events=events):
                events.append(("queue", job[2]))
                return job[1]

            actual = namespace["choose_jobs"](jobs, count, newest, priority, queue)
            expected = sorted(jobs, key=lambda row: row[:2])
            if newest:
                expected.reverse()
            assert actual == expected[:count]
            assert all(a is b for a, b in zip(actual, expected[:count], strict=True))
            assert events == [
                (kind, job[2]) for job in jobs for kind in ("priority", "queue")
            ]
