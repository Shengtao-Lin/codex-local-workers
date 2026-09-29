# Stability v1 E2E results

Date: 2026-09-25

This record covers the frozen local fixtures only. SWE-bench Lite has not been
started because the local repair loop is not yet stable enough to use a public
benchmark as a meaningful second-layer comparison.

## Environment

- LM Studio endpoint: `http://127.0.0.1:12345`
- Explorer context: 32,768
- Coder context: 24,576
- Reviewer context: 24,576
- Frozen sources: `F:/ChatGPT/agent-evaluation-harness` and
  `F:/ChatGPT/agent-runtime-kit` (SHA-256 checked, read-only)

## Five-case unified baseline

Canonical batch: `benchmarks/work/stability-v1/batch-b88d5f26af29`

The final evidence gate was recalculated from the immutable Explorer reports
after accepting a focused test path cited in findings as real test evidence.
This corrects the batch's earlier in-process Explorer count without changing
any worker output.

| Metric | Result |
| --- | ---: |
| Explorer success with real file/line evidence | 4/5 (80%) |
| Coder ready for review | 3/5 (60%) |
| Reviewer valid report, all cases | 3/5 (60%) |
| Reviewer valid report, conditional on Reviewer reached | 3/3 (100%) |
| Qualified end-to-end pass | 3/5 (60%) |
| Infrastructure failures | 0 |
| Failed validations followed immediately by an edit | 0/6 (0%) |
| Citation correction rounds exercised | 0 |

The three qualified passes were `selection-order`, `mapping-metadata`, and
`metadata-limit`. `internal-trace` and `sample-identity` both exposed the same
important Coder weakness: a correct runtime diagnosis was issued, but the next
action was not an edit. The former made an incorrect boolean rewrite; the
latter introduced an undefined `VOLATILE_CONTENT_FIELDS` name. Both exhausted
their bounded repair cycles. `sample-identity` also failed the independent
Explorer evidence gate because its report omitted line citations; later Coder
work does not erase that Explorer failure.

## Reviewer citation fixture

The sixth fixture, `reviewer-citation`, routes an isolated real-code repair
through a high-risk review so `contract_review` must contain a source-backed
entry for `behavior-1`.

- First complete run after fixing the test environment:
  `benchmarks/work/stability-v1/batch-983b2eeb9954`
  - Explorer and Coder passed.
  - Reviewer returned an empty assistant message during a tiny structured-output
    probe and was correctly classified as an infrastructure failure.
  - Estimated Reviewer context utilization was 2.25%, so context pressure was
    not causal.
- Targeted runtime fix: an empty or malformed structured-output probe now
  verifies the plain-JSON fallback before failing the review.
- Passing rerun: `benchmarks/work/stability-v1/batch-bfe0246181b1`
  - Explorer, Coder, Reviewer, focused pytest, Ruff format, and Ruff lint passed.
  - Reviewer cited `src/agent_runtime/models.py:19` with the exact source quote
    `MAX_METADATA_BYTES = 16_384` for `behavior-1`.
  - Citation convergence was achieved in zero citation-fix rounds. One unrelated
    malformed-action protocol error was corrected before the valid report.
  - Maximum reported context utilization (input plus reserved output) was
    17.12% Explorer, 40.92% Coder, and 54.52% Reviewer.

The runner now records `citation_required`, `citation_converged`,
`citation_fix_rounds`, and `citation_converged_after_fix` separately. A future
sample that initially submits a wrong quote will therefore measure the actual
repair path rather than conflating it with a first-valid citation.

## Context-length finding

No observed quality failure was near a configured context limit. In the unified
baseline, maximum reported utilization including reserved output was 17.24%
for Explorer, 39.87% for Coder, and 54.91% for Reviewer. The two Coder failures
were therefore diagnosis-to-edit/semantic recovery failures, not context-window
exhaustion. The Reviewer empty response also occurred on a very small probe.

## Phase 0 decision

**NO-GO for moving on to the public benchmark layer.** The baseline convergence
number is now recorded, Reviewer can produce a source-valid high-risk contract
review, and the observed structured-probe failure is handled and classified.
However, `repair_focus -> immediate edit` remains 0/6 in the unified batch, so
the primary stability exit criterion has not materially improved.

Next work should stay within v1: make the repair instruction/action boundary
more directive for the two frozen failing archetypes, rerun those cases for
several rounds, and preserve Explorer, Coder, Reviewer, E2E, citation, context,
and infrastructure metrics independently.

## Phase 0 repair-gate and Coder comparison follow-up

The three-role capability matrix now belongs to the current v1 stability plan:

```text
Explorer: READ + SEARCH + TRACE
Coder:    READ + SEARCH + SAFE_EDIT + VALIDATE
Reviewer: READ + SEARCH + APPROVED_EXECUTION + REPORT
```

