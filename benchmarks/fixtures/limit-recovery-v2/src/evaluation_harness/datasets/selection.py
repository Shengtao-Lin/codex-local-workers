"""Deterministic selection policies."""

from __future__ import annotations

import hashlib
import random
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import TypeVar

from evaluation_harness.contracts import SelectionPolicy

T = TypeVar("T")


def select_records(
    records: Sequence[T],
    policy: SelectionPolicy,
    *,
    identity: Callable[[T], str],
    timestamp: Callable[[T], datetime],
) -> list[T]:
    eligible = list(records)
    if policy.strategy == "all":
        return eligible
    if policy.strategy == "limit":
        ordered = sorted(eligible, key=lambda item: (timestamp(item), identity(item)))
        if policy.order == "newest":
            ordered.reverse()
        return ordered[: policy.limit]
    if policy.strategy == "random":
        ordered = sorted(eligible, key=identity)
        random.Random(policy.seed).shuffle(ordered)
        return ordered[: policy.limit]
    threshold = int((policy.percentage or 0) * 100)
    return [
        item
        for item in eligible
        if int.from_bytes(
            hashlib.sha256(f"{policy.seed}:{identity(item)}".encode()).digest()[:8], "big"
        )
        % 10_000
        < threshold
    ]
