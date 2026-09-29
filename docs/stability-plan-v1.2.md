# stability-plan-v1.2.md

## 0. Status

This supersedes `stability-plan-v1.1.md` for all new stability runs.

Runs already completed under v1.1 remain valid historical evidence and must retain their original plan/version attribution.

v1.2 keeps the same objective and the same current-v1 architecture:

```text
Primary
→ optional Explorer
→ bounded Coder
→ deterministic gates
→ Local Reviewer
→ risk-routed Primary review
```

This revision does **not** introduce live Coordinator routing.

It adds targeted convergence and protocol fixes based on recent Coder and Reviewer failures, the existing v2.1 direction toward deterministic guardrails, and external orchestration patterns that separate planning, scoped execution, repair, review, and evidence handling.

`improvement-plan-v2.1.md` Phase 1 may continue in parallel because schema/contract authoring does not change current live routing.

Phase 2 remains gated on this plan's exit criteria.

## 1. Objective

Stabilize the current Explorer / Coder / Reviewer pipeline before enabling live Coordinator routing.

The objective is not to redesign the architecture. It is to make the current specialists converge reliably enough that a future Coordinator can absorb orchestration work instead of merely wrapping unstable local loops.

The specific v1.2 goals are:

1. improve `repair_focus → edit` conversion;
2. prevent stale or overloaded Coder context from blocking obvious repairs;
3. eliminate Reviewer exact-quote copying as a source of false protocol failure;
4. classify and preflight model-request size / HTTP failures deterministically;
5. qualify local models for specific roles before quality benchmarking;
6. preserve bounded exploration for all three specialist roles;
7. establish a reproducible baseline before Coordinator routing.

## 2. Why This Still Comes Before Live Coordinator Routing

`improvement-plan-v2.1.md` assumes local specialists converge most of the time.

That assumption is still the critical prerequisite for Coordinator value.

A Coordinator can reduce Primary work only if the underlying workers are already reliable enough that most local loops terminate in `ready_for_review` rather than `no_progress`, `blocked`, `policy_violation`, `infra_failure`, or manual revert.

If Coordinator routing is enabled first, the new layer may spend more local compute only to reach the same failure Primary would already see today.

Therefore:

- fix worker convergence first;
- measure it;
- then enable Coordinator routing.

## 3. Known Failure Patterns

### 3.1 Coder does not act on a correct `repair_focus`

Observed shape:

```text
Coder writes plausible implementation
→ deterministic validation identifies a concrete failure
→ runtime emits correct repair_focus
→ Coder performs additional READ / SEARCH
→ no edit
→ no-progress stop
```

Examples already observed include:

- runtime `NameError` caused by an ORM class imported only under `TYPE_CHECKING`;
- Ruff `F821` for a missing runtime import after functional tests passed.

In both cases:

- diagnosis was correct;
- source location was known;
- repair was local and straightforward;
- Coder still failed to convert diagnosis into an edit action.

This is currently the highest-priority convergence problem.

### 3.2 Reviewer exact citation does not converge

Observed shape:

```text
Reviewer identifies approximately correct source location
→ REPORT includes mismatched source_quote
→ runtime returns citation_fixes + bounded source range
→ Reviewer resubmits mismatched quote
→ retry budget exhausted
```

The model's semantic review may be useful while the protocol fails on exact string reproduction.

Exact quote copying is not itself a useful reviewer capability.

The useful capability is identifying the correct current source evidence.

The runtime should own canonical extraction of exact bytes / lines.

### 3.3 Infra-level Reviewer/model failure

Observed shape:

```text
fresh reviewer retry
→ LM Studio HTTP 400
→ review attempt ends
```

This is distinct from model-quality failure.

Likely classes include:

- context-window overflow;
- malformed / incompatible structured request;
- model-specific request-size limits;
- upstream server rejection.

These must be classified separately from worker-quality / no-progress failures.

### 3.4 Validated terminal drift

Observed shape:

    current edit revision passes focused tests and configured checks
    -> model continues READ / SEARCH / SAFE_EDIT / VALIDATE
    -> no further repository change is needed
    -> protocol errors, no-progress, or turn exhaustion replace a valid success

After successful validation of the current unchanged revision, the runtime
enters a terminal gate. Only FINISH_SUCCESS is accepted.

The first other action is rejected before execution and receives one
deterministic nudge requiring FINISH_SUCCESS. If the model submits another
non-FINISH_SUCCESS action while the same validation remains current, runtime
finalizes ready_for_review mechanically from the existing validation evidence.

The gate is invalidated by any repository or validation-input change. It never
converts an unvalidated revision into success.

Track:

    validated_terminal_gate_entered
    post_validation_action_rejected
    terminal_nudge_issued
    runtime_finalized_after_terminal_nudge

## 4. Shared Specialist Capability Matrix

Bounded exploration is a current-v1 stability capability.

It is not reserved for the future Coordinator.

The capability matrix is:

