"""Decompose existing conjunctive contracts, never implementation units or risk."""

import copy


def apply_ledger(packet, case):
    packet = copy.deepcopy(packet)
    if case == "window-groups":
        clauses = [
            (
                "width-type",
                "width accepts only values whose concrete Python class is int. Reject bool and every int subclass, along with float, str and None, by raising ValueError.",
            ),
            (
                "width-range",
                "An accepted integer width must be at least 1; zero and negatives raise ValueError.",
            ),
            (
                "empty-validation",
                "Invalid width still raises ValueError when items is empty; valid width on empty items returns [].",
            ),
            (
                "partition",
                "Return consecutive list slices in input order; each has width elements except a possibly shorter last slice; include every input element exactly once.",
            ),
            (
                "no-mutation",
                "Do not mutate items; deep-copying individual elements is not required.",
            ),
        ]
        scenarios = [
            (
                "normal",
                "groups([1,2,3,4,5],2) returns [[1,2],[3,4],[5]].",
                {"result": [[1, 2], [3, 4], [5]]},
            ),
            (
                "empty",
                "groups([],2) returns []; groups([],0) raises ValueError.",
                {"valid_empty": [], "invalid_empty": "ValueError"},
            ),
            (
                "types",
                "True, False, 1.0, '2', None and an instance of a user-defined int subclass are invalid width values, even for empty items.",
                {"exception": "ValueError"},
            ),
        ]
    elif case == "timeout-roundtrip":
        clauses = [
            (
                "missing-default",
                "Only an absent timeout_ms key selects the default 1000. An explicitly present None is invalid and raises ValueError, not the default.",
            ),
            (
                "timeout-type",
                "A present timeout_ms value accepts only concrete Python int, rejecting bool, int subclasses, float, str and None with ValueError.",
            ),
            (
                "timeout-range",
                "Zero and positive accepted integers are preserved; negative integers raise ValueError.",
            ),
            (
                "summary-roundtrip",
                "summarize returns timeout_ms unchanged and timeout_seconds as seconds retaining fractional milliseconds; it uses the same validation/default behavior as parse_timeout.",
            ),
            ("no-mutation", "Neither function mutates the input config."),
        ]
        scenarios = [
            (
                "missing",
                "summarize({}) returns timeout_ms 1000 and timeout_seconds 1.0.",
                {"timeout_ms": 1000, "timeout_seconds": 1.0},
            ),
            (
                "zero",
                "summarize({'timeout_ms':0}) preserves zero in both output fields.",
                {"timeout_ms": 0, "timeout_seconds": 0.0},
            ),
            (
                "fraction",
                "summarize({'timeout_ms':1250}) returns 1250 and 1.25 seconds.",
                {"timeout_ms": 1250, "timeout_seconds": 1.25},
            ),
            (
                "invalid",
                "Present None, True, False, float, str, negative integers and int-subclass instances raise ValueError in both functions.",
                {"exception": "ValueError"},
            ),
        ]
    else:
        raise ValueError("unregistered contract")
    packet["required_behavior"] = [
        {"id": key, "text": text, "risk_floor": packet["risk"]["unit"]}
        for key, text in clauses
    ]
    packet["owned_contract_ids"] = [key for key, _ in clauses]
    packet["acceptance_scenarios"] = [
        {"id": key, "text": text, "observables": values}
        for key, text, values in scenarios
    ]
    return packet
