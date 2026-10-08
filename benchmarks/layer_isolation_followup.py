"""Versioned future fixtures; never mutate the first layer's frozen corpus."""

from __future__ import annotations

from layer_isolation_cases import corpus


def strengthened_corpus(template):
    data, oracles = corpus(template)
    for case in data["cases"]:
        if case["case_id"] == "duration-pair":
            case["exposure"] = "known-semantic-family"
        if case["case_id"] != "encoded-path":
            continue
        case["files"]["tests/test_target.py"] += (
            "\n\ndef test_canonical_encoding():\n"
            '    assert encode_segment("a+b") == "a%2Bb"\n'
            '    assert path_for("a+b") == "/items/a%2Bb"\n'
            '    assert encode_segment("a b") == "a%20b"\n'
            '    assert encode_segment("%2F") == "%252F"\n'
        )
        reference = oracles["encoded-path"]["reference"]
        mutant = dict(reference)
        mutant["src/product/codec.py"] = mutant["src/product/codec.py"].replace(
            "safe=''", "safe='+'"
        )
        oracles["encoded-path"]["mutants"].append(mutant)
    return data, oracles
