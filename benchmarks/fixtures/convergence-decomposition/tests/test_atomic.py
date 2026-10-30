from product.entry import compute


def test_atomic_input_output_boundary():
    assert compute(" 3 ") == 6
    assert compute(" -2 ") == -4
    assert compute(0) == 0
