"""Source-only report recovery; no artificial TRACE qualification on a source question."""

import argparse
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import bounded_evidence_support as S
import installed_scope_trial as I
import packaged_explorer_investigate as INV

BATCH = I.BASE / "explorer-report-recovery-live-20261022-1"
CONTROLS = I.BASE / "explorer-obligation-controls-20261022-1/recovery-green.xml"


def prepare(used):
    cases = list(ET.parse(CONTROLS).iter("testcase"))
    assert len(cases) == 104 and not any(c.find(x) is not None for c in cases for x in ("failure", "error", "skipped"))
    old = I.BASE / "explorer-obligation-live-20261022-1"
    if not (old / "decision.json").exists():
        report = S.read(old / "isolated/.agent/explorer-report.json")
        S.save(old / "decision.json", {"status": "HOLD_REPEATED_MALFORMED_REPORT", "success": False,
               "facts": report["protocol_error_details"], "failure_reason": report["failure_reason"],
               "confirmed_host_fault": "Existing repeated-output report recovery requires source AND tests even when Primary explicitly marks source-only",
               "semantic_conclusion": "No valid final report; no causal success credit, model semantic ability not determined"})
    original = S.save

    def save(path, value):
        path = Path(path)
        if path.name == "config.json" and path.parent.name == ".local-agents":
            value["explorer_require_test_evidence"] = False
            value.pop("explorer_require_trace_symbol", None)
        if path == BATCH / "registration.json":
            runtime = BATCH / "isolated/.local-agents/explorer-runtime.py"
            value.update(candidate="Existing one-shot native final-report recovery made available for explicit source-only evidence; same error/turn/time limits",
                         configuration_correction="This is a source-value-flow question, not TRACE tool compatibility qualification. Remove only the artificial exact-action requirement, retain actual field+callee+argument source-evidence gate unchanged",
                         exposure="Previously exposed question; prior three failures/location-only outcomes retained, not new holdout",
                         gate="Correct actual make_sample_id caller/argument and SourceTrace field with read source citations, not CanonicalSample location only",
                         no_semantic_hint="Exact same task text; no answer or patch supplied; required source paths unchanged",
                         offline_controls="104 passed, including legacy Explorer and package controls; unread/false citations and missing TRACE/regex evidence never bypassed")
            value["pins"].update({str(runtime): S.sha(runtime), str(Path(__file__)): S.sha(__file__), str(CONTROLS): S.sha(CONTROLS)})
        original(path, value)

    INV.BATCH = BATCH
    S.save = save
    try:
        INV.prepare(used)
    finally:
        S.save = original


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=("prepare", "run"))
    p.add_argument("--weekly-used", type=int, required=True)
    a = p.parse_args()
    INV.BATCH = INV.OLD.BATCH = BATCH
    INV.OLD.TASK = INV.TASK
    if a.mode == "prepare":
        prepare(a.weekly_used)
    else:
        INV.OLD.run(a.weekly_used, time.time())
