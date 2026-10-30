from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from evaluation_harness.contracts import SelectionPolicy
from evaluation_harness.datasets.selection import select_records


@dataclass
class Record:
    key: str
    at: datetime


def select(policy: SelectionPolicy) -> list[str]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    records = [Record(str(index), start + timedelta(seconds=index)) for index in range(100)]
    selected = select_records(
        records, policy, identity=lambda item: item.key, timestamp=lambda item: item.at
    )
    return [item.key for item in selected]


def test_random_selection_replays_with_seed() -> None:
    policy = SelectionPolicy(strategy="random", seed=42, limit=10)
    assert select(policy) == select(policy)
    assert len(select(policy)) == 10


def test_percentage_selection_is_stable() -> None:
    policy = SelectionPolicy(strategy="percentage", percentage=25, seed=7)
    assert select(policy) == select(policy)


def test_limit_selection_has_deterministic_order() -> None:
    assert select(SelectionPolicy(strategy="limit", limit=3, order="newest")) == ["99", "98", "97"]
