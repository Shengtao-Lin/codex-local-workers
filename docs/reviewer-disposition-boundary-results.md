# Reviewer disposition boundary: bounded implementation accepted

2026-10-10. Weekly used started and last observed at 46%, ceiling 50%. Stop
reason: explicit boundary-stage conclusion. No commit/push or sibling edits.

## What now holds

Reviewer recommendations, local-unit output and task-policy all direct `rework`
to Primary adjudication, not Coder. `record-review.py --disposition` binds Primary
finding classifications to the exact completed canonical report and current
read-source hashes. Every finding must be classified exactly once with evidence.
Confirmed defects/required test gaps may justify repair; questions/conflicting
contracts require Primary resolution. Nonblocking suggestions add no requirement.

Inherited Coder rework with a blocking Reviewer history must reference the
parent's immutable Primary rework record, unchanged Reviewer report and confirmed
finding IDs. Missing disposition, contract replan, altered report or unconfirmed
feedback is rejected before model execution. Ordinary Coder validation-failure
repair remains supported. Fresh packets remain a trusted Primary responsibility;
this is not an operating-system or authenticated-user security boundary.

There is no acceptance override: dismissing a false positive only advances to
Primary review, not automatic acceptance. Existing validation/Reviewer-pass/risk
gates remain. Protected test gaps may require a Primary scope/contract revision
rather than editing production code. Raw model decision/category/fix remain intact.

## Evidence and limits

- The same sixteen frozen cases, sources, protected tests and actual model reports
  were replayed, using the previous explicit Primary causal adjudications.
- Routing agrees with those adjudications for 16/16: six real code defects and
  two required-test gaps stay blocking, two impossible contracts route to Primary,
  six correct implementations advance only to Primary review.
- This is deterministic policy replay, **not sixteen new model successes**.
  Model semantic correctness remains 14/16; zero new LM Studio calls occurred.
- Unit/integration negatives exercise no disposition, stale report/source,
  cross-run identity, duplicate/missing/unknown finding, unresolved evidence,
  unsafe acceptance override, legacy local-unit output, and inherited-entry checks.
- Final full regression: **1014 passed, 137 subtests passed**. Installation into a
  disposable repository, its unit tests, lint and format checks pass. One initial
  full regression had a new-test formatting failure; it and both later XML runs
  remain preserved. No model/test case was changed to remove a failure.
- Model prompts, config and all unrelated baseline-frozen files are hash-verified
  unchanged. Global Coordinator remains disabled. No measured savings claim:
  Primary active time and cloud tokens remain unmeasured.

The boundary implementation is accepted for controlled use, following full Primary
review of changed runtime paths and broader regression. Reviewer formal semantic
release and the earlier product gate remain HOLD; do not relabel their failures.
The next bounded experiment should exercise Primary disposition followed by a
confirmed inherited repair on existing real units, measuring adjudication effort
against direct Primary review. This round did not run that new live model chain.

## Files and retained records

Usage instructions ship with `.local-agents/review-disposition.md` and AGENTS.md.
Policy implementation is `.local-agents/review-disposition.py`; production CLI is
`record-review.py --disposition`. Compatibility routing is in Reviewer runtime,
local-unit, task-policy and worker inherited-packet resolution. No prompt patch.

Runtime baseline: `benchmarks/work/capability-fit/reviewer-boundary-baseline-1/`.
Complete frozen runtime: `reviewer-boundary-complete-1/` in the same directory.
Intermediate snapshots remain, documenting implementation/packaging stages.
Original cases and reports: `reviewer-evidence-1/`, unchanged.
Final replay and scope audit: `reviewer-boundary-final-1-results/`.
Initial replay: `reviewer-boundary-1/`, retained (driver formatting changed later).
Replays use `benchmarks/reviewer_boundary_replay.py`; the final artifact records
its current hash. Full regression XML: `benchmarks/work/reviewer-boundary-regression-3.xml`.

The final scope audit records owned changed files, added modules/tests, unchanged
prompt/config evidence, document hashes and the continued formal-release HOLD.
Only new records were written; no prior acceptance decision was edited.
