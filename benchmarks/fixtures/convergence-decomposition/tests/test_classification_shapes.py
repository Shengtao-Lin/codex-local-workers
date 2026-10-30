import runpy


def test_malformed_nested_shapes_are_external():
    classify = runpy.run_path("src/evaluation_harness/telemetry/classification.py")[
        "is_internal_trace"
    ]
    for raw in (None, [], {"attributes": [1]}, {"resource": "bad"}, {"metadata": 1}):
        assert classify(raw) is False


def test_valid_markers_and_input_identity_are_preserved():
    classify = runpy.run_path("src/evaluation_harness/telemetry/classification.py")[
        "is_internal_trace"
    ]
    raw = {"attributes": {"evaluation.internal": True}}
    assert classify(raw) is True
    assert raw == {"attributes": {"evaluation.internal": True}}
    assert classify({"resource": {"service.name": "outside"}}) is False
    assert classify({"resource": {"service.name": "custom"}}, service_names={"custom"}) is True
