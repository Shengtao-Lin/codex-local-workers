# Stability research and bounded implementation plan

Primary assessment, 2026-09-28. Stop at the live v2.1 implementation-entry
gate or 40% weekly usage consumed (60% remaining), whichever is reached first.
A failed candidate ends that batch, not permission to fabricate a release;
further work must address a distinct evidenced cause. No source-repository writes or Git
commits. Existing historical denominators and `role-aligned-v1` stay frozen.

## Current evidence

The stopped `batch-c44bdb1a50af` has five complete cells: Explorer evidence
2/5, Coder 5/5, Reviewer 5/5, independent validation and Primary acceptance
5/5. Its sixth interrupted workspace is not a completed cell. The separate
two-case protocol-recovery repeat passed 2/2; it does not replace that batch.
The remaining observed Explorer failure reports an actual code/test mismatch
as investigation failure. Normal native FINISH_SUCCESS schema leaves file
objects unspecified and does not advertise the citations accepted by runtime;
only its recovery request exposes that structure. Client diagnostics also
previously lost finish_reason on nonempty responses.

## Sources and applicability

These are design comparisons, not evidence that another project's advertised
success rate transfers to our models. Public main-branch sources were inspected
on the date above; links are not immutable version pins. No external code was
installed or executed.

| Project | Inspected source / useful idea | Decision for this kit |
| --- | --- | --- |
| neal | [State machine](https://github.com/navels/neal/blob/main/docs/state-machine.md): validate lifecycle invariants, separate controlled blocked states, bounded same-evidence recovery | Separate investigation completion from the condition of investigated code. Preserve genuine failures; no substring-based auto-success. Existing archive authority remains. |
| neal-swebench | [Harness methodology](https://github.com/navels/neal-swebench): fixed cases, infrastructure attribution, isolated grading and oracle separation | Preserve all attempts and separate diagnostic repeats from candidate denominators. Keep grading serialized on this single local server. Public benchmark remains second-layer work. |
| Aider | [base_coder.py](https://github.com/Aider-AI/aider/blob/main/aider/coders/base_coder.py), [edit formats](https://aider.chat/docs/more/edit-formats.html), [repo map](https://aider.chat/docs/repomap.html): bounded reflections, explicit output-length handling, model-sensitive formats and compact navigation | Add finish-reason/token facts and reject truncated actions. Keep safe exact edits and bounded recovery. A navigation map is not today's blocker; defer it. |
| JcodeAgent | [context.py](https://github.com/ShakenTheCoder/JcodeAgent/blob/main/jcode/context.py): role histories, dependency-relevant context, bounded failure summaries | Existing repair_focus and scoped packets already implement the relevant principle. Do not add another Analyzer or adopt per-file decomposition for atomic multi-file invariants. |
| zm2231/codex-orchestrator | [supervision.py](https://github.com/zm2231/codex-orchestrator/blob/main/src/orchestrator/supervision.py): bounded corrective requests and deliverable checks | Keep verified artifacts, not acknowledgements. Do not import text-pattern acceptance: its review-decision matching is weaker than canonical evidence verification. |
| Untrivial agent-orchestrator | [lifecycle reactions](https://github.com/Untrivial-ai/agent-orchestrator/blob/main/backend/internal/lifecycle/reactions.go), [overview](https://github.com/Untrivial-ai/agent-orchestrator): persisted reaction signatures and session lifecycle | Useful for future persistent Coordinator recovery. Desktop/multi-worker infrastructure is unnecessary for this sequential stability gate. |
| Local-Multi-agent-Orchestrator | [model_client.py](https://github.com/JanithaIllankoon/Local-Multi-agent-Orchestrator/blob/main/src/models/model_client.py): central role-to-client configuration and server readiness | Keep model identities configuration-driven. Do not copy catch-all retries (including deterministic bad requests) or raw reasoning/output telemetry. Existing deadlines allow slow model startup. |

## Implementation units

Feature `role-protocol-convergence-20260928`: feature/integration risk medium.
Primary takes over this bounded diagnosis and protocol edit because the
architecture/failure cause is under investigation; do not ask another model to
decide which acceptance rule to weaken.

1. Unit `explorer-report-contract`, medium, no dependencies; owns
   `investigation-outcome`, `observed-citations`, `bounded-failure`.
   Advertise exact file/citation fields on the normal request; explain that
   discovering a bug can complete investigation. Preserve FINISH_FAILED and all
   actual-read citation checks. Do not reinterpret historical failures.
2. Unit `role-response-diagnostics`, medium, no dependencies; owns
   `no-truncated-action`, `metadata-only-telemetry`. Record provider finish
   reason and numeric token counts, reject length-truncated output before
   action dispatch, without unlimited retries or logging raw source. Apply the
   same boundary to the shared Coder/Reviewer client: code inspection showed
   its previous length check only covered empty responses.
3. Unit `candidate-acceptance`, medium, depends on both; owns
   `frozen-denominator`, `independent-role-results`. Focused deterministic tests,
   existing complete regression suite and Ruff first; two-round targeted
   defect-reporting fixture, then one same-input 11-case/two-round candidate
   with mathematical stop. Independently review actual patches and Explorer
   source claims before any release decision.

Acceptance: target fixture must retain true investigation failure and unread
citation rejection; transport must distinguish length truncation from JSON
syntax errors; full release still requires all §12.8 checks, role compatibility,
unknown-location handoff and Primary integration review. A successful targeted
repeat alone is not release.

## v2.1 gate terminology

Offline Phase 1 implementation is already allowed. The requested **live
implementation-entry gate** means permission to start Phase 2 routing, not
claiming that Coordinator itself has been implemented. It still requires v1.2
exit evidence. Phase 1 persistence/import enforcement and Phase 1.5 approved
Reviewer execution remain separately tracked work. Registered Reviewer test
and static-check execution already exists and was exercised in the earlier
high-risk fixtures; it is not general shell execution or completed Coordinator
routing. No numerical gate is reduced here.

## First diagnostic pilot

`batch-907d3d7cb812`: two reviewer-citation cells, Explorer evidence 1/2,
Coder/Reviewer/independent validation/Primary acceptance 2/2. The new response
metadata shows stop (not length), 283-438 completion tokens on the failed
reports, and roughly 18-20% context utilization. Repeated missing
`citations.claim` caused the failure. The previous one-shot recovery selected
only missing-line/test-list errors. It now covers citation field-shape errors,
explains the exact field, and mechanically rejects non-report actions during
that one attempt. A bad recovery stops immediately rather than returning to
investigation. This is a protocol repair, not a semantic acceptance waiver.
The second report lists relevant source/test facts but omits the requested
input-by-input diagnosis; mechanical success is not complete semantic success.

The separate repaired pilot `batch-271e5f4fdd89` passed 2/2 for Explorer
evidence, Coder, Reviewer, independent pytest/Ruff and Primary actual-diff
review. Its reports still omit some requested per-input reasoning, retained as
incomplete diagnosis rather than claiming comprehensive semantic success.
Before the full candidate, deterministic regressions passed 309 tests and 10
subtests. Runtime and models are frozen during the full candidate.

## Investigation candidate failed; capability boundary changed explicitly

`batch-180cd482857e` completed selection-order with valid Coder/Reviewer and
independent checks, but Explorer incorrectly predicted that the broken
ascending sort preserves the tied-timestamp expected `[b, a]` result. It
actually produces `[a, b]`. This violates the zero-incorrect-claim rule even
though its newest/oldest diagnosis was otherwise useful. Primary recorded the
Coder accept separately. The next mapping-metadata investigation was interrupted
while read-only; no managed writer was active. Its partial snapshot is not a
completed cell. The investigation candidate remains NO-GO.

Historical baseline-output and per-test-function experiments were then checked
in `V1.2-MODEL-CANDIDATES.md`; both had already failed to solve these semantic
errors. They are not repeated.

New opt-in unit `explorer-localization-contract`, feature/unit/integration risk
medium, depends on the response and terminal protocol fixes. Owned contracts:
`read-version-bound-reference`, `no-model-semantic-verdict`,
`role-mode-cache-isolation`, `localization-relevance`. This is a deliberately
smaller capability, inspired by Aider's separation of navigation context from
editing and the existing Reviewer's runtime-materialized source references.
It is not a claim that OSS learned to reason more reliably.

`explorer_mode=locate` asks the model to select at most six read source/test
ranges (80 lines total). Runtime rejects extra semantic-report fields, unseen
lines, changed files, unsafe paths and oversized ranges; it materializes quotes
and hashes itself. Reports say `semantic_verdict=not_evaluated`. Existing
`investigate` stays the default and keeps its original tests and results.
The cache key separates the two modes. Benchmark scoring additionally requires
the selected implementation excerpts to cover every injected mutation and a
real test assertion, using fixture oracles only in the scorer, never in prompts.
Selecting the right filename or imports alone cannot pass.

The three-case diagnostic covers selection-order, multi-file sample-identity
and mapping-message-sequence. Only after this passes should a separately named
localization-only candidate run. Its numerical pipeline thresholds must remain
those of §12.8, but it cannot establish general semantic investigation or
replace that failed baseline. Any narrower v2.1 entry decision must explicitly
restrict supported Explorer work to localization and send semantic investigation
to Primary. No automatic rewrite of wrong model claims is allowed.

### Locator diagnostics and shared search correction

`batch-c2116f3e04ee` passed selection-order and mapping-message-sequence.
sample-identity exposed a deterministic range-validation bug: the old
single-line citation set excluded blank lines, so selecting a displayed range
containing blank lines was rejected. Separate displayed-range tracking now
includes blanks while retaining nonempty-line checks for old citations. Tool
output truncation also stops marking unseen tail lines as displayed, and source
changes invalidate prior ranges. After this correction, the separate
`batch-deca48e104bc` passed sample-identity 2/2 across all roles, independent
tests and Primary actual-diff review. This does not erase the initial failure.

The initial diagnostic Coder failed sample-identity and a focused inherited
rework only corrected fingerprint volatility before repeated no-op replacements
stopped it. Both failures remain in their archives with rework/takeover Primary
decisions. No runtime rule is added to infer model fields from test names.

Unknown-location `handoff-04dffff39d05` correctly blocked Coder after three
empty Explorer searches. Inspection found that ordinary fnmatch did not match
`**/tests/test_selection_order.py` against root-level
`tests/test_selection_order.py`. A shared `matches_repo_glob` now preserves
legacy matches and additionally handles zero-directory globstar matches using
bounded dynamic programming. Explorer LIST/SEARCH/TRACE and Coder/Reviewer
SEARCH use it only after their existing scope/reparse filters. Unit risk is
medium; owned contract `consistent-navigation-without-scope-expansion`.
The unchanged question is retried only after this deterministic fix.

The retry `handoff-fc97fbda3bfb` passed unknown-source localization, current
source-hash verification, Coder validation, automatic Reviewer dispatch and
independent pytest/Ruff. Primary inspected the actual selection-order diff
and recorded acceptance. The failed predecessor remains a failed attempt.

Current three-role compatibility in
`benchmarks/results/role-compat-locate/role-compat-20260928T070615Z.json`
passed 3/3 with no infrastructure failures. Explorer exercised READ_FILE,
literal and regex SEARCH, TRACE and locator FINISH_SUCCESS; Coder exercised
SEARCH, READ_FILE, SAFE_CREATE, SAFE_REPLACE and VALIDATE; Reviewer exercised
SEARCH, READ_FILE, both approved execution actions and REPORT. The full
deterministic suite passed 322 tests and 21 subtests; changed-file Ruff passed.

Frozen localization candidate `batch-dc346d70a425` now runs the same 11 cases
twice with the existing OSS/Qwen/Muse assignments. Its candidate-inputs.json
binds runtime, runner, assessors, configuration and models. This candidate
cannot qualify general semantic investigation and is not pooled with pilots.

### Frozen localization candidate: NO-GO

`batch-dc346d70a425` stopped at a completed-unit boundary with 18/22 planned
cells retained: Explorer 16/18, Coder 17/18, Reviewer 17/17 reached,
independent validation and Primary Coder acceptance 17/18, protocol E2E 16/18,
infrastructure failures 0. Round one passed all 11; round-two sample-identity
failed, making the critical both-rounds requirement unreachable. The in-flight
scorer-unused-binding unit completed before the stop, and remains counted.

Round-two reviewer-citation Explorer repeated the same SEARCH three times
after reading source/test evidence (12.56% reported context utilization), then
stopped as no progress. Its successful Coder/Reviewer result does not erase the
Explorer failure. Sample-identity Explorer first exceeded six references, then
exceeded 80 total quoted lines during its one allowed correction. Coder made
an incomplete fingerprint-only edit, repeatedly supplied multiline text to
SAFE_REPLACE_LINE, then failed an exact SAFE_REPLACE target. All failures and
partial diffs remain archived; Primary recorded rework for the failed unit.

Bounded follow-up unit `edit-format-repair-hint`, medium feature/unit/integration
risk, owns `no-implicit-edit`, `observed-version-bound-target`, and
`unchanged-edit-authority`: after a rejected multiline SAFE_REPLACE_LINE, show
an exact unique already-observed source line and its matching hash as a
SAFE_REPLACE target. Never execute or synthesize the replacement. Stale hashes,
unread lines, unauthorized paths and oversized/ambiguous targets get no hint.
The existing protocol-error budget is unchanged. This follows Aider's useful
principle of making edit format corrections concrete, without adopting fuzzy
editing. Focused regressions passed 171 tests and 9 subtests; Ruff passed.

Locator correction now repeats both count and aggregate-line limits together.
The runner distinguishes mandatory implementation targets from extra context
reads; the model-definition file was previously ambiguously described as a
mandatory implementation citation. All actual mutation targets and test
evidence remain required by the unchanged held-out scorer. These changes
invalidate the old candidate for current-release use; it remains NO-GO.

Separate diagnostic `batch-54ca3f81bb91` passed sample-identity 2/2 across
Explorer/Coder/Reviewer, independent validation and Primary actual-diff review.
The first locator used its single report correction successfully. Neither
Coder run exercised the new multiline-edit hint, so this is not causal proof
of that hint's live benefit; deterministic tests verify its no-write behavior,
exact observed target, stale-hash rejection and explicit subsequent edit.
The complete deterministic suite now passes 324 tests and 21 subtests.

## Budget stop / handoff

Weekly usage reached 40% consumed / 60% remaining (15 percentage points since
the start). No further optimization or live test is authorized in this turn.
Current compatibility repeated 3/3 with zero infra failures in
`benchmarks/results/role-compat-locate/role-compat-20260928T074439Z.json`.

The new frozen candidate is `batch-488faa0f3eee`. At the stop check, 21 cells
had completed with independent Explorer/Coder/Reviewer/protocol success; the
last mapping-message-sequence Reviewer was still running. A STOP_REQUESTED
marker allows that in-flight unit to finish, without starting another unit.
Both sample-identity rounds passed and received Primary acceptance.

Primary rejected round-one mapping-message-sequence despite its passing tests
and Reviewer: Coder inserted a duplicate unconditional raise, leaving the old
raise unreachable. The round-two actual diff has the same defect and must also
receive rework, not automatic acceptance. This is a repeated quality miss by
Reviewer and a concrete regression to retain. Do not erase it with a later
repair or call protocol pass equivalent to Primary acceptance.

The final independent localization assessor and release-evidence closure were
not completed before the budget stop. **No new implementation-entry gate is
declared passed.** General semantic-investigation routing remains NO-GO.
Next authorized continuation: read this batch's final summary, record the last
Primary rework if still missing, run canonical localization verification and
review the explicit capability restriction. Keep all old failed candidates
separate. Do not start another broad baseline before this final audit.

## Continuation closure

The last cell completed, yielding the required two identical 11-case rounds.
Primary recorded the second mapping-message-sequence rework. The independent
`localization_readiness.py` assessor returned GO with 22/22 verified
locations, 21/21 Coder repair-focus units eventually validated, 22/22 Reviewer
and protocol passes, 20/22 Primary accepts, zero infrastructure failures,
and both sample-identity rounds accepted. Current unknown-source handoff
`handoff-72e9ee1beef5` passed Explorer current-hash gating, Coder, Reviewer,
independent pytest/Ruff and Primary actual-diff review. See
`benchmarks/V1.2-LOCALIZATION-CANDIDATE.md` for the scoped decision. This
supersedes the pending status above, not the retained failures. It qualifies
implementing locator-only Phase 2 routing; general semantic investigation and
live Coordinator deployment remain unqualified.
