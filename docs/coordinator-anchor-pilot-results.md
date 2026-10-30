# Assisted localization pilot: loading infrastructure blocks the chain

## Outcome

HOLD full-chain qualification. The existing source-anchor gate solves the known
omission in a deterministic replay, and one fresh assisted Explorer call was
complete. Coordinator selected the approved producer and produced a valid bounded
packet, but Coder never reached its first model turn. No implementation changed;
Reviewer and the dependent consumer were not run.

Evidence: `benchmarks/work/capability-fit/coordinator-anchor-pilot-1/`, especially
`deterministic-preflight-1.json`, `loading-diagnostic-1.json`,
`primary-stage-decision-1.json`, and the isolated root's `.agent` archives.

## Separate conclusions

- The previous incomplete answer is mechanically rejected with the two existing
  required-source-anchor obligations. Replacing the duplicate collector citation
  with actually read round-trip test lines passes. No model credit for this replay.
- The fresh assisted call cites entry, receipt, collector, collector-order and
  round-trip tests, with zero protocol errors. This is 1/1 **assisted** localization,
  not a revision of the previous unaided 4/5 candidate result.
- The new pilot wrapper requires Primary semantic approval bound to the report
  hash, plus unchanged anchor citations, before calling Coordinator. This is a
  pilot safeguard, not a global product change or automatic semantic verification.
- Coordinator decision and proposal passed; this establishes only the first
  bounded dispatch attempt, not dependency scheduling or end-to-end completion.
- Coder was blocked by `model_switch_failed`, `stage=load_native`, after 361.828
  seconds. This counts as infrastructure failure, not Coder quality failure.
- Subsequent CLI loading of the same Qwen succeeded in reported 8.15 seconds.
  Inventory confirmed one model, context 24576, parallel 1. Different starting
  states and a single observation prevent attributing the underlying cause.

## Validation and next step

Explorer regression: 72 tests and 29 subtests passed. Runtime and fixture hashes
remained unchanged; `git diff --check` passed. The new frozen benchmark driver has
one cosmetic Ruff SIM102 nested-if warning; retain its executed version and fix
that style in the successor before registration. No claim of all-green lint or
a newly executed full repository regression is made.

Next use the existing `model_load_backend: cli` with trusted absolute
`model_load_cli_path` in a new isolated config. Keep all current role models,
contexts and single-model residency. Run the full two-unit chain, recording
Primary acceptance before the dependent unit and independent final integration.
Do not overwrite the native-loading failure or treat the CLI load alone as a
successful worker run. Keep global Coordinator disabled.

Weekly used: 38% to last observed 39%, ceiling 40%. Stopped at this auditable
stage decision, not quota exhaustion. No commit/push or sibling modification.
