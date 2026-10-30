# Fixed candidate: frozen async unit transfer

2026-10-10. Weekly used 47%; ceiling 50%. One different frozen unit completes
Coder → automatic Reviewer → independent Primary acceptance. The production
candidate, models, prompts and release standards remain unchanged. No commit,
push, sibling-repository edits or historical-result replacement.

## Frozen comparison

The `async-stop` unit comes from the existing `supervised-scope-1` corpus. It is
a previously exposed, Primary-authored fixture, not a new real-project task or
an unseen benchmark. Its original implementation, protected tests, caller,
contract, scopes, acceptance scenarios, validation profile and medium
feature/unit/integration risk are reproduced in a new isolated directory.
The new runtime snapshot and live candidate hash-match `noop-primary-complete-1`.

The unit requires sequentially awaiting each fetch, stopping only at the first
`None`, retaining `0`, `False` and the empty string, preserving the input keys,
and propagating the original exception without visiting subsequent keys. This
differs from the preceding timestamp-normalization unit.

One call was registered, with no retry, contract adjustment or protected-test
edit. Qwen remains Coder and Muse remains Reviewer; single-model residency and
concurrency one remain configured. Actual GPU residency was not separately
measured. Explorer was not invoked because definition, caller and tests were
already located and read; no Explorer success is credited. Coordinator remains
disabled.

## Observed result

- Preflight: both original tests fail on the unchanged starting implementation.
- Coder changes only `src/product/target.py`, introducing sequential `await`
  and a `None` sentinel break. Final validation: **2 passed**, Ruff lint and
  format passed; zero protocol errors and zero repair cycles.
- Three immutable validation attempts remain: one failed pre-edit baseline and
  two passed post-edit attempts. The failed baseline did not prevent editing.
- The verified handoff automatically launches Reviewer, which reads all five
  source/test files, cites the implementation, acknowledges the actual Ruff
  results and returns `pass_to_primary` with zero protocol errors. Its approved
  execution list is empty: it did not independently execute tests.
- Primary reads the actual cumulative diff, implementation, public caller and
  protected tests. Independent pytest again reports **2 passed**; Ruff lint and
  format pass. A separate public-entry probe confirms false-value identities,
  stop position, call sequence and unchanged keys. Protected-file hashes match.
- Immutable Primary `accept` is recorded for this unit. The local-unit command
  window is **51.7 seconds**, not total Primary working time or a separately
  measured model-loading time.

The trial supports limited near-transfer of the unchanged candidate across two
different unit types. It does not establish repeated-run reliability, unfamiliar
repository performance, model interchangeability or economic savings. Formal
sixteen-case Reviewer semantic release remains **HOLD**; the prior 14/16 result
is not replaced. Cloud tokens and Primary active time remain unmeasured. The
earlier full runtime regression is historical evidence, not a newly executed
full suite in this trial.

## Evidence and next boundary

Records are under `benchmarks/work/capability-fit/transfer-candidate-1`:
`registration.json`, exact `registered-driver.py`, `audit.json`,
`stage-decision.json`, and the isolated run directory
`runs/v1/transfercand/async-stop-round-1`. Its `.agent` retains preflight output,
local-unit timing, canonical Coder and automatic Reviewer archives, all three
validation attempts, independent Primary command output and immutable review.
The runtime snapshot is `transfer-candidate-runtime-1`.

Runner: `benchmarks/transfer_candidate_trial.py`. After execution, an unused
audit-local binding was renamed for Ruff; the exact pre-registered driver is
retained. No runtime, fixture, contract or model execution was changed or rerun.

Keep the candidate frozen. The next useful evidence is a pre-registered repeat
of these distinct units, with per-run failures retained and no mid-batch fixes;
this single pass does not authorize autonomous Coordinator release.
