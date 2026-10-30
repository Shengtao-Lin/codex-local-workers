# Repeated failed-validation no-op boundary

2026-10-10. Weekly used started and last observed at 47%; ceiling 50%.
Stage decision: accept the deterministic early-stop candidate for supervised
use. No model/prompt changes, new semantic cases, sibling edits or commit/push.
Formal Reviewer semantic release and Coordinator remain HOLD/disabled.

## Change and reason

The previous real-module trial exposed an incorrect Primary contract, then
Coder repeated identical find/replace actions instead of requesting revision.
The runtime already permits REQUEST_CONTRACT_REVISION/FINISH_BLOCKED. It did
not, however, distinguish repeated no-op edits after a failed validation from
generic protocol-error exhaustion.

The single candidate counts identical SAFE_REPLACE actions only while failed
validation is pending on the current draft. The second occurrence returns
failed with repeated_noop_after_failed_validation and an explicit instruction
for Primary to compare the actual diff, immutable failing validation and intended
contract. It never declares a test stale, revises the contract, edits/tests,
revalidates, dispatches Reviewer or accepts the unit. A real edit resets the
counter. One occurrence retains normal bounded repair/revision exits. Existing
unvalidated/prevalidation no-op handling and successful repair remain intact.

Primary classified this runtime-control unit high risk, reviewed every candidate
hunk against the frozen dirty baseline, and ran broader regression. The base
runtime had existing user changes; those and all earlier results are preserved.

## Evidence

- Focused worker regression: **178 passed, 47 subtests passed**.
- Full unchanged test set: **1017 passed, 137 subtests passed**. Runtime lint and
  format pass. The three new tests cover early stop/no edit/no repair/no extra
  validation, one-no-op successful recovery/reset, and non-failed/unrelated-error
  exclusions. Existing successful/prevalidation/failed repair controls pass.
- Deterministic historical-input comparison uses the exact source, protected
  tests and erroneous original contract from reviewer-real-unit-1. Actual pytest
  reproduces 19 passes and the same two integration assertion failures in both
  arms. A scripted no-op tail drives the runtime; this is not raw model-output
  replay or new LM Studio work. Baseline stops after four no-ops (six scripted
  turns); candidate after two (four turns), with actionable Primary guidance.
- Both arms execute one validation, no source/test edits and zero local repairs.
  The original failed archive hashes remain unchanged. **Zero new model calls**;
  do not infer model-quality or time/cost savings from two fewer scripted turns.

The first full regression encountered PermissionError accessing the system
pytest temp directory: 715 passed and 302 setup errors. Its XML is retained.
The same test set passes using a new explicit workspace basetemp; no exclusion,
old-directory deletion or test change was used to remove the infrastructure error.

Two preliminary replay-driver failures are also retained: the scripted client
initially lacked context metadata, then the audit read singular failure instead
of the actual JUnit failures field. The third replay corrects only those driver
issues. They are not worker-quality failures or successful repeats.

## Records and next boundary

Baseline and candidate snapshots are under benchmarks/work/capability-fit as
noop-primary-baseline-1 and noop-primary-candidate-1. The final deterministic
comparison is noop-primary-replay-3/results.json; initial replay directories
remain. Driver: benchmarks/noop_primary_replay.py. Regressions:
benchmarks/work/noop-primary-focused-1.xml, noop-primary-full-1.xml and
noop-primary-full-2.xml. The first exact failed project trial is unchanged.

Only worker-runtime.py, its existing test module and the matching AGENTS rule
change in the production kit for this candidate. No acceptance, edit scope,
contract-adjudication or Reviewer handoff gate is relaxed. Snapshot scope audit
and immutable stage decision retain the candidate evidence. The new rule handles
SAFE_REPLACE; it is not a claim to solve every no-progress action family.

Next: freeze this candidate as the new supervised baseline and use a normal
bounded unit under a reviewed, consistent contract. Do not repeatedly force the
known impossible contract through real models. A contradictory or unclear
acceptance remains Primary's responsibility. Repeatability, formal semantic
release and an economic advantage still require separate evidence.
