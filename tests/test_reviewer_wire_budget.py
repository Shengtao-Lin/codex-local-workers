import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from reviewer_wire_budget_adapter import trim_wire


def test_wire_budget_preserves_contract_current_state_and_recent_evidence():
    initial = [
        {"role": "system", "content": "contract"},
        {"role": "user", "content": "LOCAL_REVIEW_INPUT\npacket"},
    ]
    dialogue = [
        item
        for number in range(10)
        for item in (
            {"role": "assistant", "content": str(number) + "x" * 200},
            {"role": "user", "content": "OBSERVATION\n" + str(number) + "y" * 200},
        )
    ]
    state = {"role": "user", "content": "CURRENT_STATE " + "z" * 200}
    messages = [*initial, *dialogue, state]
    frozen = copy.deepcopy(messages)
    kept, removed = trim_wire(messages, [], 1200, 100, 100)
    assert removed > 0
    assert kept[:2] == initial
    assert kept[-11:] == [*dialogue[-10:], state]
    assert messages == frozen
    assert (sum(len(item["content"]) for item in kept) + 2 + 3) // 4 <= 900


def test_irreducible_oversize_preserves_evidence_and_leaves_preflight_authority():
    messages = [
        {"role": "system", "content": "x" * 10000},
        {"role": "user", "content": "contract"},
    ]
    kept, removed = trim_wire(messages, [], 100, 10, 10)
    assert kept == messages
    assert removed == 0


def test_actual_native_schema_is_included_in_request_budget():
    messages = [
        {"role": "system", "content": "contract"},
        {"role": "user", "content": "packet"},
    ]
    messages += [
        {
            "role": "assistant" if index % 2 == 0 else "user",
            "content": "action" if index % 2 == 0 else "OBSERVATION\nevidence",
        }
        for index in range(14)
    ]
    assert trim_wire(messages, [], 1200, 100, 100)[1] == 0
    assert trim_wire(messages, [{"schema": "x" * 4000}], 1200, 100, 100)[1] == 4
