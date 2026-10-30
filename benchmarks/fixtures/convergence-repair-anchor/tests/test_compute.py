from product.core import evaluate
from product.entry import compute


def test_compute():
    assert compute(3) == 6


def test_compute_core():
    assert evaluate(-2) == -4


def test_compute_boundary():
    assert compute(None) == 0
    assert evaluate(0) == 0
