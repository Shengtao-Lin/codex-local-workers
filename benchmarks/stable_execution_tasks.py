"""New requested changes on read-only sibling sources; evaluator-only references."""

from pathlib import Path

UP = Path("F:/ChatGPT/agent-evaluation-harness/src/evaluation_harness")


def tasks(extract):
    sample = extract(UP / "canonical/fingerprint.py", "make_sample_id")
    collector = extract(UP / "telemetry/ingestion.py", "collector_environment")
    return {
        "binding": {
            "origin": "telemetry/ingestion.py", "symbol": "application_binding_path",
            "header": "from urllib.parse import quote, urlencode\n",
            "contract": "application_binding_path keeps application_id as exactly one percent-encoded path segment and workspace_id as the first urlencode query item. NEW: when environment is exactly the empty string, omit the environment query item entirely. For every nonempty environment, including whitespace, keep its exact old value and query ordering after workspace_id. Preserve all string inputs without stripping, normalizing or filesystem/network effects. Empty workspace/application IDs retain old encoding behavior. Keep signature/imports. Other input types are outside the str contract.",
            "reference": '''def application_binding_path(workspace_id: str, application_id: str, environment: str) -> str:
    values = {"workspace_id": workspace_id}
    if environment != "":
        values["environment"] = environment
    return f"/v1/applications/{quote(application_id, safe='')}?" + urlencode(values)
''',
            "public": '''from product.code import application_binding_path

def test_empty_environment_is_omitted():
    assert application_binding_path("work space", "app/id", "") == "/v1/applications/app%2Fid?workspace_id=work+space"

def test_existing_query_order_and_values():
    assert application_binding_path("w", "app", "dev&qa") == "/v1/applications/app?workspace_id=w&environment=dev%26qa"
''',
            "private": '''from urllib.parse import quote, urlencode
from product.code import application_binding_path

def test_nonempty_legacy_and_empty_fields():
    for w, a, e in [("", "", ""), (" ", "../雪%", " "), ("a+b", "a/b", ""), ("%", "?", "qa/dev")]:
        query = {"workspace_id": w}
        if e != "":
            query["environment"] = e
        assert application_binding_path(w, a, e) == "/v1/applications/" + quote(a, safe="") + "?" + urlencode(query)
''',
            "cases": [{"args": ["work", "app/id", e], "kwargs": {}} for e in ("", "qa")],
        },
        "hash": {
            "origin": "canonical/fingerprint.py", "symbol": "make_sample_id",
            "header": "import hashlib\nfrom product.dependencies import canonical_json\n",
            "contract": "make_sample_id gains one normalization: source_revision equal to the empty string has exactly the same sample ID as source_revision=None. Preserve the exact existing canonical identity fields, defaults, smp_ prefix and first32 SHA256 hex characters for every other input, including nonempty whitespace revision strings. Empty/None normalization affects source_revision only. turn_index=0 remains distinct from None; all adapter/schema/workspace identity fields remain meaningful. Use the existing read-only canonical_json byte semantics. Keep signature/imports, no mutation or external effects.",
            "reference": sample.replace('"source_revision": source_revision,', '"source_revision": None if source_revision == "" else source_revision,'),
            "public": '''from product.code import make_sample_id

BASE = dict(application_id="app", environment="qa", source_trace_id="t", row_mode="turn", turn_index=0, adapter_name="a", adapter_version="1")

def test_empty_revision_equivalence():
    assert make_sample_id(**BASE, source_revision="") == make_sample_id(**BASE, source_revision=None)

def test_revision_and_turn_remain_meaningful():
    value = make_sample_id(**BASE, source_revision="v1")
    assert value.startswith("smp_") and len(value) == 36
    assert value != make_sample_id(**BASE, source_revision="v2")
''',
            "private": '''import hashlib
from product.code import make_sample_id
from product.dependencies import canonical_json

def test_exact_identity_projection():
    for revision in (None, "", " ", "v1"):
        for turn in (None, 0, -1):
            values = dict(workspace_id="雪", application_id="a", environment="", source_trace_id="t", source_revision=revision, row_mode="turn", turn_index=turn, adapter_name="adapter", adapter_version="2", schema_version="1.1")
            identity = dict(values)
            identity["source_revision"] = None if revision == "" else revision
            expected = "smp_" + hashlib.sha256(canonical_json(identity)).hexdigest()[:32]
            assert make_sample_id(**values) == expected
''',
            "cases": [{"args": [], "kwargs": dict(application_id="app", environment="qa", source_trace_id="t", source_revision=r, row_mode="turn", turn_index=0, adapter_name="a", adapter_version="1")} for r in ("", None)],
        },
        "collector": {
            "origin": "telemetry/ingestion.py", "symbol": "collector_environment",
            "header": "import re\nfrom typing import Any\nfrom urllib.parse import quote\n",
            "contract": "collector_environment must retain every existing rejection rule and original MLFLOW_EXPERIMENT_ID output. NEW: after successful binding validation, also return OTEL_RESOURCE_ATTRIBUTES as a comma-separated string in exact order agent.workspace.id, agent.id, deployment.environment.name, whose values are respectively workspace_id, application_id and environment percent-encoded as individual values with no safe characters (including slash). Preserve exact nonempty values, including spaces, Unicode, percent and delimiters; no stripping or double encoding. Identity matching, enabled is True and ASCII numeric experiment ID rules remain intact. Do not mutate application or contact services. Keep signature/imports and return only these two keys.",
            "reference": collector.replace('return {"MLFLOW_EXPERIMENT_ID": experiment_id}', '''return {
        "MLFLOW_EXPERIMENT_ID": experiment_id,
        "OTEL_RESOURCE_ATTRIBUTES": ",".join(
            f"{key}={quote(value, safe='')}"
            for key, value in (
                ("agent.workspace.id", workspace_id),
                ("agent.id", application_id),
                ("deployment.environment.name", environment),
            )
        ),
    }'''),
            "public": '''import pytest
from product.code import collector_environment

def test_binding_environment():
    app = dict(workspace_id="w", application_id="a/b", environment="qa", enabled=True, mlflow_experiment_id="0017")
    assert collector_environment(app, workspace_id="w", application_id="a/b", environment="qa") == {
        "MLFLOW_EXPERIMENT_ID": "0017",
        "OTEL_RESOURCE_ATTRIBUTES": (
            "agent.workspace.id=w,agent.id=a%2Fb," "deployment.environment.name=qa"
        ),
    }

def test_disabled_still_rejected():
    app = dict(workspace_id="w", application_id="a", environment="qa", enabled=False, mlflow_experiment_id="17")
    with pytest.raises(ValueError):
        collector_environment(app, workspace_id="w", application_id="a", environment="qa")
''',
            "private": '''import copy
import pytest
from urllib.parse import quote
from product.code import collector_environment

def test_exact_encoding_and_no_mutation():
    values = dict(workspace_id="雪 w", application_id="x/y,%", environment=" ")
    app = dict(values, enabled=True, mlflow_experiment_id="0", extra={"x": [1]})
    before = copy.deepcopy(app)
    result = collector_environment(app, **values)
    expected = ",".join(k + "=" + quote(v, safe="") for k, v in zip(("agent.workspace.id", "agent.id", "deployment.environment.name"), values.values()))
    assert result == {"MLFLOW_EXPERIMENT_ID": "0", "OTEL_RESOURCE_ATTRIBUTES": expected}
    assert app == before

@pytest.mark.parametrize("change", [{"workspace_id": "other"}, {"enabled": 1}, {"mlflow_experiment_id": ""}, {"mlflow_experiment_id": "name"}, {"mlflow_experiment_id": None}])
def test_existing_rejections(change):
    values = dict(workspace_id="w", application_id="a", environment="qa")
    app = dict(values, enabled=True, mlflow_experiment_id="17")
    app.update(change)
    with pytest.raises(ValueError):
        collector_environment(app, **values)
''',
            "cases": [{"args": [dict(workspace_id="w", application_id="a/b", environment="qa", enabled=True, mlflow_experiment_id="17")], "kwargs": dict(workspace_id="w", application_id="a/b", environment="qa")}],
        },
    }