```text
Explorer:
  READ + SEARCH + TRACE

Coder:
  READ + SEARCH + SAFE_CREATE + SAFE_REPLACE + VALIDATE

Reviewer:
  READ + SEARCH + APPROVED_EXECUTION + REPORT
```

### 4.1 Explorer

Purpose:

- initial repository location;
- call/data-flow investigation;
- locating relevant tests;
- resolving a concrete repository question.

Constraints:

- read-only;
- no mutation;
- no worker recursion;
- focused bounded question;
- literal search by default;
- real source evidence required.

### 4.2 Coder

Purpose:

- local implementation exploration;
- locating bounded edit points;
- responding to validation evidence;
- implementing and repairing the assigned unit.

Constraints:

- exploration stays inside packet-readable scope;
- no recursive Explorer invocation;
- no architecture redesign;
- no arbitrary shell;
- no Git;
- edits only through runtime-safe actions.

### 4.3 Reviewer

Purpose:

- independent semantic verification;
- follow changed code through relevant callers, tests, error paths, and side effects;
- independently execute registered checks when useful.

Constraints:

- no edits;
- no arbitrary shell;
- no Git mutation;
- execution limited to packet/profile-registered actions;
- no final feature acceptance.

`APPROVED_EXECUTION` currently means:

```text
RUN_APPROVED_TEST
RUN_APPROVED_STATIC_CHECK
```

`RUN_APPROVED_PYTHON_SNIPPET` remains out of scope.

## 5. Coder Repair Stabilization

### 5.1 Existing repair behavior remains

The runtime should continue to:

- capture failed pytest / static-check evidence;
- generate a `repair_focus`;
- include exact path / line / rule when available;
- provide recurring repair archetype guidance for known patterns;
- stop repeated identical failures;
- stop repeated no-evidence loops;
- keep validation attempts immutable.

### 5.2 NEW — structured micro repair packet

`repair_focus` should become a structured repair object rather than only descriptive prose.

Example:

```json
{
  "repair_type": "undefined_runtime_import",
  "path": "src/example.py",
  "line": 17,
  "symbol": "AsyncSession",
  "observed_failure": {
    "source": "ruff",
    "rule": "F821",
    "message": "Undefined name AsyncSession"
  },
  "suggested_action": "add or move the required runtime import",
  "allowed_edit_targets": [
    {
      "path": "src/example.py",
      "anchor": "import block"
    }
  ],
  "evidence_refs": [
    "validation-attempt-2.json"
  ]
}
```

The micro repair packet is runtime-generated evidence and guidance.

It is not a new architecture decision.

### 5.3 NEW — one-shot repair supervision gate

After a concrete `repair_focus` exists, if the next action is an edit, continue normally.

If the next action is `BLOCKED` / `REQUEST_CONTRACT_REVISION`, handle normally.

If it is `READ` / `SEARCH`, the runtime checks whether that action produced genuinely new source evidence relevant to the repair.

If yes, allow it.

If no, issue one deterministic supervision nudge:

```text
A concrete editable validation failure is already identified.
The previous action produced no new evidence relevant to that failure.

Your next action must either:
1. edit the identified authorized region, or
2. return BLOCKED / REQUEST_CONTRACT_REVISION with a concrete reason.

Do not perform another unchanged read/search loop.
```

Only one such supervision nudge is issued for the same repair state.

If the model still does not make progress, proceed to the fresh-repair-context experiment or stop according to policy.

### 5.4 NEW — fresh compact repair context experiment

When:

- a concrete `repair_focus` exists;
- Coder has failed to act on it;
- the current worker context contains substantial prior exploration / implementation history;

the runtime may start a **fresh repair context** for the same bounded unit.

This is not a new Coder packet and does not expand scope.

The fresh repair context contains only:

- task/unit identity;
- current required behavior;
- relevant acceptance criterion;
- current cumulative diff for the target area;
- exact validation failure;
- structured `repair_focus`;
- current authorized edit targets;
- bounded current source snippet;
- one relevant test/static-check snippet if needed;
- latest current-file hashes.

Do **not** include:

- full earlier exploration transcript;
- full action history;
- stale validation attempts;
- unrelated task memory;
- earlier model prose;
- redundant source reads.

The goal is to test whether repair failure is caused by context drift / pressure rather than raw coding ability.

Measure at least:

```text
same model + existing context
vs
same model + fresh compact repair context
```

Optionally compare higher-fidelity quantizations if quantization remains a suspect.

Primary metrics:

```text
repair_focus_to_edit_conversion_rate
repair_focus_to_successful_validation_rate
```

### 5.5 Edit-target widening

If the known validation defect sits outside the current stable edit target but inside an already-authorized writable file, widen the authorized edit target mechanically to cover the necessary region.

Do not require Coder to infer permission.

Do not expand to a new file without packet revision.

Record:

```text
repair_target_widened = true/false
```

## 6. Reviewer Citation Stabilization

### 6.1 Replace exact model-authored quotes with runtime canonical materialization

Reviewer should identify source evidence by reference, not reproduce exact source text.

Preferred Reviewer evidence:

```json
{
  "source_ref": {
    "path": "src/example.py",
    "start_line": 71,
    "end_line": 73
  }
}
```

The runtime then reads the current file and materializes:

```json
{
  "source_ref": {
    "path": "src/example.py",
    "start_line": 71,
    "end_line": 73
  },
  "canonical_quote": "exact current source text",
  "source_hash": "sha256:...",
  "verified": true
}
```

The runtime owns:

- exact quote extraction;
- line-range validation;
- current-file hash;
- quote/source consistency.

Reviewer owns:

- choosing the correct evidence range;
- explaining why that evidence supports the finding/contract review.

### 6.2 Invalid source reference behavior

If Reviewer cites unread lines, out-of-range lines, a stale file version, or a forbidden/unreadable file, the report is rejected.

The runtime may return:

- the allowed bounded current source range;
- current hash;
- legal line bounds;
- required evidence obligation id.

The model then chooses a corrected `source_ref`.

Do not ask the model to copy an exact canonical quote.

### 6.3 Reviewer convergence metrics

Track:

```text
source_ref_correction_rounds
source_ref_converged
invalid_source_ref_count
stale_source_ref_count
```

Retire or de-emphasize exact quote-copy accuracy because exact copying is no longer a model responsibility.

## 7. Infra Failure Stabilization

### 7.1 Separate infra outcomes

Classify these as `infra_failure`, not worker-quality failure:

- model server HTTP 4xx/5xx;
- context-window overflow;
- malformed provider-level request;
- structured-output startup incompatibility;
- request timeout before model output;
- model load / provider failure.

They must not increment worker-quality counters unless the model actually produced a substantive worker result first.

### 7.2 NEW — section-level request-size preflight

Before every local model request estimate:

```text
total prompt tokens
total request bytes
configured model context
safety margin
```

Also estimate contribution by logical section.

Example:

```text
estimated_prompt_tokens: 22100
context_limit: 24576
safety_margin: 2500

largest_sections:
1. validation_history: 8400
2. cumulative_diff: 6300
3. source_context: 4100
```

If:

```text
estimated_prompt_tokens >
configured_context - safety_margin
```

do not send the request unchanged.

Return:

```text
input_too_large
```

with total estimate, limit, top 3 largest sections, and suggested reducible sections.

### 7.3 Section caps

All run-growing prompt sections must have explicit caps.

Examples:

```text
validation history:
  counters + recent relevant failures only

worker history:
  recent relevant outcomes only

source context:
  bounded ranges only

diff:
  changed / relevant hunks unless role requires cumulative diff

task history:
  latest relevant state, not full archive
```

Full history remains available in immutable run archives by reference.

Implementation status (v1.2): Coder and Reviewer share the same request
preflight in `worker-runtime.py`; Explorer applies the same policy in its
independent client. The configured context is reduced by the requested output
budget and a fixed safety margin before comparing estimated input tokens.
Rejected requests never reach the provider. Provider HTTP failures retain a
bounded response body plus request totals and the three largest logical prompt
sections, and are reported as `infra_failure` rather than protocol or worker
quality failures.

### 7.4 Capture literal provider rejection body

For LM Studio HTTP failures store:

- status code;
- response body;
- target model;
- request token estimate;
- request byte size;
- configured context;
- largest prompt sections.

Do not store raw full source/model payload merely for diagnostics unless existing policy explicitly allows it.

## 8. Model × Role Compatibility Qualification

Introduce a lightweight role qualification harness before a model enters real quality A/B testing.

Purpose:

```text
Can this model reliably speak and recover within this role protocol?
```

This is distinct from:

```text
How intelligent is this model at the role?
```

A model must pass protocol compatibility before semantic-quality benchmarking.

### 8.1 Coder compatibility fixture

Test at least:

```text
READ
SEARCH
SAFE_CREATE
SAFE_REPLACE
VALIDATE
repair_focus → edit
BLOCKED / REQUEST_CONTRACT_REVISION
structured output recovery
no recursive worker invocation
```

### 8.2 Reviewer compatibility fixture

Test at least:

```text
READ
SEARCH
source_ref generation
invalid source_ref correction
REPORT schema
RUN_APPROVED_TEST
RUN_APPROVED_STATIC_CHECK
unregistered execution rejection + recovery
no edit attempt
no arbitrary shell request
```

### 8.3 Explorer compatibility fixture

Test at least:

```text
literal SEARCH
regex SEARCH
TRACE
bounded READ
negative-search correctness
duplicate/no-evidence recovery
read-only behavior
```

### 8.4 Qualification result

Store:

```json
{
  "model": "example-model",
  "role": "reviewer",
  "protocol_version": "v1.2",
  "result": "pass",
  "fixture_results": {},
  "tested_at": "...",
  "context_length": 24576,
  "quantization": "..."
}
```

A protocol failure should not be disguised as poor semantic benchmark quality.

## 9. Diagnostics for Current Failure Repros

### 9.1 Coder repair incidents

For each canonical failing run:

1. inspect literal `repair_focus`;
2. inspect literal next action;
3. inspect current edit-target anchors;
4. record remaining context budget;
5. classify next action as edit, evidence-producing read/search, no-evidence read/search, blocked/revision, or malformed/protocol failure;
6. rerun against the one-shot supervision nudge;
7. rerun against fresh compact repair context;
8. optionally compare higher-fidelity quantization.

Do not rely on summaries.

### 9.2 Reviewer citation repro

For the existing Muse citation failure:

1. rerun using the new `source_ref` protocol;
2. runtime materializes canonical quote;
3. measure whether Reviewer can converge on a valid source range;
4. compare with Qwen fresh-context if needed.

If source-range selection still fails randomly, investigate model/prompt quality.

If source-range selection succeeds, retire exact-quote copying from the protocol.

### 9.3 HTTP 400 repro

For the existing rejected reviewer request:

1. capture literal LM Studio response body;
2. calculate total request tokens/bytes;
3. calculate section-size breakdown;
4. compare against model context;
5. run preflight;
6. verify the request is either compacted safely before send or rejected locally as `input_too_large`;
7. confirm no raw unexplained HTTP 400 reaches task-quality policy.

## 10. New Instrumentation

Track at least:

### Coder repair

```text
repair_focus_issued
repair_focus_next_action
repair_focus_next_action_is_edit
repair_focus_next_action_has_new_evidence
repair_supervision_nudge_issued
fresh_repair_context_used
repair_focus_to_edit_conversion_rate
repair_focus_to_successful_validation_rate
repair_target_widened
```

### Reviewer evidence

```text
source_ref_correction_rounds
source_ref_converged
invalid_source_ref_count
stale_source_ref_count
approved_execution_attempts
approved_execution_results
rejected_unregistered_execution_attempts
```

### Infra

```text
infra_failure_count
input_too_large_count
http_4xx_count
http_5xx_count
model_request_timeout_count
prompt_estimated_tokens
prompt_estimated_bytes
largest_prompt_sections
```

### Role compatibility

```text
compat_runs
compat_pass
compat_fail
compat_failure_reason
model
quantization
context_length
role
```

### Discovery

Keep existing role-local discovery evidence:

```text
observed paths / lines
searches
trace edges
duplicate/no-evidence stops
role-local question resolved
```

## 11. Baseline Measurement

Select approximately 10–15 representative recent real units.

Prefer small / medium risk units that would actually benefit from local execution and include a mix of:

- first-pass success;
- validation repair;
- static-check repair;
- Reviewer finding;
- Reviewer execution;
- bounded exploration.

Skip units that would always route directly to Primary under current policy.

Run under patched v1.2.

Record:

```text
% reaching Reviewer
% reaching ready_for_review
% accepted without manual revert
repair_focus_to_edit conversion
repair_focus_to_successful_validation
source_ref convergence
infra_failure count
approved Reviewer execution success
average Coder turns
average Reviewer turns
local token use
wall-clock time
```

Also record model / quant / context length for every local role.

This becomes the stability denominator for future Coordinator efficiency claims.

## 12. Exit Criteria

Live `improvement-plan-v2.1.md` Phase 2 may begin only when all of the following hold.

### 12.1 Coder repair convergence

`repair_focus_to_edit_conversion_rate` materially improves from the near-zero failure pattern previously observed.

A specific numeric threshold may be chosen after the first v1.2 sample, but `still near zero` is an explicit no-go.

The baseline should also show that edits after repair focus can reach successful validation at a useful rate.

For the next frozen expanded repeat, fix the decision rule before running it:
at least 70% of units receiving `repair_focus` must make an edit as the
immediate next action, and at least 90% of those units must eventually reach
successful focused validation in that call. Require at least ten such units
for the rate to be a release measure. A recorded Primary takeover remains a
Coder miss, and a case that repeats the same high-risk wrong-field failure in
both rounds is a no-go even if aggregate rates pass. The previous 22-cell
denominator measured 12/21 immediate edits and 20/21 eventual successful
validations, so it does not pass this newly fixed immediate-edit threshold.

`python benchmarks/v1_2_readiness.py` reports Explorer, Coder, Reviewer,
infrastructure, protocol, and Primary acceptance denominators from one
frozen two-round batch. Its `pipeline_decision` is distinct from full Phase 2
release: current model-role qualification, the executable capability matrix,
and Primary integration review still need final evidence.

### 12.2 Reviewer source evidence convergence

For the sampled units:

- Reviewer `source_ref` converges within the existing retry budget;
- canonical quote materialization is performed by runtime;
- exact quote copying is no longer a model blocker.

If Reviewer still cannot select valid evidence ranges, identify a model/prompt root cause before Coordinator routing.

### 12.3 Infra failures are handled deterministically

There are zero unhandled raw model-server failures in the baseline.

Context overflow / rejected requests must be caught in preflight where possible or classified as `infra_failure` with diagnostic evidence.

They must not silently terminate worker-quality flows.