Coder repair focus now distinguishes protected-test assertion locations from
authorized source candidates, supplies post-edit or observed hashes, rejects
READ/SEARCH/VALIDATE when a concrete `SAFE_REPLACE` is required, and rejects
no-op replacements whose find/replace text is identical. The runner records
`repair_gate_rejections` separately from successful edit conversion.

Evidence from the same 24,576-token Coder context:

- Original `qwen3-coder-30b-a3b-instruct-i1`, batch
  `batch-bf217574f1fe`: both `internal-trace` and `sample-identity` failed.
  The gate prevented unnecessary exploration, but the model still did not
  reliably convert repair focus into a correct edit.
- Alternate `qwen/qwen3-coder-30b`, batch `batch-09cc98a27697`:
  `internal-trace` passed Explorer, Coder, Reviewer, independent tests, and
  Ruff on the first implementation, with no repair round.
- Alternate `qwen/qwen3-coder-30b`, batch `batch-0cf8423b24fa`:
  `sample-identity` still failed. Explorer evidence passed, but after an
  initial validation the Coder attempted four READ/SEARCH actions instead of
  the required edit; all four were deterministically rejected. Maximum
  reported Coder context utilization was 44.71%, so context pressure was not
  causal.

This isolates two factors: the alternate Coder materially improves the simple
semantic repair, while the multi-file repair transition remains unstable even
with the stronger model and deterministic gate. The next experiment should use
a structured multi-file repair choice (candidate path + failing contract branch
+ required edit action) and compare repeated rounds; adding more generic prompt
text is not justified by the evidence.

## Capability implementation follow-up

The v1 runtime now implements the capability matrix directly:

- Explorer has bounded Python `TRACE` for definitions and one-hop
  callers/callees, with real path/line/quote evidence. A requested test-evidence
  investigation cannot finish successfully while omitting an observed test
  path from `relevant_tests`.
- Coder receives compact authoritative repair context with candidate source
  excerpts and hashes. In `batch-1ecce86eda6a`, `sample-identity` improved
  from zero immediate edits to 1/1 after repair focus, although the later
  multi-file replacement still missed its target.
- Reviewer can execute only catalogued focused tests and configured static
  checks through `RUN_APPROVED_TEST` and `RUN_APPROVED_STATIC_CHECK`; commands
  are fixed by trusted runtime data and run with `shell=False`.

Reviewer live evidence:

- `batch-fe161ca2b05c`: Coder and Reviewer passed the high-risk citation case;
  Reviewer re-executed the approved checks and converged without citation-fix
  rounds. Explorer returned success but omitted the test path, so the runner
  correctly kept E2E at fail.
- `batch-98effd5c8ac7` and `batch-028efb20ff7c`: Explorer evidence and Coder
  passed, but Muse failed its first substantive request with LM Studio
  `peg-native` format errors. The client now records the bounded HTTP response
  body, proving this was not context pressure (about 44% estimated utilization).
  Structured, plain-JSON, and deterministic plain-JSON requests all reproduced
  the engine error, so unbounded retry is not justified.
- `batch-1ef992f1c642` and `batch-7f54a11936fd`: routing Reviewer to
  `qwen/qwen3-coder-30b` avoided the infrastructure error and correctly ran
  focused pytest plus both Ruff checks, but it repeatedly reread source instead
  of submitting the final report after context compaction. Bounded evidence
  replay is now present, but this model still ignored the required REPORT
  transition.

Current conclusion remains **NO-GO** for the public benchmark layer. Explorer
and Coder passed the latest high-risk runs independently, and Reviewer approved
execution works, but Reviewer model/protocol stability is not yet repeatable
enough for a reliable E2E baseline. The next v1 change should make
`approved execution complete -> REPORT` a deterministic action gate, analogous
to Coder's repair gate, rather than adding retries or increasing context.

## Three-blocker optimization

The next targeted iteration implemented three bounded changes:

1. A `pass_to_primary` report that is otherwise valid but waiting only for
   approved executions is retained. After the final registered test/check
   passes, the runtime revalidates and finalizes that exact report
   deterministically; the model no longer needs to reconstruct it after context
   trimming.
2. Muse protocol handling is bounded: structured output, plain JSON, and one
   deterministic plain-JSON attempt are tried. If all fail with the exact
   LM Studio `peg-native` format error, Reviewer routes once to configured
   `qwen/qwen3-coder-30b`. Other transport or HTTP failures still fail closed.
3. Coder replacement recovery now uses an unescaped literal SEARCH anchor,
   carries required behavior and persistent no-op warnings into compact repair
   context, and keeps unchanged writable files ahead of already-edited files
   after a multi-file validation failure.

Live evidence:

- `batch-315330858892` passed Explorer, Coder, Reviewer, approved execution,
  high-risk citation, independent pytest, Ruff, and overall E2E. It recorded
  100% for all three role success measures and zero infrastructure failures.
