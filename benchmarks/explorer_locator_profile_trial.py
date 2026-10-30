"""Qualify evidence retrieval separately from unqualified narrative diagnosis."""

import argparse
import time
from pathlib import Path

import bounded_evidence_support as S
import installed_scope_trial as I
import packaged_explorer_scope as OLD

BASE = I.BASE / "explorer-locator-profile-20261022-1"
QUESTIONS = {
    "revision": {
        "task": "Locate the actual make_sample_id(...) call inside adapters/common.py::_sample, including its source_revision argument assignment, and the SourceTrace.source_revision field definition. Distinguish the actual make_sample_id call from the later CanonicalSample constructor. Return only read source ranges; Primary will determine value-flow semantics. No narrative diagnosis, implementation, test execution or edits.",
        "anchors": [{"path": "src/evaluation_harness/adapters/common.py", "text": "sample_id = make_sample_id("},
                    {"path": "src/evaluation_harness/adapters/common.py", "text": "source_revision="},
                    {"path": "src/evaluation_harness/trace_sources/base.py", "text": "source_revision:"}],
        "exposure": "Previously exposed source question narrowed to retrieval, not new semantic success",
    },
    "request": {
        "task": "Locate jobs/queue.py::request_hash and the real canonical_json definition it uses. Cite the source range containing the hash expression with the canonical_json call and the dependency definition/body; imports alone are not sufficient. Only return read source ranges, not predictions or a semantic verdict. No edits or test execution.",
        "anchors": [{"path": "src/evaluation_harness/jobs/queue.py", "text": "return hashlib.sha256(canonical_json(payload)).hexdigest()"},
                    {"path": "src/evaluation_harness/canonical/serialization.py", "text": "def canonical_json("}],
        "exposure": "New locator question on previously used project; no holdout implementation claim",
    },
}


def prepare(cell, used):
    question = QUESTIONS[cell]
    batch = BASE / cell
    original = S.save

    def save(path, value):
        path = Path(path)
        if path.name == "config.json" and path.parent.name == ".local-agents":
            value.update(explorer_mode="locate", explorer_answer_protocol=False,
                         explorer_require_test_evidence=False,
                         explorer_required_citation_paths=list(dict.fromkeys(a["path"] for a in question["anchors"])),
                         explorer_required_source_anchors=question["anchors"])
            value.pop("explorer_require_trace_symbol", None)
        if path == batch / "registration.json":
            value.update(gate="Current real relevant source ranges with every approved literal locator anchor; Primary independently verifies call and dependency evidence",
                         role="Evidence locator only; causal investigation remains HOLD",
                         exposure=question["exposure"],
                         Primary_preparation="Supplied known paths/symbols and syntax anchors; no unseen semantic algorithm or answer. Preparation cost is real, not zero.",
                         budget="Existing16 turns/8 files/10 searches/6 protocol errors/600sec; no increase",
                         stop_rule="Two fixed distinct questions; ordinary failure HOLD, preserve both outcomes; no same-question success sampling")
            value["pins"][str(Path(__file__))] = S.sha(__file__)
            runtime = batch / "isolated/.local-agents/explorer-runtime.py"
            value["pins"][str(runtime)] = S.sha(runtime)
        original(path, value)

    OLD.BATCH, OLD.TASK = batch, question["task"]
    S.save = save
    try:
        OLD.prepare(used)
    finally:
        S.save = original


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=("prepare", "run"))
    p.add_argument("--cell", choices=QUESTIONS, required=True)
    p.add_argument("--weekly-used", type=int, required=True)
    a = p.parse_args()
    OLD.BATCH, OLD.TASK = BASE / a.cell, QUESTIONS[a.cell]["task"]
    if a.mode == "prepare":
        prepare(a.cell, a.weekly_used)
    else:
        OLD.run(a.weekly_used, time.time())
