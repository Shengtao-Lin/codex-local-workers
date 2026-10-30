import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from reviewer_reasoning_examples_adapter import EXAMPLES, install


def test_examples_append_only_without_report_or_gate_overrides():
    class Runtime:
        def system_prompt(self):
            return "original trusted instructions"

        def validate_report(self, arguments):
            raise ValueError("original rejection")

    validator = Runtime.validate_report
    install(SimpleNamespace(ReviewerRuntime=Runtime))
    assert Runtime.validate_report is validator
    assert Runtime().system_prompt() == "original trusted instructions\n" + EXAMPLES
    assert "analogy only" in EXAMPLES
    assert "do not invent a longer-duration bug" in EXAMPLES
    assert "Correct implementations must still pass" in EXAMPLES


def test_attribute_presence_counterexample_is_real():
    class Record:
        __iter__ = None

    record = Record()
    assert hasattr(record, "__iter__")
    with pytest.raises(TypeError):
        iter(record)


def test_equal_duration_still_registers_two_independent_guards():
    registrations = []

    async def guard(awaitable, duration):
        registrations.append(duration)
        return await asyncio.wait_for(awaitable, timeout=duration)

    async def composite():
        await asyncio.sleep(0)
        return await guard(asyncio.sleep(0, result=7), 0.5)

    assert asyncio.run(guard(composite(), 0.5)) == 7
    assert registrations == [0.5, 0.5]