### 12.4 Role compatibility is measurable

The active Explorer, Coder, and Reviewer models each have a stored compatibility result for the current protocol version.

Any new model proposed for a role must pass compatibility qualification before semantic A/B testing.

Current qualification evidence is in `benchmarks/STABILITY-V1-RESULTS.md`.
The active mapping is OSS20B Explorer, Q4_K_M Qwen Coder, and Muse Reviewer.
Muse now uses bounded native OpenAI tool calls, which passed repeated frozen
ordinary, high-risk, and hidden-defect reviews. The current three-role live
compatibility archive is `benchmarks/results/role-compat/role-compat-20260926T084919Z.json`:
3/3 roles passed every required action with no infrastructure failure. An
earlier live probe hit an Explorer `peg-native` HTTP 400; Explorer now makes one
changed-shape, required-tool retry for that exact server failure. The passing
run does not replace multi-unit stability measurement. Prior alternative-model
screening remains historical evidence, not an active role substitution.

### 12.5 Capability matrix is enforced

Frozen E2E fixtures prove:

```text
Explorer:
  bounded READ / SEARCH / TRACE

Coder:
  bounded READ / SEARCH / SAFE_EDIT / VALIDATE

Reviewer:
  bounded READ / SEARCH / approved execution / REPORT
```

and prove prohibited capabilities remain unavailable.

Implementation status (v1.2): `benchmarks/capability-matrix-v1.2.json` freezes
the allowed and prohibited cells and binds each cell to an executable pytest
node. A meta-test verifies every referenced class and test method still exists;
the normal full suite executes the referenced behavioral tests. Explicit schema
tests fail if mutation, shell, Git, or delegation actions enter a role that must
not expose them. This runtime enforcement evidence is separate from the live
model qualification results in section 12.4.

### 12.6 Baseline exists

A real convergence baseline is recorded for approximately 10–15 representative units.

Do not proceed using an assumed savings/convergence number.

The first formal 12-unit baseline is recorded in
`benchmarks/V1.2-UNIT-BASELINE.md`. It used six frozen cases twice, with
Explorer success 10/12, Coder ready 9/12, valid Reviewer reports 6/9 reached,
E2E pass 5/12, and zero infrastructure failures. Explorer remained an
independent denominator. The result is **NO-GO** for v1.2 exit and live v2.1
Coordinator routing: Reviewer repeated-read no-progress and Coder repair
no-progress recur on fixed cases. The earlier stopped calibration and
alternative-model probes remain historical diagnostics, not this denominator.

The subsequent frozen post-fix comparison is recorded separately in
`benchmarks/V1.2-ITERATION-RESULTS.md`. It reached 12/12 Explorer evidence,
12/12 Coder readiness, 12/12 valid Reviewer reports, 12/12 protocol E2E,
and zero infrastructure failures with the original role models. This is a
go for continued v1.2 local-unit baseline measurement, not automatic
v2.1 Coordinator release: Reviewer first-report errors and six-fixture
coverage still warrant wider real-unit sampling, and immediate
`repair_focus`-to-edit conversion improved only modestly over the first
baseline (6/10 after correcting a missed `SAFE_REPLACE_LINE` metric cell).

The later expansion is tracked separately in
`benchmarks/V1.2-EXPANDED-COVERAGE.md`: approximately ten distinct frozen
behavioral units are now available, with two-source real-code Reviewer
hidden-defect challenges. New positive units were repeated in separate
batches, not pooled into the immutable six-case baseline. One adapter case
exposed a silent-filtering defect that protocol E2E and Reviewer initially
missed; Primary rejected it, the protected contract was strengthened, and
two new high-risk rounds passed Primary full review. The next numerical
baseline should run the complete expanded suite under one frozen runner hash
before any cross-model effectiveness claim or v2.1 Coordinator routing.

That one-round unified expanded suite is now recorded in
`benchmarks/V1.2-EXPANDED-UNIT-BASELINE.md`: 11/11 Explorer evidence,
11/11 Coder ready, 11/11 valid Reviewer reports, 11/11 protocol E2E,
11/11 Primary-accepted diffs, and zero infrastructure failures. Three
Reviewer reports required a recoverable protocol correction, and this is
only one complete expanded round. Continue v1.2 measurement/compatibility;
do not infer v2.1 Coordinator readiness or alternative-model equivalence.
The separate candidate screen in `benchmarks/V1.2-MODEL-CANDIDATES.md`
further shows that real Explorer line citations do not guarantee correct
diagnosis on `internal-trace`; preserve both measures rather than claiming
11/11 semantic Explorer accuracy. Bonsai and Devstral passed role protocol
compatibility, but the active model mapping remains unchanged.