- `sample-identity` improved from repeated no-op edits to a real immediate
  edit. In `batch-c74dfa97c8a8`, `repair_focus -> immediate edit` was 1/1
  with only one gate rejection. The case still failed after three matching
  validations, so the multi-file semantic repair is improved but not yet
  stable enough to count as passed.

## Validation

- Focused post-change suites: Worker 70, Explorer 23, Reviewer 31 passed.
- Fresh full suite: 155 passed, plus 4 passing subtests.
- Ruff format check: passed for `.local-agents` and the stability runner.
- Ruff lint: passed for `.local-agents` and the stability runner.
- `git diff --check`: passed (line-ending warnings only).

## v1.2 preparation and first convergence runs

New stability results now carry `plan_version: v1.2`; existing v1.1 batches
remain unchanged historical evidence.

The first v1.2 Coder slice adds:

- validation failure deltas: resolved, remaining, and new test ids;
- failed-test-symbol matching against packet edit-target anchors;
- exact `required_path` enforcement when one target is identified;
- repair excerpts narrowed to the target anchor instead of the preceding
  function;
- one-shot supervision that permits one genuinely new relevant READ/SEARCH,
  emits one nudge for a no-evidence action, and stops repeated no-progress;
- runtime-grounded undefined-symbol locations and bounded failing-test snippets
  in the compact repair context.

Observed progression for `sample-identity`:

- `batch-7fbe80bb7082`: exposed that the wide repair excerpt caused an edit to
  the adjacent `make_sample_id` function.
- `batch-0756886817de`: two of three tests passed; only preservation of
  `source_metadata` remained.
- `batch-9fc91318dc68`: the remaining repair was routed to `dedup.py`, then
  exposed a concrete undefined-symbol repair.
- `batch-c67e78bd880c`: three repair focuses selected exact paths and two
  failed-validation transitions immediately produced edits; two of three tests
  passed before the two-repair budget ended.
- `batch-3317648d2d29`: a fixture-specific third repair did not close the
  final semantic boundary. Increasing repair count alone is therefore not the
  fix; the micro packet must state the negative invariant that row identity is
  excluded while `source_metadata` remains scoring input.

Regression control: `reviewer-citation` passed end to end under v1.2 in
`batch-f352d9bddf36`, including Explorer evidence, Coder, Reviewer approved
execution, citation, independent pytest, Ruff, and zero infrastructure
failures.

Current v1.2 status remains **NO-GO** for the broader baseline. The next narrow
step is contract-aware repair guidance for negative/preservation invariants,
not more turns or a larger context window.

## v1.2 semantic-invariant follow-up

The runtime now records passing JUnit test ids alongside failures and carries
test-name-derived preservation/ignore invariants into compact repair context.
Coder is also instructed to establish a focused-test baseline before its first
source edit so already-passing boundary behavior is visible before mutation.

Live sample-identity evidence:

- batch-009a9e77c5ac showed that failure-only invariants were insufficient:
  Coder excluded source_metadata while attempting to ignore row identity.
- batch-2d61bcc7584f preserved the content-fingerprint boundary but introduced
  a local import after first use in dedup.py; context utilization remained
  below 45%, so context length was not the limiting factor.
- batch-5c3c29e789fe and batch-addb78939a00 confirmed that a pre-edit
  baseline works, but the model repeatedly reread the exact supplied repair
  region instead of editing. A second supervision nudge was tested and removed
  because it did not improve conversion.
- The frozen fixture contract was corrected to state both sides explicitly:
  ignore only sample_id, while preserving source_metadata as scoring input.
- batch-9358a873b772 then produced a repair-focus edit, but Coder introduced
  local-name shadowing of canonical_json and later omitted the required
  contract-check id. Explorer evidence passed; Coder and E2E did not.

Status remains **NO-GO**. The next targeted runtime work should classify
newly introduced local-name shadowing/UnboundLocalError and retain a valid
contract-check template across repair validations. More repair turns or a
larger context window are not supported by the evidence.

## v1.2 repair-state follow-up

Two additional deterministic runtime defects were corrected:

- UnboundLocalError caused by a new local assignment/import shadowing an
  earlier read now produces an exact same-path SAFE_REPLACE repair focus.
- Once a VALIDATE contract check is accepted, later repair validations inherit
  its required behavior ids. Ordering and observable confirmations are not
  synthesized.
- The configured repair-turn reserve now activates after a successful repair
  edit when fewer than the configured reserve turns remain.
- NameError and UnboundLocalError compact repair packets now consistently carry
  candidate_edit_paths plus expected_sha256_by_path.

Live evidence:

- batch-ddcbc5d68ee7 confirmed contract-check inheritance but exposed that the
  configured repair reserve was not activated after a late repair edit.
