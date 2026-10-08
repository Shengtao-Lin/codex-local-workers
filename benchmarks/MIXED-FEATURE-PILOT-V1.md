# Mixed feature pilot v1

This is a six-goal corpus preparation and pilot, **not a completed two-round
release gate**. Never pool it with the earlier localization cohort.

The preregistered recipe is `fixtures/mixed-features-v1.json`:

- bounded report configuration → report selection, two dependent medium-risk units;
- asynchronous SQL aggregate → read-only summary response, two dependent high-risk units;
- real reuse-scores task, one atomic high-risk unit;
- real score-summary API task, one atomic high-risk unit;
- SWE-bench Lite `pallets__flask-4992`, config file loading modes;
- SWE-bench Lite `pallets__flask-4045`, blueprint name validation.

Two public tasks share Flask to keep preparation modest; this is not broad
repository diversity or a statistically significant general benchmark.
Their exact base commits and acquired source hashes are frozen. Docker is not
running, and the existing diagnostic interpreter lacks Flask dependencies.
Public native environment/test preflight remains pending. No official SWE-bench
score is reported. Public acquisition uses an explicit task-field allowlist;
reference patches, test patches and hints are not forwarded to worker snapshots.

Real-task snapshots combine current read-only context/tests with hash-verified
archived writable-file preimages. The summary acceptance test comes from the
saved pre-write checkpoint. These are **adapted replays**, not exact original
execution inputs. Detailed snapshots are retained under ignored
`benchmarks/work/mixed-v1/candidate-1/sources/`; no source project was modified.
The summary baseline independently collected eight tests: six failed, two passed.

## Pilot observations

Both authored round-one goals reached Coder via real Muse Coordinator and OSS
Explorer calls. The Coordinator uses Primary-approved unit boundaries; this
measures supervised proposals/routing, **not independent feature decomposition**.
Testing decomposition proposals requires a separate read-only proposal stage and
Primary approval before execution; the runtime's qualified scope is unchanged.

The bounded-report first unit edited and validated, but accepted float 1.5 and
raised TypeError for None instead of ValueError. Final validation had two failures
and thirteen passes; no-op replacements exhausted the protocol-error budget.
Primary recorded `replan`, without takeover or crediting feature acceptance.

The async-query first unit introduced a reference to `stmt` before assignment,
duplicate count bindings and missing await. It did not perform post-edit
validation; target-missing errors exhausted the protocol budget. Primary recorded
`replan`. Reviewer correctly did not start in either goal, and dependent second
units were not dispatched. These are two failed feature pilots, not four attempted
units and not evidence about Reviewer quality.

One preparer schema rejection happened before any model turn: scenarios omitted
observable fields. The corrected candidate uses a separate workspace; the first
preparation is retained and does not count as a model-quality failure.

## Continue without hiding failures

Do not run all remaining rounds while the same mechanical blocker is untreated.
Finish native public/real replay preflight, review fixture completeness, and add
a bounded edit-mismatch/post-edit validation diagnostic. Preserve pilot failures.
Any runtime, corpus or role change starts a new frozen candidate, never overwrites
old records. Model comparison uses identical frozen snapshots and contracts.

Final acceptance requires all units' actual tests/static checks, fresh Reviewer,
immutable Primary decisions, and whole-feature integration. Zero tests, partial
features, skipped dependent units and Primary implementation are not local-worker
successes. Cloud tokens remain unknown; account percentages are budget signals.

## Targeted edit/validation patch and candidate 2

Target-missing replacements no longer reset post-edit evidence counters. If a
draft already changed and has no current validation, a mismatch requires VALIDATE
before further edits. Bounded current-line suggestions are navigation only and
lead to a current READ_FILE, not authority to apply approximate replacements.
Invalid VALIDATE field shapes do not release the draft gate; only an actual
validation observation does. Regression covers rejected additional mutation,
current-file validation and invalid-argument gate retention.

Candidate 2 reran the first async-query unit in a separate frozen workspace.
Coordinator and Explorer again routed successfully. Coder performed three actual
validations, two after edits, but kept the missing await and non-aggregate query,
then explicitly finished failed. Primary recorded `replan`; no feature acceptance,
Reviewer call or Primary implementation is credited. No target-mismatch gate
event occurred: this sample does **not** establish a live-model benefit from
that specific branch. The later invalid-VALIDATE hardening is deterministic-test
verified and was not part of candidate 2's frozen runtime.
