import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from reviewer_retained_wire_adapter import trim_wire
from reviewer_retained_wire_v2_adapter import trim_wire as trim_real_handoff


def test_retained_source_precedes_old_dialogue_with_original_budget():
    initial = [
        {"role": "system", "content": "contract"},
        {"role": "user", "content": "LOCAL_REVIEW_INPUT\n" + "s" * 12000},
    ]
    dialogue = [
        item
        for number in range(10)
        for item in (
            {"role": "assistant", "content": str(number) + "a" * 1000},
            {"role": "user", "content": "OBSERVATION\n" + str(number) + "o" * 1000},
        )
    ]
    state = {"role": "user", "content": "CURRENT_STATE " + "c" * 1000}
    messages = [*initial, *dialogue, state]
    frozen = copy.deepcopy(messages)
    kept, removed = trim_wire(messages, [], 5600, 100, 100)
    assert removed > 0
    assert kept[:2] == initial
    assert kept[-7:] == [*dialogue[-6:], state]
    assert messages == frozen
    assert (sum(len(item["content"]) for item in kept) + 5) // 4 <= 4860


def test_fixed_source_oversize_cannot_be_silently_discarded():
    messages = [
        {"role": "system", "content": "c"},
        {"role": "user", "content": "LOCAL_REVIEW_INPUT\n" + "s" * 10000},
    ]
    assert trim_wire(messages, [], 100, 10, 10) == (messages, 0)


def test_real_handoff_can_trim_to_last_exchange_without_losing_fixed_source():
    initial = [
        {"role": "system", "content": "contract"},
        {"role": "user", "content": "LOCAL_REVIEW_INPUT\n" + "s" * 12000},
    ]
    dialogue = [
        item
        for number in range(10)
        for item in (
            {"role": "assistant", "content": str(number) + "a" * 1000},
            {"role": "user", "content": "OBSERVATION\n" + str(number) + "o" * 1000},
        )
    ]
    state = {"role": "user", "content": "CURRENT_STATE " + "c" * 1000}
    messages = [*initial, *dialogue, state]
    frozen = copy.deepcopy(messages)
    old, _ = trim_wire(messages, [], 4500, 100, 100)
    assert (sum(len(item["content"]) for item in old) + 5) // 4 > 4300
    kept, removed = trim_real_handoff(messages, [], 4500, 100, 100)
    assert removed == 18
    assert kept == [*initial, *dialogue[-2:], state]
    assert messages == frozen
    assert (sum(len(item["content"]) for item in kept) + 5) // 4 <= 3870
