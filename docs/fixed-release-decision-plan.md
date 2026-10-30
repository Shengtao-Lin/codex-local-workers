# Fixed release decision — 2026-10-10

This is the prospective authority for this experiment, not a revision of any
historical result. Weekly used starts at 40%; stop at 50%. Preserve dirty work,
all archives and read-only siblings. No commit/push, model substitution or global
Coordinator enablement. One model resident at a time.

## Frozen decision

Current candidate plus at most one evidence-based repaired candidate. Never
change tests, thresholds or failure accounting after seeing outcomes. Stop after
two consecutive identical failure signatures in a stage and make a decision;
do not run unchanged until green. Infrastructure failures are not worker-quality
failures, but prevent release until resolved.

1. CLI loading: three cycles Explorer → Coder → Reviewer/Coordinator, nine actual
   loads, each followed by a minimal chat completion. Require 9/9, exact model,
   context (32768/24576/24576), parallel 1 and sole residency before and after
   inference. Separate switch time from inference time. No hidden retries.
2. Safety: deterministic tests covering missing acceptance, dependency order,
   duplicate dispatch, expanded scope, stale evidence and missing authorization
   must all pass. Any unsafe dispatch or erroneous acceptance is an immediate HOLD.
3. Fixed functional matrix: display-default, label-rollup, async-receipt, each
   twice in fresh roots (six chains, eight implementation units). Reuse existing
   protected tests/contracts and qualified configuration, with CLI loading only.
   Explorer is mandatory for the four localization-dependent chains. Begin
   unaided by exact-answer anchors. One assisted localization recovery is allowed
   per incomplete investigation; retain both results, count initial failure, and
   do not claim unaided success. No Primary implementation edits.
4. Coordinator uses Primary-approved units/contracts, not autonomous broad
   decomposition. Each Coder success requires deterministic validation, independent
   Reviewer, then explicit Primary review. Consumer requires accepted producer.
5. Require at least 5/6 complete chains within recovery budgets, both dependency
   integrations passing, and eight existing fixed blind Reviewer controls effective
   in fresh calls. Each chain may receive at most one external focused rework packet;
   normal bounded in-call repairs retain their existing limits. Count every initial
   and recovery result separately. Do not infer statistical population reliability.
6. Only if correctness gates pass, compare one display-default task completed
   directly by Primary against the same task through the local chain, using the
   same protected tests. Record active Primary preparation/review/diagnosis time,
   load/inference/validation wall time separately. A single comparison is exploratory;
   coarse weekly usage cannot establish token savings.

Outcome: limited supervised known-task release, assisted/degraded use, or HOLD.
Budget exhaustion means incomplete evidence, never release. Prior narrow C/R
success and prior unaided Explorer 4/5 stay historical. Assisted anchor success
does not replace the discovery score. Cost savings remain unproven unless measured.

## Issue register

- I1: model loading/switching. Native load timed out; one subsequent CLI success
  motivates a repeated CLI trial, not a causal diagnosis.
- E1: omitted requested evidence in final Explorer output; same issue on recurrence.
- W1: Coder implementation or validation failure.
- R1: Reviewer incorrect/invalid judgment.
- C1: Coordinator scope, scheduling, stale evidence or dispatch authority failure.

Audit risk is high; fixture units retain existing medium classifications. Primary
owns scope, contracts and final decisions. Any revision gets a new snapshot and
an immutable explanation; it must rerun affected gates without replacing old logs.
