# `sample-identity` bounded-unit decomposition comparison

Status: targeted frozen experiment, **not** a general v1.2 or v2.1 release gate.

The source bytes, injected defects, protected `tests/test_sample_identity.py`, LM Studio endpoint, and role models match the existing frozen `sample-identity` fixture. The experiment changes only Primary's implementation-unit decomposition and focused-test selection. `fingerprint` owns `behavior-1` and may modify only `canonical/fingerprint.py`; dependent `reuse-key` owns `behavior-2`–`behavior-4` and may modify only `evaluations/dedup.py`. Each unit gets a fresh single-question Explorer investigation and Local Reviewer. The second cannot start until an archive-backed Primary acceptance of the first exists. The original complete test file remains read-only and is rerun after both units as the cross-function acceptance test.

| Snapshot | Explorer | Coder first call | Reviewer | Primary | Full integration |
| --- | --- | --- | --- | --- | --- |
| `route-split-f652229a80f7` | 2/2 | 2/2 ready | 2/2 pass | 2/2 accepted | 6/6 pytest, Ruff pass, `FEATURE_READY` eligible |
| `route-split-801d044fff04` | 2/2 | 2/2 ready | 2/2 pass | 2/2 accepted | 6/6 pytest, Ruff pass, `FEATURE_READY` eligible |

Across these two split snapshots: Explorer 4/4, Coder first-call readiness 4/4, Reviewer 4/4 reached, feature integration 2/2, and no explicit infrastructure failures. The Primary-reviewed actual edits were the same in both rounds: remove every existing `VOLATILE_CONTENT_FIELDS` item before fingerprint hashing; for the score-reuse payload use JSON-mode sample serialization excluding only `sample_id`. No source file outside each unit's writable scope changed. The integration archives bind the accepted source files and protected test to current SHA-256 hashes and executed pytest/Ruff results; the offline `FEATURE_READY` decision validator passed. The Coordinator state was **not** autonomously advanced to feature-ready.

The recent unsplit, unknown-location question-v2 snapshot `route-unknown-a5ec731a9ea8` passed Explorer but Coder returned `blocked`; Reviewer was not reached and independent tests failed. Earlier unknown-location unsplit snapshots also failed first-call Coder. This contrast supports testing behaviorally cohesive units with a protected feature-level round trip, but it is not a controlled statistical proof of improvement: the unit packet and focused-test sets changed together, and only one multi-file case was repeated twice.

The unsplit failed Coder run reached about 52% of its 24,576-token context window; the split calls peaked around 42% and 44%. None approached the limit, so the evidence points more toward task/repair complexity than context exhaustion. In the compared archives, the unsplit failed call made 16 model requests; the two successful split calls made 6 each. These are diagnostic observations, not a latency or token-cost guarantee.

Reproduce with `benchmarks/sample_identity_split_route.py first`, review the frozen diff and run `record-review.py --decision accept` for `fingerprint-a1` only if warranted, then run `second --workspace <snapshot>`. Review and accept `reuse-key-a1` separately. Finally run `verify --workspace <snapshot> --record-integration`. The runner never records Primary unit acceptance or feature readiness on its own.

For either archived completed snapshot, `benchmarks/sample_identity_split_route.py inspect --workspace <snapshot>` replays the read-only feature-evidence gate with both run references. It does not invoke a model, rewrite the frozen workspace, or make Primary's final decision. Both archived snapshots returned `eligible_for_primary_final_review` when replayed through this entry point.
