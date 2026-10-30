import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from strata_capability_audit import FILES, inspect, read_exact


def put(root, key, text):
    path = root / FILES[key]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_missing_install_does_not_become_safe_or_usable(tmp_path):
    report = inspect(tmp_path)
    assert all(r["status"] == "UNKNOWN_OR_REJECTED" for r in report["files"].values())
    assert report["enabled_features"] == []
    assert report["native_launch_authorized_by_this_report"] is False


def test_static_presence_never_enables_tools(tmp_path):
    put(tmp_path, "bundle", '{"version":"test"}')
    for key in FILES.keys() - {"bundle"}:
        put(tmp_path, key, "installed but not configured")
    report = inspect(tmp_path)
    assert all(r["status"] == "PRESENT_STATIC_ONLY" for r in report["files"].values())
    assert report["files"]["bundle"]["version"] == "test"
    assert report["enabled_features"] == []
    assert report["provider_calls"] == report["commands_executed"] == 0
    assert not report["credentials_read"]


def test_hazards_are_source_backed_not_automatic_runtime_claims(tmp_path):
    put(tmp_path, "sdk", "apiKeyEnv: DEEPSEEK_API_KEY\nmode: danger-full-access\n")
    put(tmp_path, "web", "provider is unavailable\n")
    put(tmp_path, "files", "without one the tools use unconditional provider calls\n")
    report = inspect(tmp_path)
    assert len(report["observed_blockers"]) == 4
    assert report["files"]["sdk"]["evidence"][1]["line"] == 2
    assert len(report["files"]["sdk"]["sha256"]) == 64
    assert "effective running plugin tree and overrides" in report["unknown"]


def test_changed_file_hash_and_missing_marker_are_visible(tmp_path):
    path = put(tmp_path, "sdk", "danger-full-access")
    before = inspect(tmp_path)
    path.write_text("unknown alternate config", encoding="utf-8")
    after = inspect(tmp_path)
    assert before["files"]["sdk"]["sha256"] != after["files"]["sdk"]["sha256"]
    assert after["files"]["sdk"]["evidence"] == []
    assert not after["native_launch_authorized_by_this_report"]


@pytest.mark.parametrize(
    "path", ["../secret", ".env", "node_modules/unknown/package.json"]
)
def test_exact_manifest_excludes_credentials_and_arbitrary_paths(tmp_path, path):
    with pytest.raises(ValueError, match="exact inspection manifest"):
        read_exact(tmp_path, path)


def test_does_not_evaluate_yaml_or_import_inspected_code(tmp_path):
    put(tmp_path, "sdk", "!!js throw new Error('MUST NOT EXECUTE')\n")
    report = inspect(tmp_path)
    assert report["files"]["sdk"]["status"] == "PRESENT_STATIC_ONLY"
    assert report["commands_executed"] == 0


@pytest.mark.parametrize("body", ["not json", "[]", "null", '"text"'])
def test_invalid_bundle_is_unknown_not_a_crash(tmp_path, body):
    put(tmp_path, "bundle", body)
    assert inspect(tmp_path)["files"]["bundle"]["status"] == "UNKNOWN_OR_REJECTED"


def test_oversized_inputs_rejected(tmp_path):
    put(tmp_path, "sdk", "x" * 256_001)
    assert inspect(tmp_path)["files"]["sdk"]["status"] == "UNKNOWN_OR_REJECTED"


def test_output_is_create_only(tmp_path):
    from bounded_evidence_support import save

    output = tmp_path / "report.json"
    save(output, {"original": True})
    with pytest.raises(FileExistsError):
        save(output, {"original": False})
    assert json.loads(output.read_text()) == {"original": True}