- batch-c61b8b8b9d96 confirmed UnboundLocalError classification and exact-path
  routing, but compact repair metadata lacked candidate paths.
- batch-5af05126ce74 exercised 34 Coder requests after the reserve and compact
  packet fixes. The name-shadowing blocker was cleared, but the final
  implementation still failed both score-reuse semantic assertions and stopped
  under bounded repair supervision. Explorer evidence remained valid and
  context utilization stayed below 47%.

The remaining sample-identity blocker is now semantic implementation quality:
the Coder must exclude sample_id while preserving source_metadata, scorer
identity/contract, effective configuration, deterministic mapping order, and
the sha256: return shape together. More protocol retries are not justified by
the current evidence.

## v1.2 explicit-contract and validated-terminal follow-up

The sample-identity fixture now emits four separately owned behavior contracts,
three observable acceptance scenarios, and narrow implementation guidance. The
contract explicitly preserves the original payload components and return shape
instead of asking Coder to infer them only from protected tests.

The runtime also normalizes an exact SAFE_REPLACE no-op to ready_for_review only
when the current edit revision already passed focused tests and every configured
check and validation inputs remain unchanged. Unvalidated no-ops and no-ops
after a later edit still fail closed.

Reviewer now discards optional contract_review entries for small/medium
pass_to_primary reports when no high-risk or focused-rework obligation requires
them. Required contract evidence remains strict.

Live evidence:

- batch-d4d2ee28d39c reached a fully passing Coder implementation, but two
  post-validation no-op replacements exhausted the protocol budget.
- batch-7b00fce90fed reached ready_for_review after validated no-op
  normalization. Explorer and Coder passed; independent pytest and both Ruff
  checks passed. The initial Reviewer failed because it supplied malformed
  optional medium-risk contract_review entries.
- A read-only Reviewer replay of that exact canonical Coder archive passed as
  diagnostic-optional-contract-review, verifying all four contract ids and both
  configured checks with no findings.
- batch-e6e21282fa6f again produced code that passed independent pytest, format,
  and lint, but Coder attempted a post-validation SAFE_REPLACE whose target was
  absent. It remained failed because target-miss intent cannot safely be
  normalized as an exact no-op.

The pipeline is materially closer but is not yet repeatable end to end. The
remaining Coder issue is a terminal-state transition after successful
validation. A future gate may reject further mutation attempts and request
FINISH_SUCCESS, but it must not silently accept a failed non-no-op edit.

## v1.2 validated-terminal gate

The runtime now treats a successful, current validation as a terminal state.
Any later action other than `FINISH_SUCCESS` is rejected before dispatch. The
first such action receives a one-shot nudge; a second action is mechanically
finalized as `ready_for_review`. If any validation input changes, the gate is
invalidated and normal validation requirements apply again.

Regression evidence:

- Worker runtime focused suite: 81 passed.
- batch-f158ef4a7e95 ran the frozen `sample-identity` fixture through Explorer,
  Coder, Reviewer, and independent acceptance checks.
- Explorer supplied valid source evidence; Coder reached `ready_for_review`;
  Reviewer returned `pass_to_primary`; independent pytest (3 tests), Ruff
  format, and Ruff lint passed.
- The live run entered the terminal gate once, rejected one post-validation
  action before execution, issued one nudge, and then received a compliant
  `FINISH_SUCCESS`. Runtime auto-finalization was not needed.
- Maximum reported context utilization was 15.07% for Explorer, 45.63% for
  Coder, and 56.60% for Reviewer, so this passing run was not context-bound.

This establishes one qualified end-to-end pass for the retained compat
fixture. It does not yet establish the multi-round baseline required for GO.

## v1.2 request preflight and infrastructure classification

Coder and Reviewer now share a send-time request preflight; Explorer applies
the same policy in its independent LM Studio client. Each request records total
bytes, estimated input tokens, configured context, output reserve, safety
margin, and the three largest logical prompt sections. Requests that cannot fit
are rejected locally as `input_too_large` before any HTTP call. HTTP 4xx/5xx
responses retain a bounded provider body and are reported as `infra_failure`
without incrementing protocol-error counters.

Verification evidence:

- Full local-agent suite: 172 passed plus 4 subtests; Ruff and diff checks pass.
- Unit tests prove oversized Coder/Reviewer and Explorer requests never call
  `urlopen`, and prove HTTP 400/500 status/body classification.
- Runtime tests prove both Coder and Explorer preserve the structured
  `infra_failure` and leave protocol-error counts unchanged.
- batch-ddfc13347f2b exercised the new preflight against the live shared LM
  Studio service. No request was rejected and no infrastructure failure
  occurred. Explorer succeeded; Coder reached 45.63% maximum reported context
  utilization, then failed one of three semantic assertions and later missed a
  SAFE_REPLACE target. This is worker-quality variance, not an infra failure.

