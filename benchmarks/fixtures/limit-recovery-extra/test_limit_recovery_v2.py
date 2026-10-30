"""Readable tie counterexamples and non-timing search-cost acceptance."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import ClassVar

import pytest

from evaluation_harness.contracts import SelectionPolicy
from evaluation_harness.datasets.selection import select_records


@dataclass(eq=False)
class Item:
    tag: str


@pytest.mark.parametrize("order", ("oldest", "newest"))
@pytest.mark.parametrize("limit", (1, 2, 20))
def test_labelled_equal_key_order(order: str, limit: int) -> None:
    values = [Item("A"), Item("B"), Item("C")]
    before = list(values)
    result = select_records(
        values,
        SelectionPolicy(strategy="limit", order=order, limit=limit),
        identity=lambda item: "same",
        timestamp=lambda item: datetime(2026, 1, 1, tzinfo=UTC),
    )
    expected = ["A", "B", "C"] if order == "oldest" else ["C", "B", "A"]
    assert [item.tag for item in result] == expected[:limit], (
        "All primary keys equal: oldest retains A,B,C; "
        "newest reverses to C,B,A before slicing"
    )
    assert values == before


class EqualityKey(str):
    equality_calls: ClassVar[int] = 0

    def __eq__(self, other: object) -> bool:
        type(self).equality_calls += 1
        return super().__eq__(other)

    __hash__ = str.__hash__


@pytest.mark.parametrize("order", ("oldest", "newest"))
def test_position_bookkeeping_has_no_quadratic_equality_scan(order: str) -> None:
    # Unique keys and equal timestamps force tuple list.index scans to compare keys.
    # This supplements ordering-comparison counts; it is not a wall-clock threshold.
    values = [Item(f"{i:04}") for i in range(512)]
    keys = {item.tag: EqualityKey(item.tag) for item in values}
    EqualityKey.equality_calls = 0
    result = select_records(
        values,
        SelectionPolicy(strategy="limit", limit=8, order=order),
        identity=lambda item: keys[item.tag],
        timestamp=lambda item: datetime(2026, 1, 1, tzinfo=UTC),
    )
    calls = EqualityKey.equality_calls
    assert calls < 8192, (
        f"Position bookkeeping performed {calls} equality checks; "
        "repeated linear searches are not bounded selection"
    )
    expected = values[:8] if order == "oldest" else list(reversed(values))[:8]
    assert result == expected
