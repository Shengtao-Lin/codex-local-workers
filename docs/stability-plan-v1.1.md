# stability-plan-v1.1.md

## 1. Objective

Stabilize the current architecture (`AGENTS.md`, v1) before resuming
`improvement-plan-v2.1.md` at Phase 2. This is a diagnostic and bug-fixing
pass on the existing Explorer/Coder/Reviewer pipeline — not an architecture
change, and not a prerequisite for every part of v2.1: Phase 1
(Coordinator schema/contract authoring) does not touch live routing and may
proceed in parallel with this plan.

## 2. Why This Comes First

`improvement-plan-v2.1.md`'s efficiency case (§22) assumes the local
specialists converge on their own most of the time — that is what lets a
Coordinator absorb orchestration work without adding a second layer of
failures for Primary to clean up. Recent runs under v1 show unresolved
convergence problems at the Coder and Reviewer level (§3). If a Coordinator
is introduced before these are understood:

- every Coordinator-routed failure will need to be triaged against the
  possibility that it is one of these already-known issues, which makes
  both the old and the new bugs harder to isolate;
- local compute will be spent retrying inside the Coordinator's rework
  loop before reaching the same escalation v1 would have hit directly,
  which is a net cost, not a saving.

Fixing what's described below improves the system in use today regardless
of whether v2.1 ever ships, so this work is not a detour.

## 3. Known Failure Patterns

These are drawn from three recent runs.

### 3.1 Coder does not act on a correct `repair_focus`

Observed twice, with the same shape both times:

- **Run A:** Coder produced a working query structure, but imported the
  ORM class it needed only under `TYPE_CHECKING`, causing a runtime
  `NameError` (1 of 3 focused tests passed). The runtime's `repair_focus`
  correctly identified the guarded-import issue at its exact source
  location. Coder's next actions were further reads with no edit; the unit
  stopped as no-progress before Reviewer ever ran.
- **Run B:** Coder fixed the `NameError` from Run A and passed 3/3 focused
  tests, but a configured static check (Ruff `F821`) found `AsyncSession`
  undefined at `reuse_lookup.py:17`. `repair_focus` correctly surfaced this
  as an early repair focus per policy. Coder again only read/searched with
  no edit and stopped under "failed validation followed by no new
  evidence"; Reviewer never ran.

In both cases the runtime diagnosis and the `repair_focus` mechanism worked
exactly as designed. The gap is specifically at "diagnosis handed to
Coder" → "Coder emits an edit action." Run B is the more informative of the
two: Coder's actual code quality was sufficient to pass 3/3 functional tests,
so this does not look like a raw coding-ability gap — it looks like a
protocol / instruction-following gap that shows up specifically when Coder
is supposed to act on a runtime-supplied diagnosis rather than write new
code from a fresh packet.

### 3.2 Reviewer citation does not converge

Local Reviewer (muse-glimmer) repeatedly submitted a `source_quote` that
did not match the actual source line it was citing. The runtime's
`citation_fixes` mechanism correctly identified the mismatches and supplied
bounded correction ranges, but the citations did not converge to a valid
report within the retry budget.

### 3.3 Infra-level failure during a Reviewer retry

After switching to a different reviewer model for a fresh read-only retry,
LM Studio returned an HTTP 400 and the review attempt failed outright. This
is distinct from 3.2: it is a rejected request, not a wrong answer, and it
ended the attempt entirely rather than producing a reviewable (if
imperfect) result.

All three runs ended in a manual revert rather than acceptance.

## 4. Diagnostic Steps

### 4.1 For 3.1 (Coder not editing after `repair_focus`)

1. Pull the canonical run archive for both incidents. Read the literal
   `repair_focus` text and Coder's literal next action(s) — not a summary —
   to determine whether Coder issued a plain READ/SEARCH (protocol
   compliance, no attempted fix) or something ambiguous that the runtime
   normalized into a read.
2. Check whether the packet's `edit_targets` anchors for these units
   included the import block / top-of-file region, or only a function-body
   symbol. If the anchor didn't cover the region that actually needed the
   edit, Coder may have had no clearly authorized place to make the change.
3. If (1) and (2) are inconclusive, re-run the same repro packet with Coder
   temporarily upgraded to Q4_K_M or Q5_K_M (same quant family, higher
   fidelity) to see whether the diagnosis-to-edit gap persists at higher
   precision. This isolates whether the current IQ4_XS setting is a
   contributing factor.
4. Check the remaining context budget at the moment `repair_focus` is
   issued. If it is within a few thousand tokens of the configured 24576
   cap, treat context pressure as a suspect and re-test with a larger
   configured context length.

### 4.2 For 3.2 (Reviewer citation mismatch)

1. Pull the archive for the mismatch run. Check how many `citation_fixes`
   rounds were attempted and whether the quoted line drifted toward the
   correct one across rounds (drift = a precision issue worth tuning) or
   stayed effectively random (no drift = the model isn't grounding in the
   returned range at all, which points at the prompt template rather than
   the quant).
2. Re-run the same repro against an alternate reviewer candidate (e.g.
   Qwen fresh-context) to check whether this is muse-glimmer-specific or a
   property of the citation-fix mechanism itself.