Section 12.3 is mechanically covered. The live run is intentionally retained
as evidence that infrastructure classification does not hide semantic failure.

## v1.2 model-by-role compatibility qualification

`benchmarks/role_compat.py` now runs the disposable three-role smoke, extracts
actual actions from canonical Explorer, Coder, and Reviewer archives, and
stores timestamped results plus a local `latest.json`. Core task completion and
full protocol-action coverage are separate: uncovered actions produce
`incomplete`, never an inferred pass. Existing immutable smoke evidence can be
re-evaluated without another model call.

First stored qualification (`role-compat-20260926T024824Z.json`):

- all three roles passed the core live fixture on the shared LM Studio service;
- Explorer observed SEARCH, READ_FILE, and FINISH_SUCCESS; TRACE remains
  unexercised;
- Coder observed READ_FILE, SAFE_REPLACE, VALIDATE, and FINISH_SUCCESS; SEARCH
  and SAFE_CREATE remain unexercised;
- Reviewer observed READ_FILE and REPORT; SEARCH and both approved-execution
  actions remain unexercised;
- result: 0 complete passes, 3 incomplete, 0 core failures.

Section 12.4 is now measurable and persisted, but it is not yet satisfied as a
full compatibility pass. These explicit gaps define the next frozen fixtures
for section 12.5.

## v1.2 frozen capability matrix

`benchmarks/capability-matrix-v1.2.json` now freezes all three current-role
boundaries and maps every allowed/prohibited cell to executable evidence.
Coverage includes bounded reads, literal/regex search, Explorer TRACE, Coder
SAFE_CREATE/SAFE_REPLACE/VALIDATE, Reviewer registered test/static execution,
REPORT, scope escape rejection, control-file protection, and action-schema
exclusion of mutation, shell, Git, and delegation where prohibited.

Verification evidence:

- matrix referential-integrity meta-test resolves every cited class and method;
- full local-agent suite: 178 passed plus 4 subtests;
- scoped Ruff and `git diff --check` pass.

Section 12.5 is mechanically satisfied for runtime enforcement. Live model
qualification remains honestly incomplete for the action gaps listed above;
the frozen runtime fixture is not used to inflate those model results.

## v1.2 targeted live compatibility follow-up

The disposable compatibility fixture was expanded without adding a Reviewer
`VALIDATE` action. Reviewer validation remains canonical evidence inspection
plus registered `RUN_APPROVED_TEST` / `RUN_APPROVED_STATIC_CHECK` actions.

Observed results:

- Coder completed the expanded fixture and produced a full live compatibility
  pass with READ_FILE, SEARCH, SAFE_CREATE, SAFE_REPLACE, VALIDATE, and
  FINISH_SUCCESS all present in its canonical action archive. Five independent
  tests passed.
- The first combined Explorer prompt executed SEARCH and TRACE but stopped on
  duplicate/no-progress supervision. Splitting it into a separate focused
  investigation succeeded with READ_FILE, SEARCH, TRACE, and FINISH_SUCCESS.
- The Explorer model nevertheless ignored the explicit regex-mode request and
  issued literal searches. `REGEX_SEARCH` is therefore tracked as its own
  compatibility item rather than being hidden by generic SEARCH success.
- Reviewer qualification ended in an LM Studio transport timeout before the
  approved-execution sequence. The result is classified as
  `model_request_timeout` / `infra_failure`, not a Reviewer capability failure.

Current live status: Coder pass; Explorer incomplete on regex-mode compliance;
Reviewer pending a clean approved-execution run after infrastructure timeout.

## v1.2 fixed-model compatibility follow-up (2026-09-26)

The active models remain OSS20B / Qwen Coder / Muse at 32768 / 24576 / 24576
context. The configured Reviewer fallback to Qwen was removed, so a Muse
compatibility result cannot silently come from another model. The Reviewer
SEARCH gate now counts only completed searches and gives a hint derived from a
real changed file. Explorer qualification requires a regex SEARCH and a TRACE
with actual file/line evidence before success. Its core question now states
that finding a code defect is a successful investigation.

Observed independent snapshots:

- `role-compat-20260926T041452Z.json`: Explorer pass; Coder failed two semantic
  error-path tests, so Reviewer was correctly not dispatched.
- `role-compat-20260926T041849Z.json`: Coder pass and five independent tests
  passed; Explorer core investigation ended with `FINISH_FAILED` despite
  correctly finding the gap; Muse Reviewer received an HTTP 400 `peg-native`
  error after automatic dispatch.
- `role-compat-20260926T042621Z.json`: Explorer and Coder both passed every
  required action; Coder's five tests passed. The automatic Muse Reviewer
  dispatch and one fresh-id retry both returned the same HTTP 400. The retry
  rechecked the frozen handoff and halved the output cap from 4096 to 2048.
