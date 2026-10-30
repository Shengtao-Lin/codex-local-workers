# Fixed candidate: registered two-unit repeat batch

2026-10-10 local date. Weekly used 48% at start and last observation; ceiling
50%. Requested batch completed, no commit/push or sibling edits. Candidate,
models, prompts, contracts, protected tests and original acceptance gates stayed
unchanged. Historical records are retained.

## Registration and result

Before any model call, register two new clean repetitions of each previously
passing unit, alternating timestamp and async. All four isolated copies are
restored from hash-checked original authorized-file preimages and unchanged
protected files, not from successful implementations. Only task/feature/run
identities change in the canonical packets; risk and behavior remain unchanged.
One Coder call per cell, automatic fresh Reviewer, no external rework or retry.
Each cell needs original deterministic validation, Reviewer pass and independent
risk-routed Primary acceptance. Any terminal failure counts against the batch.

| Cell | Independent tests | Coder protocol errors | Reviewer protocol errors | Local-unit seconds | Primary |
| --- | ---: | ---: | ---: | ---: | --- |
| timestamp-r1 | 21 passed | 1 | 1 | 79.3 | accept |
| async-r1 | 2 passed | 0 | 1 | 44.6 | accept |
| timestamp-r2 | 21 passed | 1 | 0 | 83.0 | accept |
| async-r2 | 2 passed | 1 | 0 | 48.0 | accept |

Coder readiness **4/4**, automatic Reviewer passes **4/4**, end-to-end Primary
acceptance **4/4**. No terminal worker or model-launch failure occurred. Protocol
corrections remain visible: five rejected actions across these calls, recovered
within the original bounded calls. Both timestamp Coder corrections were
`VALIDATE requires contract_check for this packet`; they were not edit failures.
The batch does not require zero protocol corrections and the gate was not changed
to hide them.

Each timestamp result has the same sole outer-whitespace strip before the
existing ISO parser. Primary reviews the full changed module and public adapter
path for the first result, then verifies exact full-file identity plus actual
diff and protected hashes for the second. Independent complete copied-fixture
pytest, Ruff lint/format and Pyright all pass. Both async results implement the
same sequential await and None-only break; independent pytest, Ruff and public
entry probes pass, including false-value identities and exact stop sequence.
Protected tests also verify original exception identity and empty-input behavior.
Immutable Primary reviews exist for all four cells; automatic handoff did not
itself authorize acceptance.

Reviewer execution varies legitimately: timestamp-r1 acknowledges trusted
runtime checks without additional execution; timestamp-r2 executes approved
static checks and tests; both async Reviewers execute approved focused tests.
There is no claim that all Reviewers ran every check independently.

## Test-tool failures retained separately

The original registered runner's audit command completed timestamp-r1 independent
checks, then failed to collect `protocol_error_count` from the compact report.
An initial independent collector then failed on both first-round cells because
canonical handoff does not use the compact `validation_summary` shape. These
three audit-command failures are not worker failures and are not erased.

`audit-tool-errors.json` records them. The registered runner is untouched. A
separate collector reads each field from its actual report schema and reuses
existing independent command records without overwriting or rerunning them.
Only the collector was corrected; no model run, contract, fixture, production
runtime or pass standard changed. These are real benchmark-tool defects, so
this batch must not be described as entirely infrastructure-error-free.

## Bounded conclusion

The unchanged candidate is repeatable **in this registered four-run batch on
these two already-exposed units**. Together with the earlier individual trials,
each unit has three observed passing runs on the fixed candidate, but the earlier
trials are not folded into this batch's denominator. Four successes do not prove
a general success rate or unseen complex-task stability.

No new Explorer localization question was present: zero Explorer calls/credit.
Coordinator remains disabled. Models and single-residency configuration remain
unchanged; physical GPU residency was not independently measured. The async
fixture is Primary-authored and the timestamp fixture is a previously exposed
real-module copy, not a full sibling deployment. Formal sixteen-case Reviewer
semantic release remains **HOLD**, preserving the prior 14/16 outcome.

Measured local-unit windows total about **254.9 seconds**. Primary preparation,
active reasoning, independent audit time, cloud tokens and a direct-Primary
comparator are not measured; no savings claim follows. No new full kit runtime
regression is claimed, since the runtime did not change.

Stop this batch with a clear bounded pass. Keep the candidate frozen rather than
adding prompts in response to recoverable protocol corrections. A subsequent
stage should test a pre-registered, different failure-sensitive or small real
unit; do not substitute more repeats of these easy units for the outstanding
Reviewer semantic gate, or infer autonomous Coordinator readiness.

## Records

`benchmarks/work/capability-fit/fixed-candidate-repeat-1` retains registration,
exact registered driver, audit-tool errors, stage decision and four isolated
cell directories. Each `.agent` includes canonical Coder/Reviewer history,
validation attempts, live output/timing, independent command outputs,
`independent-repeat-audit.json` and immutable Primary `review.json`.
Runner: `benchmarks/fixed_candidate_repeat.py`; independent collector:
`benchmarks/fixed_repeat_audit.py`. Runtime snapshot:
`benchmarks/work/capability-fit/transfer-candidate-runtime-1`, hash-matched to
`noop-primary-complete-1` before every run/audit.
