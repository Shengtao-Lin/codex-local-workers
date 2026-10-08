# Complex reliability coverage, revision 2

This is an engineering test corpus, not v2.1 release acceptance. Existing v1
recipes and execution records remain unchanged. Select the expanded corpus with
`mixed_feature_benchmark.py prepare --suite complex-v2`.

## Added coverage

- ASCII-only configuration rejection, Unicode numerals, trailing newline,
  container inputs and float coercion, retaining the existing public round-trip.
- One high-risk atomic unit spanning publication and evidence-copy modules:
  eligibility, lease-before-write, awaited write/commit, rollback and exception
  propagation. Protected tests verify event order and observable state.
- A dependent medium-risk summary unit: exact run identity, failed-history
  denominator, successful-only reuse provenance and nested mutation isolation.
- Primary-only reference repair and eight seeded defects verify the seven
  protected business assertions. Reference code stays outside worker snapshots.
- Batch-qualified invocation identities, frozen driver hashes and pre-dispatch
  verification of corpus and protected-test hashes. Source edits are allowed;
  changing protected tests or the driver requires a new frozen batch.

Primary still defines the units. This does not test autonomous decomposition.
The synthetic lease interface does not establish real database concurrency or
PostgreSQL isolation. Public benchmark snapshots remain a separate layer.

## Observed results

The first `coverage-1` atomic-publish pilot used the existing models serially:

- Coordinator generated an in-scope two-file packet.
- Explorer returned five verified source references.
- Coder added eligibility and lease checks but left shallow copying and absent
  rollback. Final focused validation: six executed, three failed.
- Coder requested evidence.py permission already present in its packet. This
  did not justify expanding scope. Primary recorded immutable `replan`.
- Reviewer and the dependent summary were not run. Feature not accepted.

The pilot was frozen before explicit structured ordering constraints were added;
its original textual ordering contract and archived packet remain authoritative.
Do not rerun it with the changed driver. Use a new batch for the next experiment.

Deterministic regression before that final ordering addition: 485 passed,
28 subtests passed; two known externally drifted source-pin tests excluded.
Latest focused verification is recorded separately, not conflated with that run.

## Next experiments

1. Inherited anchored rework for evidence copying and rollback, retaining both
   files in the same atomic unit; no blanket turn-budget increase.
2. Exercise the fresh independent Reviewer after a validated unit, plus a clean
   control/hidden-defect diagnostic independent of Coder success.
3. Replace the older SQL service fixture's one-method fake result with actual
   SQLite/SQLAlchemy results before broadening SQL API coverage. Do not treat a
   valid alternative result-access API as a worker failure.
4. Repeat complete goals in frozen batches and report role success, integration
   acceptance and infrastructure failures separately. No Primary takeover credit.

## Follow-up: inherited repairs and uncovered exception boundary

The inherited a2 repair passed six protected tests and both Ruff checks. The
runtime automatically started Muse Reviewer; it read both implementation files
and the focused tests and returned `pass_to_primary`. Independent Primary review
then executed a rollback-failure probe: rollback RuntimeError replaced the
original write OSError. This violated the existing contract; a2 was recorded
`rework`, not accepted. Retain this Reviewer false negative.

The a3 inherited call made no cumulative source change. Old tests passed before
the intended edit, triggering the existing validation terminal gate. Reviewer,
with the concrete failure feedback, correctly returned the exception-masking
finding. This is feedback-assisted detection, not independent first-pass success.

Primary created a new a4 packet revision with an additional read-only protected
test for write/commit failure followed by rollback failure. Old archives and
validation records were untouched. Coder made edits but ended with the same
source hash; three validations still reported two failures out of eight tests.
No Reviewer or dependent summary ran for a4. Feature remains unaccepted; do not
repeat the unchanged failure or claim end-to-end success.

Future complex fixtures now include both rollback-failure cases and a ninth
seeded defect. Their Primary-only reference implementation preserves the
original exception even if rollback fails. SQL service fixtures now return real
SQLAlchemy results: both tuple access and `mappings().one()` reference variants
pass. The v1 recipe is unchanged.

Follow-up regression: **489 passed, 28 subtests passed, 2 deselected**. The two
exclusions remain external source-pin drift. No source-project writes, commits
or pushes. The remaining model issue is focused exception repair, not context
overflow; a4's observed context utilization was below 50 percent.

## Independent Reviewer qualification controls

`complex_reviewer_challenge.py` creates isolated, explicitly synthetic archives;
it never invokes Coder and cannot establish Coder or feature success. Normal-path
tests and Ruff execute against the exact source before review. A Primary oracle
outside packet-readable src/tests verifies the hidden failure or correct control.
No previous finding or review feedback is supplied. Each invocation has a unique
identity. Later controls freeze source, configuration and driver hashes before
calling the Reviewer.

Observed with the unchanged Muse model, serially:

| Reviewer instruction | Hidden rollback defect | Correct cleanup control |
| --- | --- | --- |
| Existing prompt | Missed; passed to Primary | Passed without findings |
| General cleanup-failure reasoning added | Missed; passed to Primary | Passed without findings |

These are one trial per cell, not a statistical success rate. They show that
protocol success and green normal-path tests do not establish semantic review.
The new guidance asks which exception reaches the caller if cleanup fails, while
allowing any contract-compliant code shape; it is not a proven quality improvement.
Do not release high-risk independent review on this evidence.

One initial clean-control preflight failed Ruff before the model started because
the reference used `except/pass`. The corrected control uses `contextlib.suppress`
and passes the same configured checks. That preflight is fixture infrastructure,
not a model-quality failure. The original pilot remains unaccepted.

Next qualification must add an independently scored error-path obligation or
evaluate another explicitly authorized Reviewer candidate against the same hidden
and clean controls. Do not simply repeat the unchanged failed prompt. Keep
deterministic protected boundary tests and high-risk Primary review mandatory.

Final regression after formatting repair: **496 passed, 28 subtests passed,
2 deselected**. Disposable installation checks also passed (five tests).