- Isolated Reviewer replays against successful Coder archives passed at 4096
  and 2048 output tokens, with READ_FILE, SEARCH, approved pytest, both Ruff
  checks, and `pass_to_primary`. A 512-token diagnostic returned an empty
  assistant message. Starting directly in plain JSON at 2048 passed once and
  failed with the same `peg-native` HTTP 400 on the next identical frozen
  snapshot. These successes demonstrate capability, not a stable pass rate;
  structured-output probing alone does not explain the server error.

`role_compat.py` now scores only successfully executed actions, treats a failed
VALIDATE as exercised without calling the Coder core successful, marks an
unreached Reviewer as `not_run`, and retains each Reviewer infrastructure
attempt separately. The full local-agent suite passed: 185 tests plus 4
subtests; scoped Ruff and `git diff --check` passed.

Status: **NO-GO for the 10–15 unit v1.2 baseline.** Muse's repeated server-side
format rejection remains an infrastructure blocker even at low context
utilization. Automatic Reviewer dispatch works after `ready_for_review`, but
cannot convert a rejected model request into a valid review. The next
investigation must isolate LM Studio's Muse request-format behavior or obtain
a stable same-model response before collecting convergence numbers. Do not
count these trials as a usable E2E baseline.

## v1.2 Muse Reviewer transport diagnosis (2026-09-26)

The fixed roles remain OSS20B / Qwen Coder / Muse at 32768 / 24576 / 24576.
The Reviewer system prompt was shortened while retaining independent diff and
validation review, bounded reads/searches, approved execution, and grounded
REPORT requirements. The archived compatibility run
`role-compat-20260926T045537Z.json` passed all three roles after reevaluation
of a finalized deferred REPORT. A second fresh run
`role-compat-20260926T045927Z.json` failed Reviewer protocol convergence; its
exact Coder archive later passed a focused Reviewer replay after SEARCH repair
feedback was made concrete. A third fresh run
`role-compat-20260926T050546Z.json` passed all three roles. This establishes
capability but not repeatable Reviewer success.

The six-case frozen E2E calibration started in
`batch-653c10e6872f`. Its first case, `selection-order`, provided valid
Explorer file/line evidence. Coder reached `ready_for_review`, repaired after
`repair_focus`, and passed independent pytest (2 tests), Ruff format, and Ruff
check. Automatic Muse Reviewer exhausted four protocol errors (non-JSON,
empty SEARCH, malformed JSON, invalid REPORT decision), so the case was not an
E2E pass. The batch was interrupted before scoring further cases; it is not a
baseline denominator. A replay of the same validated Coder archive with
concrete SEARCH and decision-value feedback failed on the first model turn
with LM Studio HTTP 400 `peg-native`, including structured, plain JSON, and
unstructured fallback requests. Reported request context utilization was
about 25%, far below the configured 24576-token limit.

Frozen transport probes on that same Reviewer input isolated the failure:

- `reviewer-transport-20260926T051619Z-1b853c.json`: minimal structured
  requests returned 3/3; full compact-system structured requests returned 1/3.
- `reviewer-transport-20260926T051746Z-a64fd5.json`: explicitly forbidding
  native tool-recipient markup did not fix it (structured 1/3; plain 0/3).
- `reviewer-transport-20260926T051851Z-7b392d.json`: lower sampling
  temperature did not fix it (0.1: 1/3; 0.0: 0/3).

The LM Studio server log for the failed replay showed
`common_chat_peg_parse: unparsed peg-native output: to=READ_FILE ...`, followed
by task cancellation and `Channel Error`. This is direct evidence that Muse
sometimes emits native tool-recipient syntax that this LM Studio backend
rejects even though the application requests JSON actions. The local runtime
classifies the resulting HTTP 400 as `infra_failure`; it does not falsely
count it as a Coder or Reviewer quality failure.

Status: **NO-GO for the 10–15 unit v1.2 baseline and live v2.1 routing with
the current Muse/LM Studio transport.** The 12.3 classification gate works,
and all three roles have stored compatibility evidence, but Reviewer 12.4
repeatability and 12.6 baseline remain unsatisfied. Keep Muse selected; do not
silently substitute Qwen. Resume the measured baseline only after the same
fixed Muse Reviewer request is reliably handled by the local serving stack or
an explicitly qualified transport path.

## Reviewer candidate qualification on fixed archives (2026-09-26)

The active OSS Explorer, IQ4_XS Qwen Coder, and Muse Reviewer configuration was
not changed. All four user-proposed Reviewer ids were present in LM Studio.
`qwen/qwen3-coder-30b` is the separate Q4_K_M model, not the active Coder id.
The diagnostic Reviewer requests used the same frozen archives and a controlled
24576-token context budget. The transport probe used three identical full
first-turn requests per candidate; all four returned parseable JSON actions
3/3. That is only a startup transport result, not a completed review.

