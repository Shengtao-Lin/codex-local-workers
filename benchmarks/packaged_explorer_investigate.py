"""Match the question to existing investigate mode; retain locate-only outcome."""

import argparse
import time
from pathlib import Path

import bounded_evidence_support as S
import installed_scope_trial as I
import packaged_explorer_scope as OLD

BATCH=I.BASE / "packaged-explorer-investigate-20261022-1"
TASK="Investigate the make_sample_id(...) call inside adapters/common.py::_sample. Trace its source_revision argument back to the SourceTrace field, distinguishing that call from the later CanonicalSample(...) construction. Does the caller normalize the value before passing it? Cite a read source range containing the actual callee name and argument assignment, plus the field definition. Only this read-only value-flow question; no code/test changes or implementation suggestions."


def prepare(used):
    original=S.save
    def save(path,value):
        path=Path(path)
        if path.name=="config.json" and path.parent.name==".local-agents":
            value.update(explorer_mode="investigate",explorer_answer_protocol=False,explorer_require_trace_symbol="make_sample_id",explorer_required_citation_paths=["src/evaluation_harness/adapters/common.py","src/evaluation_harness/trace_sources/base.py"])
        if path==BATCH / "registration.json":
            value.update(mode="existing investigate, answer_protocol false",gate="One source-backed actual make_sample_id value-flow explanation; cite callee and argument in read source, not a different constructor",lineage="First packaged-explorer locate result retained as genuine location but insufficient causal evidence",Primary_intervention="Inspected wrong cited constructor, narrowed question and corrected task/mode match; no semantic answer or implementation supplied",budgets="unchanged",pins={**value["pins"],str(Path(__file__)):S.sha(__file__)})
        original(path,value)
    OLD.BATCH,OLD.TASK=BATCH,TASK
    S.save=save
    try:
        OLD.prepare(used)
    finally:
        S.save=original


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=("prepare","run"))
    p.add_argument("--weekly-used",type=int,required=True)
    p.add_argument("--observed-at",type=float)
    a=p.parse_args()
    OLD.BATCH,OLD.TASK=BATCH,TASK
    if a.mode=="prepare":
        prepare(a.weekly_used)
    else:
        OLD.run(a.weekly_used,a.observed_at or time.time())
