from product.wrapper import display_name


def test_presence_semantics():
    for record, expected in (({}, "unnamed"), ({"name": None}, None), ({"name": ""}, "")):
        before = dict(record)
        assert display_name(record) == expected
        assert record == before
