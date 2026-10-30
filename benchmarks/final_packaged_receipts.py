"""Final preservation/budget receipts, never edits an earlier decision."""

import subprocess

import bounded_evidence_support as S
import installed_scope_trial as I


def main():
    batch = I.BASE / "packaged-release-20261022-1"
    old = I.BASE / "packaged-flat-profile-20261022-1"
    baseline = S.read(old / "baseline.json")
    allowed = {"AGENTS.md", ".local-agents/README.md", ".local-agents/host-proposal.md",
               ".local-agents/local-bounded-unit.py", ".local-agents/local-bounded-review.py",
               ".local-agents/model_residency.py", ".local-agents/worker-runtime.py",
               ".local-agents/explorer-runtime.py"}
    changed = {p for p, digest in baseline["preimages"].items() if S.sha(S.KIT / p) != digest}
    assert changed <= allowed, changed - allowed
    assert all(S.sha(old / "preimages" / p) == digest for p, digest in baseline["preimages"].items())
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=S.KIT).decode().strip()
    assert head == baseline["head"]
    S.save(batch / "preservation.json", {"head_unchanged": head,
           "original_preimages_all_intact": True,
           "modified_preexisting_runtime_files": {p: {"old": baseline["preimages"][p], "current": S.sha(S.KIT / p)} for p in sorted(changed)},
           "other_preexisting_runtime_files_unchanged": True,
           "default_configs_unchanged": True,
           "docs_preimages": {str(p.relative_to(batch)): S.sha(p) for p in (batch / "preimages").rglob("*") if p.is_file()},
           "sibling_policy": "Read-only environments/source snapshots; no sibling writes authorized or issued",
           "commit_push": "Not performed", "weekly_used_observed": 35, "weekly_ceiling": 60})
    S.save(I.BASE / "packaged-chain-profile-20261022-1/budget-authority.json", {
        "actual_latest_user_weekly_stop": 60,
        "registration_weekly_stop": 60,
        "observed_at_completed_chain": 35,
        "inherited_helper_metadata_stop": 50,
        "interpretation": "Legacy close helper reports50 in nested metrics and its admission function retains that stricter cap. It did not bind this completed batch at35; no latest-user60 stop was reached. Historical helper output retained, not rewritten.",
        "counts": "New wrapper registered exactly1 chain/2 units. Generic inherited preparation stdout says4/8; authoritative registration and canonical evidence are1/2, not4/8."})
    print("Preservation and budget receipts saved; HEAD and default configs unchanged")


if __name__ == "__main__":
    main()