The frozen, same-input two-round expanded audit is now in
`benchmarks/V1.2-TWO-ROUND-AUDIT.md`. It recorded 21/22 Explorer real-line
evidence, 21/22 Coder readiness, 21/21 reached Reviewer passes, 21/22
Primary-accepted diffs, zero infrastructure failures, and 12/21 immediate
`repair_focus`-to-edit actions. A separate Primary semantic audit found only
16/22 complete Explorer diagnoses. The first-round two-file
`sample-identity` unit failed and repeated targeted Qwen rework showed a
stable wrong-field signature, followed by three quality-gate failures under
a narrower field-aware packet. **Phase 2 remains NO-GO.** The post-batch
protected-test strengthening and generic LM Studio role-alternation retry
are new changes, not silently included in that frozen denominator.

The subsequent two-unit `sample-identity` experiment is recorded separately
in `benchmarks/V1.2-TWO-ROUND-AUDIT.md`. It found a pytest node-selector
handoff/Reviewer path bug, now fixed and unit-tested, but all three first-unit
Coder diffs still omitted the existing `labels` exclusion. A new protected
assertion catches that regression. These runs are not pooled into the frozen
baseline; Primary recorded takeover and **Phase 2 remains NO-GO**.

### 12.7 Explorer diagnosis is a separate release gate

Explorer must be scored twice: actual source/test line evidence and a
Primary-reviewed diagnosis of the source-predicted outcome versus each
contract-relevant assertion. Coder or Reviewer success cannot repair an
Explorer miss. The machine-readable frozen audit in
`benchmarks/V1.2-EXPLORER-SEMANTIC-AUDIT.json`, checked by
`benchmarks/explorer_semantic_audit.py`, records 21/22 mechanical evidence
reports but only 16/22 complete diagnoses, and only 16/22 cells where both
strict Explorer diagnosis and protocol E2E pass. This is **NO-GO**.

For a future same-input expanded repeat, require at least 90% strict Explorer
diagnosis, real line evidence for each counted success, and no repeated
miss on one frozen case before Phase 2 routing. Keep first-call failures and
later focused retries separately visible; do not silently overwrite a failed
Explorer result with a downstream Coder success.

The focused OSS reasoning-effort check in
`benchmarks/V1.2-MODEL-CANDIDATES.md` further separates context from output
budget: medium reasoning improved three weak semantic cases only to 3/6,
while high reasoning repeatedly exhausted 2048 or 4096 output tokens well
before approaching the 32768 input-context window. The active low-effort
configuration remains unchanged. Explorer, Coder, and Reviewer now identify
an empty response with `finish_reason=length` as an explicit
`output_token_limit` infrastructure failure rather than an unexplained
worker-quality miss.

Subsequent focused OSS follow-ups produced 5/8 complete diagnoses despite
8/8 mechanically successful reports. Medium reasoning with a 4096 output
reserve produced 5/6 strict diagnoses on the same weak cases after full-report
re-audit, versus 3/6 at the default reserve. Temperature zero reached 6/6
on those three cases, but an expanded 11-case first round had at least four
strict misses, making the required 20/22 impossible even with a perfect
second round. Compact findings are truncated at 800 characters; all release
semantic judgments must use the full diagnostic report.
The semantic-audit CLI now refuses a frozen batch if any compact report lacks
a matching in-workspace full diagnostic report or their statuses disagree;
the existing 22-cell audit still validates as 16/22 strict.
Use `python benchmarks/explorer_semantic_audit.py --release-gate` for the
Explorer-only §12.7 decision. It requires two rounds of the same 11-or-more
case identities, an identified Primary semantic reviewer, at least 90% strict
diagnoses, and no case missed in both rounds. It also compares the source
manifest, packet contract (excluding the unique run ID), protected read-only
files, and faulty source bytes recovered from the Coder preimage archive
across rounds. It exits nonzero on NO-GO. The
current frozen batch returns NO-GO (16/22, with repeated
`metadata-key-length` and `sample-identity` misses). This gate does not certify
the other §12 exit criteria; preserve the immutable run archives for later audit.
Bonsai Explorer failed three default-budget calls before a report, and its
single larger-budget report omitted relevant assertions. Devstral Coder
passed the metadata boundary twice but failed the mapping container/element
distinction twice; none of these trials changes the active role mapping or
the **NO-GO** decision. Detailed frozen archives and Primary judgments are
in `benchmarks/V1.2-MODEL-CANDIDATES.md`.

A subsequent per-test-function Explorer investigation experiment preserved
independent full reports but reached only 1/4 strictly complete weak cases in
each of two trials, despite 15/15 mechanically valid subreports per trial.
It is diagnostic only; it does not change the frozen baseline, active model
routing, or Phase 2 gate.

An opt-in source-backed assertion review protocol was also screened on the
parameterized mapping fixture. Exact read-line quote and target-ID coverage
can be enforced mechanically, but the completed OSS report still assigned the
wrong branch/exception to `str` and `bytes`; Bonsai did not complete the
records. The unqualified runtime mode was removed after the trial.
Neither result justifies an expanded baseline or Phase 2 release.

