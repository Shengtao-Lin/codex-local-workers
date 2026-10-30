"""New isolated three-task batch; only Reviewer source-stage profile differs."""

import argparse
import os
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import bounded_evidence_support as S
import installed_scope_trial as I
import normal_task_trial as N
import real_change_trial as R

BATCH = I.BASE / "reviewer-direct-20261021-1"
ORDER = ["json-1", "message-1", "destination-1"]
ADAPTER = Path(__file__).with_name("reviewer_direct_report.py")


def prepare(used):
    controls = list(ET.parse(BATCH / "controls-2.xml").iter("testcase"))
    assert len(controls) == 23 and not any(c.find(t) is not None for c in controls for t in ("failure", "error", "skipped"))
    assert not (BATCH / "registration.json").exists()
    original_refresh, original_save = I.refresh_material, S.save

    def refresh(root, config):
        original_refresh(root, config)
        target = root / ".local-agents/local-bounded-review.py"
        text = target.read_text(encoding="utf-8")
        assert "DIRECT.install" not in text
        text = text.replace("from bounded import reviewer_capture_entry as CAPTURE", "from bounded import reviewer_capture_entry as CAPTURE\nfrom bounded import reviewer_direct_report as DIRECT")
        assert text.count("    if options.inspect_only:") == 1
        text = text.replace("    if options.inspect_only:", "    runtime_class = DIRECT.install(module, runtime_class, enabled=True)\n    if options.inspect_only:")
        target.write_text(text, encoding="utf-8")
        shutil.copyfile(ADAPTER, root / ".local-agents/bounded/reviewer_direct_report.py")

    def save(path, value):
        if Path(path) == BATCH / "registration.json":
            value.update(
                candidate="Explicit isolated direct-report-v1: existing low reasoning and required REPORT from first source-review request; Coder/checks/budgets/verdict gates unchanged",
                gate="3/3 independent full-chain accept, one each original frozen task; diagnostic only, no production or broad qualification",
                comparison="Old real-change-trial-20261021-4 remains 0/1 accepted, five NOT_RUN. This is a NEW candidate batch, not completion or erasure of that batch. Coder is fresh, so full-chain outcomes alone cannot isolate Reviewer causality.",
                exposure="json is exposed old task; message and destination not live-exposed. All three tasks retain exact old templates/private acceptance. No failed draft, successful patch or Reviewer response injected as Coder hints.",
                offline="controls.xml retains basetemp setup errors and an inapplicable historical pre-live assertion; controls-2.xml 23 protocol/negative controls passed, historical pre-live assertion excluded because those old trials already ran",
                continue_rule="Ordinary Coder/semantic rework HOLD but continue diagnostics; Reviewer execution/infra, safety, drift, deadlines or weekly50 stop; no resampling",
            )
            for p in (Path(__file__), ADAPTER, BATCH / "controls-2.xml"):
                value["pins"][str(p)] = S.sha(p)
            for name in ("cells.json", "origins.json"):
                value["pins"][str(BATCH / name)] = S.sha(material / name)
        original_save(path, value)

    I.refresh_material, S.save = refresh, save
    R.BATCH, R.ORDER = BATCH, ORDER
    # The reused builder insists on an absent batch directory; controls already
    # exist here, so temporarily supply its path-existence precondition with a
    # separate NEW material directory, keeping all controls in the parent.
    material = BATCH / "material"
    R.BATCH = material
    def material_save(path, value):
        if Path(path) == material / "registration.json":
            save(BATCH / "registration.json", value)
        else:
            save(path, value)
    S.save = material_save
    try:
        R.prepare(used)
    finally:
        I.refresh_material, S.save = original_refresh, original_save
    reg = S.read(BATCH / "registration.json")
    assert reg["registered"] == 3
    # Expose immutable manifests at the expected runner paths, not duplicate
    # mutable copies of the task roots. Root locations remain material/cells/.
    for name in ("cells.json", "origins.json", "baseline.json"):
        original_save(BATCH / name, S.read(material / name))
    old = R.I.BASE / "real-change-trial-20261021-4"
    for topic in R.TASKS:
        for p in (material / "templates" / topic).rglob("*"):
            if p.is_file() and not any(x in p.parts for x in ("__pycache__", ".pytest_cache", ".ruff_cache")):
                assert S.sha(p) == S.sha(old / "templates" / topic / p.relative_to(material / "templates" / topic))
    print("Three matched starts frozen with isolated Reviewer candidate")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("--cell", choices=ORDER)
    parser.add_argument("--weekly-used", type=int, required=True)
    parser.add_argument("--observed-at", type=float)
    args = parser.parse_args()
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if args.mode == "prepare":
        prepare(args.weekly_used)
    else:
        N.run(args.cell, args.weekly_used, args.observed_at, batch=BATCH, order=ORDER, build_command=I.command, usage_limit=50, batch_seconds=10800)
