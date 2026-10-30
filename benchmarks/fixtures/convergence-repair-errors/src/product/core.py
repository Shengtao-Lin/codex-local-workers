def parse_count(value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("count must be integer")
    if value < 0:
        raise ValueError("invalid count")
    return value
