import inspect
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import stdlib_reference as R


def test_verbatim_documentation_not_selected_repair_advice():
    result = R.collect("import json\ndef f(value):\n    return json.dumps(value)")
    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item["documentation"] == inspect.getdoc(json.dumps)
    assert item["signature"] == str(inspect.signature(json.dumps))


def test_no_arbitrary_import_or_code_execution():
    result = R.collect(
        'import nonexistent_untrusted\nnonexistent_untrusted.execute()\nraise Exception("must not run")'
    )
    assert result["items"] == []


def test_all_referenced_approved_calls_include_aliases():
    result = R.collect(
        "import json as j\nimport hashlib\ndef f(x):\n    return hashlib.sha256(j.dumps(j.loads(x)).encode()).hexdigest()"
    )
    assert [item["api"] for item in result["items"]] == [
        "hashlib.sha256",
        "json.dumps",
        "json.loads",
    ]


def test_reference_is_readonly_bound_and_not_an_edit(tmp_path):
    import supervised_reference_trial as trial

    target = tmp_path / "src/product/code.py"
    target.parent.mkdir(parents=True)
    source = "import json\ndef canonical_json(x):\n    return json.dumps(x)\n"
    target.write_text(source, encoding="utf-8")
    packet = {
        "scope": {"read": ["src"], "readonly": [], "modify": ["src/product/code.py"]}
    }
    policy = {"source_paths": [], "readonly_hashes": {}}
    config = {"coder_single_function": {"dependencies": "import json\n"}}
    paths = trial.configure(tmp_path, packet, policy, config)
    assert paths == ["context/stdlib-reference.json"]
    assert paths[0] in packet["scope"]["read"]
    assert paths[0] in packet["scope"]["readonly"]
    assert packet["scope"]["modify"] == ["src/product/code.py"]
    assert policy["readonly_hashes"][paths[0]] == trial.S.sha(tmp_path / paths[0])
    assert json.loads((tmp_path / paths[0]).read_text(encoding="utf-8"))["items"][0][
        "documentation"
    ] == inspect.getdoc(json.dumps)
    assert target.read_text(encoding="utf-8") == source
