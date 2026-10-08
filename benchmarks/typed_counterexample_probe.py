"""Trusted executable observations; no source editing or reference implementation."""

import importlib
import json
import sys


class Child(int):
    pass


def observe(function, args, expected):
    try:
        value = function(*args)
        actual = {"kind": "return", "repr": repr(value), "type": type(value).__name__}
    except Exception as error:
        actual = {"kind": "raise", "type": type(error).__name__}
    valid = actual["kind"] == expected["kind"]
    if expected["kind"] == "raise":
        valid = valid and actual.get("type") == expected["type"]
    else:
        valid = valid and actual.get("repr") == expected["repr"]
    return (
        None
        if valid
        else {
            "function": function.__name__,
            "arguments": [
                {"repr": repr(a), "type": f"{type(a).__module__}.{type(a).__name__}"}
                for a in args
            ],
            "expected": expected,
            "actual": actual,
        }
    )


def probe(case):
    target = importlib.import_module("product.target")
    checks = []
    raised = {"kind": "raise", "type": "ValueError"}
    if case == "window-bounds":
        for items in ([], [1, 2]):
            for value in (True, False, Child(1), -1, 1.0, None):
                checks.append((target.window, (items, value, 1), raised))
                checks.append((target.window, (items, 0, value), raised))
        checks.append(
            (target.window, ([1, 2, 3], 1, 9), {"kind": "return", "repr": "[2, 3]"})
        )
    elif case == "port-roundtrip":
        options = importlib.import_module("product.options")
        for text, number in (("00080", 80), ("1", 1), ("65535", 65535)):
            checks.append(
                (options.parse_port, (text,), {"kind": "return", "repr": repr(number)})
            )
            checks.append(
                (
                    target.endpoint,
                    ("node.test", text),
                    {"kind": "return", "repr": repr(f"node.test:{number}")},
                )
            )
        for text in ("", "0", "65536", "-1", "+80", " 80", "80 ", "８０", "٨٠", "8_0"):
            checks.append((options.parse_port, (text,), raised))
            checks.append((target.endpoint, ("node.test", text), raised))
    else:
        raise ValueError("unregistered case")
    failures = [
        result
        for function, args, expected in checks
        if (result := observe(function, args, expected)) is not None
    ]
    return {"observations_executed": len(checks), "counterexamples": failures}


if __name__ == "__main__":
    sys.path.insert(0, "src")
    print(json.dumps(probe(sys.argv[1]), ensure_ascii=False))