### 4.3 For 3.3 (HTTP 400)

1. Capture the literal LM Studio response body for the failing request,
   not just the status code — it usually names the actual rejection
   reason.
2. Compare the token/byte size of the failing request against the fallback
   model's configured Context Length. If the request exceeds it, this is a
   context-length mismatch introduced by the model switch, not a model
   defect.
3. Add a pre-flight size check before dispatching to any local model: if
   estimated request tokens exceed (configured context − safety margin),
   either truncate/summarize non-essential history or fail fast with a
   labeled `infra_failure` outcome, rather than sending the request and
   receiving a raw 400.

## 5. Structural Fixes To Land Regardless of Root Cause

Treat bounded exploration as a current-v1 stability capability, not a future
Coordinator feature. The role matrix for this phase is:

```text
Explorer: READ + SEARCH + TRACE
Coder:    READ + SEARCH + SAFE_EDIT + VALIDATE
Reviewer: READ + SEARCH + APPROVED_EXECUTION + REPORT
```

`TRACE` is read-only call/data-flow traversal grounded in observed files and
lines. `APPROVED_EXECUTION` means only packet/profile-registered tests and
static checks; it is not arbitrary shell access. Coder and Reviewer must be
able to perform the bounded local discovery needed for implementation and
independent verification even when Explorer already ran. Explorer remains a
separate measured stage whenever initial location is required, and downstream
success never erases an Explorer evidence failure.

- Classify context-window overflow and malformed/rejected upstream
  requests (HTTP 4xx/5xx from the local model server) as a distinct
  `infra_failure` outcome, separate from worker-quality failure
  signatures. This extends the existing principle that a launch/
  configuration failure before the first model turn does not affect a
  worker-quality streak — the same should hold for a mid-call infra
  failure.
- For recurring repair archetypes (guarded-import placement, undefined-
  name-at-a-known-line), consider giving `repair_focus` more directive,
  template-like phrasing — e.g. "move `X` from the `TYPE_CHECKING` block to
  a top-level import" — rather than purely descriptive diagnosis, since the
  evidence in §3.1 suggests the model can read the diagnosis but isn't
  reliably converting a descriptive finding into an edit action on its
  own.
- When a packet's known bug sits outside the current `edit_targets`
  anchors (e.g. an import statement above the anchored function symbol),
  widen the anchor to include that region rather than leaving Coder to
  infer it has permission to touch it.

## 6. New Instrumentation

Needed to know whether §5's fixes actually worked, and to give
`improvement-plan-v2.1.md` §23 real numbers to compare against later:

- `repair_focus_issued` vs. `next_action_is_edit` — tracked per Coder call.
  This is the single most important ratio given the evidence in §3.1.
- `citation_fix_rounds` and `citation_converged` — tracked per Reviewer
  call.
- `infra_failure_count`, kept separate from `quality_gate_failure_count`
  and `no_progress_count`.
- Per-role discovery evidence: observed paths/lines, searches, trace edges,
  duplicate/no-evidence stops, and whether the role answered its own bounded
  question without recursive worker calls.
- Reviewer approved-execution attempts/results keyed by registered action id,
  plus rejected unregistered execution attempts. Keep these separate from
  Coder validation evidence.

## 7. Baseline Measurement

1. Select roughly 10–15 representative units from recent real work,
   spanning small/medium risk (skip anything that would already route
   straight to Primary regardless of whether a Coordinator exists).
2. Re-run them under the current, patched v1 pipeline.
3. Record: % reaching Local Reviewer, % reaching acceptance without a
   manual revert, the `repair_focus_to_edit` conversion rate, the citation
   convergence rate, and the infra-failure count.

This baseline is what `improvement-plan-v2.1.md` §22's efficiency claims
get compared against later. Without it, "the Coordinator saved X%" has no
denominator.

## 8. Exit Criteria (resume `improvement-plan-v2.1.md` Phase 2 when all hold)

- The `repair_focus_to_edit` conversion rate has materially improved from
  the ~0% observed in the three incidents in §3. "Still near zero" is a
  clear no-go.
- Reviewer citation convergence is reached within the existing retry budget
  for the sampled units, or a specific root cause (e.g. quantization) has
  been identified with a fix in progress.
- Zero unhandled infra-level failures (HTTP errors, context overflow) in
  the baseline run — these should now be caught pre-flight or classified
  separately, not silently ending the run.
- An actual baseline convergence number from §7 is recorded, whatever it
  turns out to be.
- The three-role capability matrix in §5 is enforced by schema/runtime checks
  and exercised by frozen E2E fixtures: role-local discovery remains bounded,
  Explorer success is independently scored, and Reviewer execution is limited
  to registered test/static-check ids with unregistered execution rejected.

## 9. Non-Goals

- Do not redesign `AGENTS.md`'s core architecture during this pass.
- Do not start routing real feature work through a Coordinator before the
  exit criteria in §8 are met. `improvement-plan-v2.1.md` Phase 1
  (contract/schema authoring) may proceed in parallel since it doesn't
  touch live routing.
- Do not treat "add a Coordinator" as a fix for the failure patterns in
  §3 — they exist independently of whether a Coordinator is present, and
  will still be there underneath one if left unaddressed.
