import pytest

from greeting import build_greeting


def test_build_greeting_trims_name_and_adds_punctuation() -> None:
    assert build_greeting("  Ada  ") == "Hello, Ada!"


@pytest.mark.parametrize("name", ["", "   ", "\t"])
def test_build_greeting_rejects_blank_name(name: str) -> None:
    with pytest.raises(ValueError, match="name must not be blank"):
        build_greeting(name)