A new one-round, eleven-case OSS Explorer candidate screen with `medium`
reasoning and 4096 output tokens produced 11/11 mechanically cited reports
but only 7/11 Primary-reviewed complete diagnoses. Even a perfect second
round would be below the fixed 20/22 threshold, so this setting was not
activated and the paired candidate was stopped after one round. The exact
ratings and archive are in `benchmarks/V1.2-EXPLORER-MEDIUM-SCREEN.json`.

A later disposable Explorer probe supplied the trusted protected-test failure
output already observed before the investigation. It returned 2/3 mechanical
reports but 0/3 strictly correct diagnoses on the weak cases; the complete
reports and review are in `benchmarks/V1.2-MODEL-CANDIDATES.md`. The active
Explorer input and Phase 2 NO-GO decision remain unchanged.

A subsequent proactive Coder repair-context trial improved first-repair
immediate edits to 8/10 in a fixed five-case, two-round diagnostic batch,
but only 8/10 units passed E2E and the two-file `sample-identity` case failed
in both rounds. One further changed-approach replay exposed and repaired a
newly introduced missing-attribute diagnostic path, but Coder introduced
another nonexistent field and failed. Primary recorded takeover after three
consecutive quality-gate failures. These calls do not replace the frozen
22-cell denominator or clear §12.1; details and immutable archive paths are
in `benchmarks/V1.2-TWO-ROUND-AUDIT.md`. Phase 2 remains **NO-GO**.
The proactive context's first implementation dropped prior source reads;
current code preserves them. A later bounded duplicate-read restoration and
removal of test-name-derived field "invariants" have unit evidence and a
separate two-round `sample-identity` diagnostic: Coder, Reviewer, independent
pytest/Ruff, and Primary diff review passed 2/2 under the active mapping. Both
runs needed a repair nudge before the first edit, so this does not clear the
70% immediate-edit gate. Explorer gave real citations twice but only one
strictly complete two-file diagnosis. These runs are not pooled with the
frozen 22-cell baseline; see `benchmarks/V1.2-TWO-ROUND-AUDIT.md`.

### 12.8 Frozen role-aligned decision rule for the next candidate (2026-09-27)

Sections 12.1 and 12.7 above remain the **original** gate and their frozen
results remain NO-GO. The next changed-runtime batch uses the separately named
`role-aligned-v1` gate. Select it explicitly with
`python benchmarks/v1_2_readiness.py --gate-version role-aligned-v1`.
Do not recalculate historical acceptance under this rule or pool diagnostic
pilots with the candidate batch.

For 11 or more identical frozen cases in two rounds, the role-aligned gate
requires:

- Explorer file/line evidence in at least 90% of cells, no repeated evidence
  miss on one case, and zero Primary-rated incorrect source claims. Report its
  strict complete-diagnosis score separately as a capability measure;
  incomplete but accurately bounded diagnoses stay visible.
- At least ten Coder units receiving `repair_focus`, with at least 90% of them
  reaching successful focused validation in their bounded call. Record the
  immediate-next-edit rate and redundant reads as efficiency diagnostics, not
  substitutes for validation. Keep the existing two-round `sample-identity`
  requirement and protected cross-function tests.
- All reached Reviewer units return a valid `pass_to_primary` report with
  required citations; zero infrastructure failures; at least 90% protocol E2E
  and Primary-accepted actual diffs. Preserve every run's separate outcome.

An Explorer claim rated `incorrect` must be corrected by Primary before it is
used in a Coder packet. The existing E2E runner already prepares the packet
before Explorer and therefore does not prove that handoff; require a separate
unknown-location handoff fixture before enabling live Coordinator routing.
The active three-role compatibility result, capability-matrix behavioral tests,
and Primary integration review remain required by sections 12.4-12.5.

Stop after one complete candidate batch, or at a case boundary when its
remaining cells cannot mathematically reach a hard gate, and at most one
focused repair and repeat on affected cases. Record exactly one of: release GO after every gate
and integration check passes; supervised use with explicit Primary takeover
for unsupported investigation classes; or NO-GO if an unsafe handoff, false
acceptance, scope escape, validation error, or unbounded loop remains. A
focused repeat does not replace a failed full-batch denominator.

The first role-aligned candidate reached three Explorer/E2E misses in its first
five cells, making the 20/22 gates unreachable. It was stopped, and one
two-case protocol repair repeat passed without replacing that denominator.
The decision is supervised use with Primary review; live Phase 2 remains NO-GO.
See `benchmarks/V1.2-ROLE-ALIGNED-CANDIDATE.md` for immutable workspace paths
and failure signatures. Future candidates may use the runner's
`--stop-when-unreachable` flag to record the same mathematical stop at a case
boundary.

### 12.9 Separately scoped localization-only implementation entry (2026-09-28)

The general-investigation candidate in `batch-180cd482857e` failed the
zero-incorrect-source-claim rule on its first completed cell. The original and
role-aligned investigation gates remain NO-GO. Supplying observed test failures
and splitting diagnosis per test were already tried historically without
reproducible semantic improvement; do not repeat those experiments unchanged.