| Reviewer candidate | Ordinary `selection-order` full review | High-risk `reviewer-citation` full review | Hidden long-input defect challenge |
| --- | --- | --- | --- |
| `qwen/qwen3-coder-30b` Q4_K_M | 3/3 valid pass, 0 protocol errors; approved pytest and Ruff executed | 2/2 valid pass, 0 protocol errors; per-obligation source citation and approved checks | 0/3: repeated-read stop, including after bounded changed-source/test evidence replay and at temperature 0.1 |
| `openai/gpt-oss-20b` | 1/1 valid pass, 3 protocol errors | 0/2: protocol budget exhausted | 1/1 scored `rework` with the exact early-return source line; an earlier report also found it but was mis-scored by a stale hard-coded line check |
| `zai-org/glm-4.7-flash` | 1/1 valid pass, 3 protocol errors | 0/1: protocol budget exhausted | 0/1: empty assistant message (infrastructure) |
| `google/gemma-4-26b-a4b` | 0/2 at standard short startup probe; 1/1 full pass with that probe bypassed for diagnosis | 0/2 protocol budget exhausted with diagnostic probe bypass | Not qualified |

The high-risk archive's original ephemeral uv interpreter had expired. For
candidate replays only, the trusted current interpreter was substituted in
memory for registered approved checks; the archived packet, source, tests,
validation evidence, and on-disk config were not edited. The Gemma probe
bypass is explicitly diagnostic and did not change the production Reviewer
gate. The hidden-bug challenge was updated to copy the current multi-file
smoke fixture and score the injected defect's actual line; a regression test
guards that scorer.

Candidate result archives are under `benchmarks/results/reviewer-transport/`
and `benchmarks/results/reviewer-candidates/`; each complete review also has a
unique `.agent/tasks/.../reviews/candidate-*/` archive in its frozen workspace.
The Q4 Qwen high-risk handoff contains actual source-line citation and passed
approved checks. GPT-OSS's scored challenge report contains a concrete
`src/slug.py` early-return finding, not merely an escalation.

Decision: **no automatic Muse replacement yet.** Q4 Qwen is the strongest
protocol/convergence candidate, but its repeated-read loop on a real defect
would give an unacceptable false-negative outcome. GPT-OSS has promising
defect detection but fails the high-risk citation path. A future Reviewer
qualification must pass both green high-risk reviews and a hidden-defect
challenge repeatedly before the 10–15 unit stability baseline can be counted.

## Newly downloaded models: role trials (2026-09-26)

The LM Studio model inventory confirmed `prism-ml/bonsai-27b` (Q1_0) and
`mistralai/devstral-small-2-2512` (Q4_K_M). These were candidate trials, not
changes to the active OSS Explorer / IQ4_XS Qwen Coder / Muse Reviewer config.

For Explorer, `explorer_candidate_eval.py` copied the same three frozen cases
from the two read-only source repositories into separate per-model workspaces.
Each candidate used a 32768-token context and had to make a real model request;
cache hits were excluded. An initial shared-workspace trial is **invalid for
comparison** because Bonsai reused OSS's Explorer cache. The corrected two-round
A/B is `candidate-20260926T062355Z-5bd11e.json`:

| Explorer | Mechanical success with observed file/line evidence | Semantically sound after source/test review | Failure signature |
| --- | --- | --- | --- |
| OSS20B | 4/6 | 2/6 | Two no-new-evidence loops |
| Bonsai-27B | 4/6 | 2/6 | Two empty `finish_reason=length` responses after repair |

The two mechanically successful `sample-identity` reports per model are
**semantic false positives**. Both models say the current implementation
ignores `sample_id`, apparently treating the test expectation as proven behavior.
The frozen `CanonicalSample` contains `sample_id`, while both
`content_fingerprint` and `score_reuse_key` hash `sample.model_dump(mode="json")`
without excluding it. Thus the cited lines exist, but the claimed behavior is
false. The two models did locate the relevant `selection-order` and
`internal-trace` branches in their other successful runs, although some cited
line numbers were off by one. The measured maximum reported context utilization
was below 18%, so these failures do not demonstrate context exhaustion.
The corrected harness calls this a *mechanical* result and explicitly requires
semantic review; it must not be presented as a qualified Explorer success rate.
A separate isolated Bonsai `selection-order` success is stored in
`candidate-20260926T062238Z-0aa204.json`, but is not added to the paired
denominator.

