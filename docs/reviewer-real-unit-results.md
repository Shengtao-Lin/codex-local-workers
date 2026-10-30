# Real-module supervised unit trial

2026-10-10. Weekly used 46% at start, 47% last observed; ceiling 50%.
Stop reason: a checkable bounded-stage conclusion. No commit/push, sibling
writes, runtime/prompt/model changes or Coordinator activation.

## Result

One additive timestamp feature was attempted on an isolated copy of the frozen
real agent-evaluation-harness adapter modules. This is not an authorized feature
deployment to the sibling project. Existing source was copied unchanged, not
deliberately broken. The feature accepts outer whitespace in ISO timestamp
strings while preserving parsing errors, timezone rules, datetime/default
identity, raw source evidence and adapter trace/turn behavior.

The accepted-input compatibility boundary imposed **high** feature, unit and
integration risk. Coder owned only common.py; all tests and remaining source
were protected. Existing pytest/Ruff/Pyright project settings were inspected.
Pyright was explicitly included in the trusted validation profile. No packages
were installed. Explorer was not invoked because the helper, caller and tests
had already been read and located; there is no new Explorer success credit.

There were two separately registered contracts, not two passing repetitions:

| Trial | Outcome | Local command window |
| --- | --- | --- |
| Original contract | replan: Primary-authored equality requirement was wrong; Coder failed after repeated identical replacements | 22.7 s |
| Explicit contract revision | accepted isolated unit: Coder, automatic Reviewer, high-risk Primary review and integration regression pass | 81.3 s |

The original acceptance incorrectly compared entire CanonicalSample objects
between padded and unpadded input. Actual source_metadata retains the raw
event_time string, so those samples should not be wholly identical. The only
production edit, adding strip() before existing parsing, passed 19/21 tests;
the remaining two failures were the incorrect equality assertions. Primary owns
that contract mistake. Coder nevertheless repeatedly attempted unchanged edits
instead of using REQUEST_CONTRACT_REVISION, consuming the bounded protocol-error
budget. Its failed archive and Primary replan decision are preserved.

The second trial starts from the same original source in a separate root. Its
new registered contract compares all sample fields except the raw timestamp
entry, and explicitly requires that entry to preserve the exact padded input.
The first test/packet/registration/result are not edited or relabeled. This is a
disclosed contract correction, not a weakening of a legitimate invariant.
The original fixed sixteen-case Reviewer gate is unchanged.

## Executed evidence

- Each preflight: original ten tests pass; eleven added feature checks produce
  five expected failures and six passes before implementation. Pyright reports
  zero type errors. Initial copied-project Ruff lint and format pass.
- Revised Coder: **21 executed, zero failures/errors/skips**, current validation
  inputs unchanged; Ruff format/lint and Pyright pass. Only common.py changes,
  with the single addition of strip() in the existing string branch.
- Automatic independent Muse Reviewer: pass_to_primary, zero protocol errors,
  source-backed owned-contract quotation at the private helper, source and
  protected tests actually read. It runs approved tests (21 pass), Ruff and
  Pyright, rather than claiming unperformed validation.
- Primary: full changed-file and actual cumulative-diff review at high risk;
  independent complete **copied fixture** regression (21 pass), Ruff and Pyright
  pass. Normalized samples, IDs, runtime/messages, offset/wall time, JSON
  roundtrip and nonmutation are covered for trace and turn modes. This is not
  the complete sibling repository, PostgreSQL or MLflow validation.
- Hash audit: protected tests/config/packet, original real fixture and frozen
  runtime unchanged. Actual source equals original plus precisely the one
  recorded strip() change. Immutable Primary accept follows the independent
  passing Reviewer; there is no false-positive acceptance override.

Pyright emits informational missing local .venv/update notices; the interpreter
is explicitly the existing sibling venv, and diagnostics report zero errors,
warnings or informations. No dependency installation or environment repair was
performed. Single-model-residency configuration and concurrency one are retained;
local calls are sequential, not an independent GPU residency measurement.

## What this establishes, and what it does not

The revised contract demonstrates one live high-risk supervised unit on real
modules. It does **not** establish repeatable stability, real-project deployment,
autonomous semantic Reviewer release or reduced Primary work. Formal Reviewer
semantic gate remains HOLD at the prior 14/16 result. Global Coordinator remains
disabled. The previous two synthetic-parent repair-chain passes remain distinct.

Command windows and preparation-script durations are measured, but Primary
active reasoning/preparation/adjudication time and cloud tokens are not
instrumented. No comparable direct-Primary run was measured. Therefore the
planned economics comparison is incomplete and no savings claim is made; this
tiny source edit would not by itself justify delegation for efficiency.

The next improvement should target **early Primary contract adjudication after
a repeated validation failure**, not more Reviewer prompt examples or a larger
semantic test set. Existing repair-only schemas already allow
REQUEST_CONTRACT_REVISION and FINISH_BLOCKED; this observed failure is not proof
that the runtime removed those exits. Preserve the current safety boundary and
use the failed archive to test whether duplicate-edit termination surfaces a
clear, actionable Primary decision instead of spending more model turns.
Any runtime candidate should be separately frozen and tested against existing
negative/regression controls before another live experiment.

## Retained records

Under benchmarks/work/capability-fit:

- reviewer-real-unit-1: original registration, exact registered driver,
  preflights, failed Coder/validation/JUnit/diff, immutable Primary replan.
- reviewer-real-unit-2: revised registration, exact registered driver,
  preflights, actual Coder and auto Reviewer archives, Primary acceptance,
  independent regression/static-command outputs and audit.json.
- reviewer-real-unit-runtime-1 and reviewer-real-unit-runtime-2: frozen runtime
  snapshots for each trial; production runtime is not changed this round.

The runner is benchmarks/reviewer_real_unit_trial.py. The two Primary-authored
protected tests are separately retained in real-adapter-datetime-extra as
test_timestamp_whitespace_trial.py and test_timestamp_whitespace_trial_v2.py.
Post-run audit additions do not alter the retained registered-driver hashes.