A new, explicitly narrower `localization-v1` gate may qualify **implementation
of localization-only Phase 2 routing**, not general autonomous investigation.
This is a changed capability boundary, not a retroactive pass or proof of
improved semantic reasoning. Keep the default investigation mode unchanged
until a deployment decision explicitly selects a qualified mode.

Preregistered candidate requirements:

- Same 11+ frozen fixture types in two rounds, all attempts retained, frozen
  runtime/config/runner manifest. An input change invalidates the candidate.
- At least 90% independent Explorer localization success and no repeated miss
  on one case. Runtime-generated source_refs must match the frozen source
  hashes and exact displayed ranges. The held-out scorer must find every
  injected implementation location and a related test assertion in the selected
  excerpts; correct filenames or imports alone are insufficient.
- Zero fabricated/changed-source quotations. Semantic diagnosis is explicitly
  **not evaluated**, not assigned a synthetic perfect score. General behavioral
  questions require Primary takeover rather than being silently downgraded to
  location questions.
- Preserve §12.8 Coder/Reviewer/infra/Primary thresholds: 10+ repair-focus units,
  90% eventual validation, every reached Reviewer converges with required
  citations, no infrastructure failures, 90% protocol E2E and Primary accepts,
  and sample-identity Coder acceptance in both rounds.
- Current role compatibility, capability matrix/full regressions, a real
  unknown-source locator-to-Coder handoff, and Primary integration review.
  A locator report never grants acceptance or scope expansion.

Use `benchmarks/localization_readiness.py --batch <candidate>` for this separate
pipeline assessment. It must never output qualification for general semantic
routing. A GO permits implementing a route that dispatches only locator work;
before enabling that route, the Coordinator contract must mechanically reject
unsupported investigation kinds and preserve Primary's acceptance authority.
It is not a deployed Coordinator and not the general Phase 2 release gate.

Recorded outcome (2026-09-28): frozen `localization-v1` candidate
`batch-488faa0f3eee` met this implementation-entry gate: 22/22 verified
locations, 21/21 repair-focus units eventually validated, 22/22 Reviewer and
protocol passes, 20/22 Primary accepts, zero infrastructure failures, and
both sample-identity rounds accepted. Current role compatibility, full
regressions and an unknown-source handoff passed. See
`benchmarks/V1.2-LOCALIZATION-CANDIDATE.md` for evidence and the two retained
Primary rework decisions. General semantic routing remains NO-GO.

## 13. Relationship to `improvement-plan-v2.1.md`

This plan gates live Coordinator routing.

Allowed in parallel:

```text
improvement-plan-v2.1 Phase 1
Coordinator schema / contract / guardrail authoring
```

Allowed independently during stability work:

```text
Phase 1.5 Reviewer approved execution
```

Not allowed until v1.2 exit criteria pass:

```text
Phase 2 live Coordinator routing
```

The v2.1 architecture remains unchanged.

## 14. Explicit Non-Goals

Do not use this stability pass to add:

- live Coordinator routing;
- a new Analyzer model;
- a separate QA agent;
- arbitrary Reviewer shell;
- arbitrary Reviewer Python snippets;
- generic DAG framework;
- per-worker Git worktrees;
- parallel Coders;
- vector memory;
- UI;
- multi-language/provider abstractions.

Do not add a new model merely to solve a deterministic protocol problem.

Prefer:

```text
deterministic runtime
→ constrained protocol
→ model role qualification
→ only then model replacement
```

## 15. Future Efficiency Ideas — Not Stability Blockers

### 15.1 Compact repo / symbol map

Potential future optimization:

```text
path
symbols
signatures
imports / dependency hints
file hash
```

Use it only as navigation guidance.

It is not proof and must invalidate with source hash changes.

### 15.2 Fresh Coder context per future Coordinator unit

A future Coordinator may prefer disposable Coder contexts per behaviorally cohesive unit, while continuity lives in Coordinator memory and immutable runtime evidence.

### 15.3 Parallel work / worktrees

Only consider after Coordinator is stable, sequential local execution demonstrates value, and parallelism becomes an actual bottleneck.

## 16. Recommended Execution Order

```text
1. Implement source_ref → runtime canonical citation
2. Add section-level request-size preflight / diagnostics
3. Add structured repair_focus micro packet
4. Add one-shot repair supervision nudge
5. Add fresh compact repair-context experiment
6. Add model × role compatibility fixtures
7. Freeze E2E capability fixtures
8. Run 10–15 unit stability baseline
9. Record convergence metrics
10. Decide whether v1.2 exit criteria pass
11. Only then enable v2.1 Phase 2 live Coordinator routing
```

The order intentionally fixes deterministic protocol problems before changing models or adding orchestration layers.

## 17. Guiding Principle

> Do not add another agent to compensate for a failure the runtime can classify, constrain, verify, or repair deterministically.

The local models should spend their capability on:

```text
understanding
implementation
semantic review
bounded exploration
```

The runtime should own:

```text
scope
exact evidence
mechanical validation
request sizing
protocol enforcement
state integrity
failure classification
```

That separation is the main stability objective of v1.2.
