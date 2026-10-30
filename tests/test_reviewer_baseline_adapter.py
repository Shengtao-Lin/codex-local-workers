import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from reviewer_baseline_adapter import baseline_context


def test_baseline_context_requires_exact_archive_and_hash_without_read_credit(tmp_path):
    root = tmp_path
    run = root / ".agent/tasks/task/runs/run"
    path = "src/example.py"
    archived = run / "preimages" / path
    archived.parent.mkdir(parents=True)
    content = b"def original():\n    return object()\n"
    archived.write_bytes(content)
    sha = hashlib.sha256(content).hexdigest()
    manifest = [
        {
            "path": path,
            "existed": True,
            "sha256": sha,
            "archive_path": archived.relative_to(root).as_posix(),
        }
    ]
    (run / "preimages.json").write_text(json.dumps(manifest))
    (run / "changes.json").write_text(
        json.dumps(
            {"actual_relevant_changes": [{"path": path, "before": {"sha256": sha}}]}
        )
    )
    inspected = []
    runtime = SimpleNamespace(
        repo_root=root,
        run_root=run,
        read_lines={},
        _assert_read_allowed=lambda p: (p, root / p),
        editor=SimpleNamespace(
            _assert_no_reparse_components=lambda p: inspected.append(p)
        ),
    )
    reviewer = SimpleNamespace(ReviewError=ValueError)
    result = baseline_context(runtime, reviewer)
    assert result[0]["historical"] is True
    assert result[0]["current_source_read_credit"] is False
    assert runtime.read_lines == {}
    assert inspected == [archived.relative_to(root).as_posix()]
    archived.write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash drift"):
        baseline_context(runtime, reviewer)
    archived.write_bytes(content)
    manifest[0]["archive_path"] = "../other"
    (run / "preimages.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="archive path"):
        baseline_context(runtime, reviewer)
