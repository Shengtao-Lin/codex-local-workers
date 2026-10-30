"""Primary acceptance following the sole substantive recovered review."""

from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import reviewer_load_recovery as R


def main():
    row=S.read(R.V.BATCH / "cells.json")["message-2"]
    root=Path(row["root"])
    identity=row["identity"]
    review_id="retry-"+identity["run_id"]
    path=root / ".agent/tasks" / identity["task_id"] / "reviews" / review_id / "handoff.json"
    report=S.read(path)
    assert report["decision"]=="pass_to_primary" and not report["findings"]
    disposition=R.BATCH / "disposition.json"
    S.save(disposition,{"schema_version":1,"authority":"primary","identity":report["identity"],"report_sha256":S.sha(path),"resolution":"cleared","evidence":["Primary inspected message-2 full source and diff: both float branches removed, bool exclusion/string priority/original fallback unchanged. Original independent complete tests/static checks passed; source unchanged across zero-request load failure and one substantive recovered fresh review."],"findings":[]})
    command=[S.PYTHON,"-B",root / ".local-agents/record-review.py","--repo",root,"--task-id",identity["task_id"],"--run-id",identity["run_id"],"--decision","accept","--summary","Primary accepts after original validation and exactly one substantive fresh review; zero-request load failure retained, no Coder rerun or same-code semantic resampling.","--config",root / ".agent/config.json","--disposition",disposition]
    result=T.run(command,root)
    S.save(R.BATCH / "record-command.json",result)
    assert result["exit_code"]==0,result
    S.save(R.BATCH / "primary-decision.json",{"decision":"accept","identity":identity,"review_id":review_id,"original_infra_failure_preserved":True,"assisted":False,"coder_rerun":False,"semantic_review_resampling":False,"cloud_tokens":"unknown"})
    S.save(R.BATCH / "handoff.json",{"current_state":"independently accepted after transport recovery","original_decision":"decision.json","Primary":"primary-decision.json","old_fixed_batch_stop_and_scores":"unchanged"})
    print("Accepted recovered unit; original infrastructure stop retained")


if __name__=="__main__":
    main()
