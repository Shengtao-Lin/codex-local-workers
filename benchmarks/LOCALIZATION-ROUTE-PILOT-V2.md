# Restricted localization route: five-type pilot (question v2)

Status: **observational pilot, not a v1.2 or v2.1 release gate**. The preregistered `localization-v1` implementation-entry assessment used 11+ cases in two rounds; this report tests the implemented restricted route on five distinct frozen types in one round. Each run used a separate snapshot under `benchmarks/work/stability-v1`, pinned read-only source files, its own `.agent` archive, and independent post-run pytest/Ruff checks. The five exact result files are recorded in `benchmarks/work/stability-v1/localization-route-pilot-v2.json`.

| Case | Snapshot | Explorer evidence | Coder first call | Reviewer | Independent E2E |
| --- | --- | --- | --- | --- | --- |
| `metadata-limit` | `route-unknown-54c5f3bb3594` | valid | ready | pass | pass |
| `internal-trace` | `route-unknown-f2fea97dc169` | valid | ready | pass | pass |
| `scorer-unused-binding` | `route-unknown-247170a7a46c` | valid | ready | pass | pass |
| `mapping-message-sequence` | `route-unknown-18239cc48a43` | valid | ready | pass | pass |
| `sample-identity` | `route-unknown-a5ec731a9ea8` | valid | blocked | not reached | fail |

Totals: injected baseline failure 5/5; Explorer 5/5; Coder first-call readiness 4/5; Reviewer pass 4/4 reached (not 5/5); independent first-pass E2E 4/5; explicit infrastructure failures 0. There were no rework calls **in this five-cell cohort**. Primary inspected the four passing cumulative diffs: constant correction, telemetry membership correction, unused binding removal, and string/bytes sequence rejection respectively. No broad unrelated edits were present.

The `sample-identity` Coder again excluded only `sample_id` and `labels` from the fingerprint, leaving volatile `source_metadata`, and replaced JSON-mode sample serialization with a hand-built object. Focused tests failed, so Reviewer was correctly withheld. This matches a prior unknown-location failure signature. The packet already stated both invariants; another unchanged retry is not justified. The earlier separately recorded a1→a2→a3 supervised rework conversion remains evidence of eventual repair, not a first-call pass for this cohort.

One prior `metadata-limit` attempt (`route-unknown-70d5984bc3f7`) is **outside** this cohort. Its v1 question named the injected value `MAX_METADATA_BYTES = 163_840`; Explorer searched once successfully but never read that result and stopped after three no-evidence searches. The v2 question names the stable symbol `MAX_METADATA_BYTES`. Both snapshots are retained; changing the question starts a new candidate and never erases the v1 failure. The route runner now writes `route-result.json` even when Explorer fails and checks Ruff when the injected baseline defect is static-only. The summary tool rejects mixed question versions and keeps initial and rework counts separate.

Decision: the restricted localization handoff is working on four types, but **unattended routing remains NO-GO**. The next targeted experiment should decompose `sample-identity` into two behaviorally cohesive Coder units while keeping its cross-function protected integration assertions and Primary integration review. Compare that version against the current single multi-file unit on fresh identical snapshots; do not claim an improvement from a single successful rework or hide the initial failures. Reviewer defect-detection challenges and broader two-round coverage remain separate requirements.

That targeted decomposition was subsequently run twice on fresh snapshots. Both split-unit chains passed their focused Coder→Reviewer calls and full integration checks; see `benchmarks/SAMPLE-IDENTITY-SPLIT-COMPARISON.md`. This is a separate experimental variant and does not rewrite the five-cell first-pass result above.
