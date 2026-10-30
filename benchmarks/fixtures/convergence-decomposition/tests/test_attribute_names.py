import runpy


def test_attribute_names_are_sorted_unique_immutable_snapshot():
    module = runpy.run_path("src/agent_runtime/telemetry/attributes.py")
    names = module["runtime_attribute_names"]()
    expected = tuple(
        sorted({value for key, value in module.items() if key.isupper() and isinstance(value, str)})
    )
    assert names == expected
    assert isinstance(names, tuple)
    assert len(names) == len(set(names))
    assert "agent.run.id" in names
    assert module["RUN_ID"] == "agent.run.id"
