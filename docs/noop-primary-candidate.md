# Failed-validation no-op termination candidate

2026-10-10. Weekly used ceiling 50%, start 47%. One deterministic runtime
candidate, no prompts/models/semantic-case changes. Baseline frozen as
benchmarks/work/capability-fit/noop-primary-baseline-1. Existing real-unit-1
failure remains immutable; this is a new experiment, not relabeling it.

Primary owns this high-risk runtime-control unit: termination must never allow
unvalidated acceptance or bypass contract/scope/Reviewer gates. No dependencies.
Owned invariant: repeated identical SAFE_REPLACE actions after failed validation
do not edit source or consume local repairs; the second occurrence on the same
draft returns failed with an actionable Primary contract/source/test decision.
One occurrence retains a chance to edit, validate or explicitly exit. Real edits
reset the draft counter. Reads and other protocol errors are not progress.
No inference that any test is stale; Primary decides. Successful/prevalidation
no-op behavior and all existing acceptance protections remain unchanged.

Gate: deterministic stop/recovery/reset/prevalidation controls, full current
regression and project lint/format; replay an exact archived failed JUnit/control
sequence through frozen baseline and candidate without new model-credit claims.
If candidate regresses valid repair or cannot distinguish the archived failure,
retain evidence and reject it. No live replay of the impossible original
contract simply to reproduce an already known failure.