Devstral Reviewer produced 2/3 valid first-turn JSON actions on the fixed
transport probe (`reviewer-transport-20260926T061808Z-bdfa1f.json`); the other
response was empty. On the ordinary `selection-order` archive it completed 2/2
reviews with zero protocol errors. On the high-risk `reviewer-citation` archive,
one review returned `rework` with three protocol errors and identified a real
test gap: a supposed exact 16384-byte boundary test uses a 16384-character
string whose JSON encoding is larger. The second high-risk review exhausted
the protocol-error budget. On the live hidden long-input defect challenge it
returned `pass_to_primary` with no findings, a false negative. Candidate
archives are `candidate-20260926T061846Z-039b8f.json` and
`candidate-20260926T062012Z-83ede4.json`; the challenge has a separate
disposable temp workspace. Candidate high-risk checks used the current trusted
Python interpreter only because the archived ephemeral interpreter had expired.

Conclusion: neither new model is a stable drop-in replacement. Bonsai did not
beat OSS on the paired Explorer cases and is slower here. Devstral can review
ordinary changes and raised one useful test gap, but its transport and
hidden-defect detection are not repeatable enough to replace Muse. Keep the
active model mapping unchanged, and do not count the 10–15 unit v1.2 baseline
until the Reviewer gate has a candidate that repeatedly handles high-risk
citations **and** catches the hidden-defect challenge. The Explorer semantic
false-positive pattern also needs a targeted guard before treating file/line
citations alone as success.

## v1.2 transport and baseline-readiness follow-up (2026-09-26)

The preceding NO-GO conclusions describe the older role transport and model
configuration. The active configuration is now OSS20B Explorer (32,768),
Q4_K_M `qwen/qwen3-coder-30b` Coder (24,576), and Muse Reviewer (24,576),
all on the same LM Studio server. The Q4 Coder passed two fresh multi-file
`sample-identity` snapshots with protected pytest and Ruff; later fresh trials
showed a partial first pass, and one inherited narrow packet finished the
second file with 3/3 tests, Ruff, and automatic Muse review. This is evidence
of rework convergence, **not** a claim of 100% first-pass Coder reliability.

Muse now receives the five allowlisted Reviewer actions as native OpenAI
function tools. The runtime still validates each action and scope. On a frozen
`internal-trace` archive that previously produced two LM Studio `peg-native`
400s, native mode returned 3/3 valid `pass_to_primary` reviews with no infra
failure or protocol error. It caught the hidden long-input early-return defect
in 2/2 native challenge runs (`rework`, source line 5), and passed 2/2 frozen
high-risk green reviews with source references and approved pytest/Ruff
execution (`candidate-20260926T082019Z-d56997.json`). This qualifies Muse for
the measured baseline, not for automatic Primary acceptance.

Explorer's frozen citation gate now checks the complete archived report,
requires actual file/line evidence for each scoped path, and offers a bounded
line-number hint from already read files after a missing citation. A two-round
OSS replay across `selection-order`, `internal-trace`, and `sample-identity`
was 5/6 mechanical successes with no cache hits
(`candidate-20260926T083328Z-a9f7d0.json`). The one failed
`sample-identity` run exhausted its no-new-evidence budget; the successful
`sample-identity` report was separately checked against the source behavior.
Mechanical citation success is still not a semantic guarantee.

The latest three-case calibration, before that citation hint, was Explorer
1/3, Coder 2/3 first pass, Reviewer 2/2 when dispatched, E2E 1/3, and zero
infra failures (`batch-440b1ad5fede/summary.json`). It remains a calibration,
not a v1.2 baseline. Its partial `sample-identity` Coder snapshot subsequently
passed after inherited rework and automatic review. Maximum reported context
utilization in that calibration was about 32% Explorer and 46% Coder on the
failed case, so context exhaustion was not the observed cause.

A live role-compat run first passed Coder and Muse Reviewer but hit one
Explorer `peg-native` HTTP 400 after completing regex SEARCH, READ, and TRACE
(`role-compat-20260926T084449Z.json`). Explorer now retries only that exact
server-format rejection once with required tool choice and a smaller output
cap; unrelated HTTP 400s still fail closed. The subsequent complete live
result is `role-compat-20260926T084919Z.json`: **3/3 role passes**, every
required action observed, zero infra failures, five independent focused tests
passed in the disposable smoke, and automatic Muse Reviewer dispatch succeeded.
The full local-agent and benchmark test suite passed 218 tests plus four
subtests; Ruff check and format passed on touched Python files.

Decision: **ready to start, but not yet pass, the v1.2 10–15-unit baseline**.
Keep the frozen fixtures, independent Explorer denominator, immutable `.agent`
archives, first-pass versus rework counts, Reviewer defect-detection checks,
context utilization, and infra failures separate. Do not promote candidate
trials or this small calibration into the baseline, and do not start the
public benchmark layer until the measured v1.2 exit criteria are evaluated.

The first formal two-round, 12-unit v1.2 run is now recorded separately in
`V1.2-UNIT-BASELINE.md`. Its E2E result is 5/12 with no infrastructure
failures, so the current v1.2 exit decision is NO-GO. The readiness decision
above meant ready to *measure*, not ready for v2.1 Coordinator routing.
