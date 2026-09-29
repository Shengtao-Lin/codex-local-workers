# improvement-plan-v2.1.md

## 0. Status and Relationship to Other Documents

This supersedes `improvement-plan-v2.md`. The target architecture and the
phased-rollout philosophy are unchanged. Compared to v2, this revision:

1. Adds deterministic runtime enforcement for every rule that previously
   depended on the Coordinator's own restraint (see §6a).
2. Splits Coordinator output into two kinds that are governed differently:
   schema-validated packet generation, and a closed-enum decision (see §4.3).
3. Closes an escalation-avoidance gap in the local rework loop, where a
   Coordinator that rewrites a stuck packet's wording could reset
   failure-signature streaks indefinitely (see §16).
4. Keeps `RUN_APPROVED_PYTHON_SNIPPET` explicitly out of scope until evidence
   justifies it (see §11).
5. Decouples the Reviewer execution-capability rollout from the Coordinator
   rollout so each can be tested, measured, and rolled back independently
   (see §24).
6. Adds instrumentation for whether the new runtime backstops actually fire
   (see §23).
7. Makes Phase 2 onward conditional on the exit criteria in
   `stability-plan-v1.2.md`. Phase 1 (schema/contract authoring) may proceed
   in parallel because it does not touch live routing and does not depend on
   current Coder/Reviewer convergence.
8. Makes bounded exploration a shared specialist capability rather than an
   Explorer monopoly: Coder and Reviewer retain the local discovery needed
   to implement and verify their own unit, under different mutation and
   execution permissions (see §7.1).
9. Requires any local model entering Coder/Reviewer/Coordinator semantic
   quality evaluation to first pass the model × role compatibility
   qualification defined in `stability-plan-v1.2.md`.
10. Uses runtime-materialized canonical source evidence for Reviewer citations:
    Reviewer selects a current `source_ref`; the runtime validates the range,
    binds it to the current source hash, and materializes the exact quote
    (see §12 and `stability-plan-v1.2.md`).

Sections not called out above are unchanged from v2 in substance and are
restated in full here so this file is a complete, standalone reference.

## 1. Objective

Upgrade the current Local Python Agent Orchestration Kit so the Primary
Agent does substantially less per-unit orchestration work, while preserving
every safety property the current system already has:

- Primary-owned architecture, scope, risk, and final acceptance
- read-only Local Explorer
- bounded Local Coder with deterministic runtime controls
- independent Local Reviewer
- schema-v2 implementation packets
- risk-routed Primary review
- immutable run archives and evidence
- validation, focused pytest, JUnit evidence, diff/state integrity checks
- bounded repair/rework behavior

The main architectural change is a **Local Coordinator** between Primary and
the local specialists. The difference from v2 is where the new autonomy is
allowed to be freeform (packet authorship) versus where it must be
mechanically checked (every boundary rule in §4.2).

## 2. Target Architecture

```text
User
  ↓
Primary Agent
  ├─ understand request
  ├─ architecture
  ├─ implementation plan
  ├─ feature-level contracts/invariants
  ├─ feature/integration risk floors
  └─ acceptance criteria
        ↓
Local Coordinator
  ├─ turn implementation plan into bounded work units
  ├─ decide whether Explorer is needed
  ├─ create unit packets
  ├─ choose unit risk/review routing within Primary's floors
  ├─ dispatch Explorer / Coder / Reviewer
  ├─ manage local retries/rework
  ├─ maintain execution memory
  ├─ collect runtime evidence
  └─ escalate only when required
        ↓
Deterministic Guardrail Layer   (NEW — see §6a)
  ├─ contract-id membership check
  ├─ risk-floor clamp
  ├─ dependency / scope diff check
  └─ schema validation of generated packets
        ↓
Local Specialists
  ├─ Explorer
  ├─ Coder
  └─ Reviewer
        ↓
Deterministic Runtime
  ├─ scope enforcement
  ├─ safe edits
  ├─ validation
  ├─ test execution
  ├─ hashes / evidence
  └─ immutable run history
        ↓
Local Coordinator
        ↓
Compact feature/unit result
        ↓
Primary Agent
  ├─ high-value review
  ├─ integration review
  ├─ accept / replan / takeover
  └─ final user response
```

Primary still moves from:

```text
architect + project manager + packet author + reviewer
```

to:

```text
architect + high-value reviewer + final authority
```

The Deterministic Guardrail Layer is new. It is what actually makes the
"Coordinator must not…" rules in §4.2 true, instead of leaving them as
prompted intentions that a 20B–30B local model may or may not respect under
pressure.

## 3. Primary Agent Responsibilities

Primary remains authoritative for:

- user intent
- architecture
- feature-level implementation plan
- externally observable behavior
- invariants and contracts
- feature-level scope boundaries
- public API / compatibility decisions
- dependency decisions
- feature risk and integration risk
- contract risk floors
- acceptance criteria
- final Git decisions
- final review / accept / replan / takeover
- final response to the user

Primary should no longer need to manually author every detailed Coder
packet. Primary should produce a compact **feature plan** instead.

## 4. Local Coordinator

### 4.1 Purpose

The Local Coordinator is the execution manager for an already-decided
Primary implementation plan. It may convert an `implementation plan` into an
`execution plan`. It must not convert `requirements` into `new architecture`.
The Coordinator is not a peer architect.

### 4.2 Coordinator Responsibilities

The Coordinator may:

- read the Primary feature plan
- read task memory and current repository evidence
- split the feature plan into behaviorally cohesive implementation units
- preserve atomic invariants when splitting work
- assign dependencies between units
- decide whether a focused Explorer call is needed
- summarize Explorer findings into the next unit packet
- generate schema-v2 Coder packets
- select readable/writable scope within Primary-authorized areas
- choose focused tests
- assign unit risk, but never below Primary risk floors
- route work through Coder and Reviewer
- manage bounded local rework loops
- track progress and failure signatures
- prepare a compact feature-level handoff to Primary

The Coordinator must not:

- redesign architecture
- lower feature/integration/contract risk floors
- add new dependencies without escalation
- expand into forbidden areas
- change public contracts without escalation
- make security decisions that Primary did not authorize
- silently weaken acceptance criteria
- accept the final feature on behalf of Primary

Every item in the "must not" list is backed by a mechanical check in §6a.
Prompt language alone is not treated as sufficient enforcement for any of
them, because the Coordinator is a local model of the same class (20B–30B)
that Coder and Reviewer already show occasional protocol-following gaps
under — see `stability-plan-v1.2.md` §3 for concrete examples.

### 4.3 Coordinator Output: Two Kinds, Governed Differently

v2 treated Coordinator output as one set of high-level outcomes. In
practice the Coordinator produces two structurally different things, and
they should be constrained differently.

**4.3.1 Packet generation (structured, schema-validated).** Splitting a
feature plan into units, writing schema-v2 Coder packets, choosing focused
tests, and summarizing Explorer findings are generative tasks — the same
category of work Coder already does under schema validation. These outputs
pass through the Deterministic Guardrail Layer (§6a) before dispatch, not
merely reviewed after the fact.

**4.3.2 Decision output (closed enum).** The Coordinator's own status after
a step is a small, closed set:

```text
CONTINUE
REWORK_LOCAL
ESCALATE_PRIMARY
FEATURE_READY
```

This layer is validated as a strict enum with required accompanying fields
(`unit_id`, a reason code for `REWORK_LOCAL`/`ESCALATE_PRIMARY`). A response
that doesn't parse as one of these four is a protocol failure, not a
substantive answer to accept.

Do not collapse these two into one interface. Restricting the whole
Coordinator to enum output would remove the generative capability v2 needs
from it; treating packet generation as unconstrained free text would remove
the one place a runtime check can catch drift before it reaches a worker.

## 5. Work-Unit Decomposition

The Coordinator should break a feature into **behaviorally cohesive
implementation units**. Do not split merely by line/file count.

Good unit:

```text
"After lease loss, Worker.execute must not commit success or failure,
with focused tests proving both paths."
```

Bad split:

```text
Unit 1: add bool
Unit 2: change if
Unit 3: add assertion
```

A high-risk feature may contain lower-risk units, but atomic high-risk
invariants stay high-risk.

## 6. Risk Ownership

Use separate levels:

```text
feature_risk
unit_risk
integration_risk
contract risk_floor
```

Rules:

- Primary sets feature risk.
- Primary sets integration risk.
- Primary sets contract risk floors.
- Coordinator may classify unit risk.
- Coordinator may raise risk.
- Coordinator may never lower a unit below an owned contract's risk floor.
- Coder and Reviewer never lower risk.
- Local success never removes a Primary-mandated integration review.

### 6a. Deterministic Enforcement (NEW)

Each rule above gets a runtime check, not just a stated rule:

- **Contract-id membership check.** The runtime holds the set of
  `contract_id`s declared in Primary's `feature-plan.json`. Any
  Coordinator-generated packet referencing a `contract_id` outside that set
  is rejected and the unit is routed to `ESCALATE_PRIMARY` automatically —
  the Coordinator does not get to self-report this.
- **Risk-floor clamp.** The runtime computes
  `effective_unit_risk = max(coordinator_declared_risk, floor(owned_contract_ids))`.
  The Coordinator's declared value is a proposal, not the value used; the
  floor always wins.
- **Dependency / scope diff check.** Any import, package-manifest, or path
  change outside a packet's authorized `scope.writable` / `scope.readonly`
  triggers automatic escalation, independent of what the Coordinator's own
  packet claims about scope.
- **Schema validation.** Every Coordinator-generated Coder packet is
  validated against the same schema-v2 contract Coder packets already
  require; a malformed or incomplete packet is rejected before dispatch,
  the same as an invalid Coder or Reviewer report is today.

Record how often each of these actually fires — see the new
`policy_violation_blocked_count` metric in §23. A count of zero over a
meaningful sample is evidence the Coordinator is behaving; a nonzero count
is the mechanism doing its job, not necessarily alarming on its own, but a
rising rate is a sign the Coordinator model or prompt needs attention.

## 7. Explorer Routing

Explorer should remain optional. The Coordinator decides whether Explorer
is needed for a unit.

Use Explorer when:

- relevant code is not already located
- caller/callee flow is unclear
- focused tests are not known
- existing evidence is stale
- Coordinator has one concrete unanswered repository question

Do not use Explorer when:

- paths and symbols are already known
- valid cached evidence exists
- the unit is trivial/local
- the Coder packet already contains enough context

Explorer output should remain read-only and bounded. The Coordinator should
forward only concise findings, never large raw transcripts.

### 7.1 Shared Bounded Exploration

`Explorer` is a role, not the exclusive owner of every read or search. All
three specialists need enough local discovery capability to complete their
own responsibility without treating an earlier model's summary as proof.
The intended capability matrix is:

```text
Explorer:
  READ + SEARCH + TRACE

Coder:
  READ + SEARCH + SAFE_EDIT + VALIDATE

Reviewer:
  READ + SEARCH + APPROVED_EXECUTION + REPORT
```

The same verbs have role-specific purpose and limits:

- Explorer performs focused repository location and call-flow investigation.
  `TRACE` is read-only traversal from observed symbols/call sites and must
  cite real files and lines; it is not program execution or speculative prose.
- Coder uses `READ` and `SEARCH` to locate the bounded edit and to respond to
  validation/repair evidence. Its exploration remains inside packet-readable
  scope and the existing no-new-evidence limits. It does not need to invoke a
  separate Explorer for every missed anchor or post-validation diagnosis.
- Reviewer uses a fresh context and independently reads/searches changed code,
  tests, callers, and relevant error paths. `APPROVED_EXECUTION` is an umbrella
  capability for packet/profile-registered actions such as
  `RUN_APPROVED_TEST` and `RUN_APPROVED_STATIC_CHECK`; it is not arbitrary shell
  access and does not include edits.

Explorer remains independently measured whenever a case requires initial
location. Later Coder or Reviewer success must not overwrite an Explorer
failure. Conversely, a successful Explorer report does not remove Coder's or
Reviewer's obligation to inspect current source before editing or reporting.
Each role's evidence should record observed paths/lines, searches, duplicate or
no-evidence stops, and (for Reviewer) approved execution ids and results.

## 8. Coder Role

Qwen remains the implementation specialist. Coder should receive: unit
goal, contract ids, required behavior, acceptance scenarios, read scope,
write scope, forbidden scope, edit targets / known symbols, focused tests,
validation profile, and inherited rework findings when relevant.

Coder may:

```text
READ
SEARCH
SAFE_CREATE
SAFE_REPLACE
VALIDATE
repair within configured limit
```

Coder should not: invoke Explorer, invoke Reviewer, invoke Coordinator,
invoke Codex, use Git, redesign architecture, broaden scope, change
protected tests/contracts, or install dependencies.

This prohibition is about worker recursion, not exploration. Coder's own
bounded `READ` and `SEARCH` are first-class implementation capabilities as
defined in §7.1.

## 9. Local Reviewer Upgrade

The current Reviewer is read-only and evidence-driven. v2.1 gives Reviewer
a **constrained execution capability** so it can independently verify
behavior instead of only reasoning over existing Coder validation evidence.
This does **not** mean unrestricted shell access.

The recommended model is:

```text
Reviewer
  ↓
trusted runtime actions
  ├─ READ
  ├─ SEARCH
  ├─ RUN_APPROVED_TEST
  ├─ RUN_APPROVED_STATIC_CHECK
  ├─ RUN_APPROVED_PYTHON_SNIPPET (optional, deferred — see §11)
  └─ REPORT
```

Reviewer still cannot: edit files, run Git mutations, install packages,
spawn other agents, invoke arbitrary shell commands, execute commands
outside the configured validation allowlist, change environment
configuration, or accept the feature.

Reviewer `READ` and `SEARCH` are not merely fallback diagnostics. They are
required independent exploration tools: Reviewer should follow the changed
behavior far enough through callers, tests, and error paths to support its
report, while staying inside packet-readable scope. See §7.1.

**Rollout note:** unlike v2, this capability's rollout is decoupled from the
Coordinator's — see Phase 1.5 in §24. It ships and is measured on the
current v1 architecture, independent of whether Coordinator work is ready.

## 10. Why Reviewer Execution Helps

A Reviewer that can independently run approved checks can verify claims
such as: a focused test still passes after the final Coder edit; an error
path actually behaves as expected; a suspected regression can be
reproduced; a static check finding is real; Coder handoff evidence is
stale or incomplete; an acceptance scenario needs one additional targeted
check. This reduces the need for Primary to reopen the repository merely
to answer simple questions like "does this exact path actually fail/pass?"

## 11. Reviewer Shell / Execution Policy

Do not expose a generic shell tool such as `RUN_SHELL("anything")`. Prefer
capability-based execution. Example trusted actions:

```json
{
  "action": "RUN_APPROVED_TEST",
  "test_id": "worker-heartbeat-focused"
}
```

or:

```json
{
  "action": "RUN_APPROVED_STATIC_CHECK",
  "check_id": "ruff"
}
```

The runtime maps ids to trusted commands from the packet/profile.

`RUN_APPROVED_PYTHON_SNIPPET` remains explicitly **out of scope for this
phase**. The difference between it and the two approved actions above is
categorical, not a matter of degree: `RUN_APPROVED_TEST` and
`RUN_APPROVED_STATIC_CHECK` execute from a closed set of commands
registered at packet time; a snippet is composed by the Reviewer model at
review time, which is fundamentally harder to sandbox correctly even with
no network access and no writes. Do not implement it until:

- `RUN_APPROVED_TEST` and `RUN_APPROVED_STATIC_CHECK` have shipped and been
  measured (Phase 1.5, §24), and
- the resulting metrics show a concrete, recurring class of question those
  two actions cannot answer.

## 12. Reviewer Result Model

Reviewer still returns `pass_to_primary`, `rework`, or `escalate`.

Each finding should distinguish:

- `reasoned_finding`
- `executed_finding`

This lets Primary trust executed evidence more heavily without trusting the
Reviewer model's prose.

For source-backed findings, Reviewer identifies current source evidence with a
structured `source_ref` rather than reproducing exact source text:

```json
{
  "path": "src/example.py",
  "start_line": 71,
  "end_line": 73
}
```

Reviewer is responsible for selecting the correct evidence range and
explaining why it supports the finding, contract review, ordering claim, or
other review obligation.

The deterministic runtime is responsible for:

- validating that the referenced path/range is currently readable;
- checking that the reference belongs to the current source revision;
- binding the reference to the current file hash;
- extracting the canonical current source quote;
- storing the verified source evidence in the immutable review/run record.

The model is not required to reproduce exact source text. Exact quote copying
is not treated as a Reviewer capability or semantic-quality metric.

If Reviewer cites unread, stale, out-of-range, or forbidden source, the runtime
rejects the report and returns only the bounded information needed to correct
the `source_ref`. It does not accept an unverified quote as evidence.

Executed findings must additionally identify the registered approved action
and its actual runtime result. A Reviewer statement that a test or static
check passed is not evidence unless the runtime executed and recorded that
registered action.

## 13. Reviewer Model Strategy

Do not hard-code one model assumption into the architecture. Candidate roles:

```text
Explorer:
  gpt-oss-20b

Coder:
  Qwen3-Coder-30B

Reviewer:
  Qwen3-Coder fresh context
  or Muse Glimmer 30B
  or another strong local coding/reasoning model

Coordinator:
  Muse Glimmer 30B
  or gpt-oss-20b
  or another model with strong plan-following/tool-routing behavior
```

Before a model enters semantic quality A/B evaluation for a role, it must pass
the current model × role protocol qualification defined in
`stability-plan-v1.2.md`.

Qualification and quality are separate:

```text
protocol compatibility
        ↓
semantic quality benchmark
        ↓
role candidate
```

A model that cannot reliably satisfy the role protocol should not consume real
feature benchmark runs merely to measure semantic quality.

Coordinator quality should be evaluated primarily on:

- following Primary's implementation plan;
- correct work-unit decomposition;
- correct worker routing;
- avoiding unnecessary Explorer calls;
- maintaining scope/risk/contract boundaries;
- knowing when to escalate;
- long-horizon execution stability.

Reviewer quality should be evaluated primarily on:

- semantic defect detection;
- test-gap detection;
- false-positive rework rate;
- false-negative rate;
- escalation quality;
- source-evidence grounding;
- approved-execution use when it materially improves verification;
- Primary work avoided.

As a directional signal only (not a substitute for Phase 4 A/B testing), model
benchmarks may be used to choose candidates. They are priors, not role
qualification or quality conclusions. The actual role protocol and completed
task benchmark remain authoritative for this system.

## 14. Shared Memory Ownership

```text
Primary:
  feature intent
  architecture
  authoritative contracts
  final review decisions

Coordinator:
  execution-state memory
  unit state
  worker routing
  rework state

Runtime:
  immutable evidence
  hashes
  validation
  run archives

Workers:
  no authoritative persistent memory
```

Suggested layout:

```text
.agent/
├─ feature-plan.json
├─ current-task.json
├─ units/
│  ├─ unit-001.json
│  ├─ unit-002.json
│  └─ ...
└─ tasks/
   └─ <task_id>/
      └─ runs/
         └─ <run_id>/
```

## 15. Memory Precedence

```text
1. Primary feature plan / latest Primary revision
2. Primary review feedback
3. actual current repository state
4. Coordinator execution memory
5. worker history
```

Historical attempts are context, not authority.

## 16. Coordinator Rework Loop

The Coordinator should absorb low-value orchestration loops:

```text
Coder
  ↓
deterministic gates
  ↓
Reviewer
  ↓
rework
  ↓
Coder
```

No Primary involvement is needed if: architecture is unchanged, scope
remains authorized, contract is unchanged, risk floor is unchanged, failure
is local/mechanical/semantic within the unit, and progress is still being
made.

**Closing an escalation-avoidance gap (NEW).** Once the Coordinator authors
packets itself, it can in principle retry a stuck unit by rephrasing the
packet each time, so the literal failure-signature streak never repeats and
escalation never triggers, even though the underlying problem hasn't moved.
To prevent this:

- Aggregate streaks by `unit_id` (or the `contract_id` / `required_behavior`
  it's anchored to), not by literal packet text or failure-signature string
  match.
- Add a hard cap on the number of distinct packet variants the Coordinator
  may generate for the same `unit_id`, independent of whether any
  individual failure signature repeats. Hitting the cap escalates, even if
  every attempt technically "failed differently."

**Infra failures are not rework-loop failures (NEW).** A context-window
overflow or a rejected upstream request (HTTP 4xx/5xx from a local model
server) is not evidence about the unit or the worker's competence; route it
to a separate `infra_failure` outcome (§19, §23) rather than counting it
toward the same-unit rework streak.

Reuse the existing failure-signature/no-progress/quality-gate streak
concepts otherwise. Do not use a simplistic global call limit. Coordinator
should escalate when repeated local loops stop converging.

## 17. Primary Review After Coordinator

Primary should receive a compact summary containing: feature status,
completed units, local rework count, resolved Reviewer findings, changed
paths, validation summary, open uncertainties, integration risk,
recommended Primary review level.

Primary should not need to read every Explorer transcript, every Coder
turn, every Reviewer turn, or repeated successful validation output, unless
an uncertainty/failure requires drill-down.

## 18. Primary Review Routing

Keep existing risk routing:

```text
Small:
  deterministic gates
  + Local Reviewer
  + Primary may accept from compact evidence

Medium:
  deterministic gates
  + Local Reviewer
  + Primary lightweight review

High:
  deterministic gates
  + Local Reviewer
  + Primary full review

High integration-risk feature:
  final Primary cumulative integration review
```

The Coordinator prepares the evidence package but does not replace
Primary's mandated review.

## 19. Deterministic Fast Path

Before invoking any reviewer model, continue using deterministic checks for
mechanical and infrastructure-level problems:

```text
syntax
format
lint
diff quality
focused pytest
JUnit evidence
changed-path attribution
post-validation mutation detection
hash consistency
context-window overflow
malformed/rejected upstream request (local model server 4xx/5xx)
```

Mechanical issues should not consume Primary review.

Context overflow and rejected upstream model requests are `infra_failure`
classes, not worker-quality failures. Catch them pre-flight where possible and
classify them separately from semantic failure.

For every local-model request, preflight should record at least:

- estimated prompt tokens;
- request byte size;
- configured context limit;
- safety margin;
- estimated contribution by logical prompt section;
- the three largest prompt sections.

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

All prompt sections that grow with run history must have bounded compaction
rules.

Typical policy:

```text
validation history:
  counters + recent relevant failures only

worker history:
  recent relevant outcomes only

source context:
  bounded ranges only

diff:
  changed / relevant hunks unless the role requires cumulative diff

task history:
  latest relevant state, not the full archive
```

Full evidence remains available in immutable archives by reference; prompt
compaction must not destroy or rewrite evidence.

If a request cannot fit safely inside:

```text
configured_context - safety_margin
```

return a labeled `input_too_large` infra outcome before dispatch rather than
sending an oversized request.

For actual LM Studio HTTP failures, capture enough provider diagnostics to
classify the failure: status code, response body, target model, estimated
tokens/bytes, configured context, and largest prompt sections.

See `stability-plan-v1.2.md` for the current request-size preflight and
infra-failure contract.

## 20. Evidence Caching

Preserve and extend the current evidence cache. Cache entries should
contain: path, hash/revision, captured range, purpose, producing
worker/run, timestamp, validity state.

Rules: unchanged file hash → evidence may be reused; changed file → related
evidence invalidates; unrelated evidence remains valid; cache hints are
navigation aids, not proof; final acceptance evidence should reference
current file versions.

## 21. Failure / Escalation Policy

Escalate immediately on: scope escape, unsafe edit, security violation,
forbidden dependency change, public contract conflict, architecture
conflict, unrecoverable runtime integrity failure.

Escalate after bounded local attempts on: repeated identical failure,
repeated no-progress, repeated reviewer/coder disagreement, repeated
quality-gate failure, inability to produce required evidence.

`infra_failure` events (§16, §19) are tracked and, if they recur for the
same underlying cause, escalate on their own bounded threshold — they
should not silently retry forever, but they also should not be folded into
the same counter as a semantic worker failure.

Do not escalate merely because a feature has many legitimate work units.

## 22. Expected Efficiency Improvement

The main expected savings come from removing these tasks from Primary:
deciding whether each unit needs Explorer, creating every detailed Coder
packet, routing every local rework, reading every Coder handoff, manually
deciding every Reviewer invocation, resolving mechanical validation
failures, repeatedly reading already-valid evidence.

**This assumes the local specialists converge on their own most of the
time.** That assumption is unverified as of this writing — see
`stability-plan-v1.2.md` for the baseline this needs before the savings
estimate below means anything. Adding a Coordinator on top of a low local
convergence rate does not produce these savings; it adds another layer of
local retries before the same escalation Primary would have handled
directly under v1, at higher local compute cost.

Primary should ideally operate in this pattern:

```text
PLAN ONCE
  ↓
LOCAL EXECUTION
  ↓
EXCEPTION? → Primary
  ↓
FINAL / HIGH-VALUE REVIEW
```

instead of:

```text
PLAN
→ orchestrate unit
→ review
→ orchestrate next unit
→ review
→ local rework
→ review
→ ...
```

## 23. Metrics for v2.1

Track at least:

```text
feature_id
unit_count
explorer_calls
coder_calls
reviewer_calls
local_rework_count
coordinator_escalations
primary_review_level
primary_rework_count
primary_takeover

reviewer_false_positive
reviewer_false_negative
reviewer_findings_confirmed
reviewer_findings_rejected
source_ref_convergence_rate
invalid_source_ref_count

primary_files_opened
primary_full_diff_read
primary_selected_hunks_read

local_model_tokens
wall_clock_time

policy_violation_blocked_count
repair_focus_to_edit_conversion_rate
repair_focus_to_successful_validation_rate
repair_supervision_nudge_issued
fresh_repair_context_used

infra_failure_count
input_too_large_count
prompt_estimated_tokens
largest_prompt_sections

role_compat_pass_rate
role_compat_failure_reason
```

Do not duplicate every Stability diagnostic into v2.1 metrics. Keep the values
that are useful for Coordinator efficiency, model-role selection, escalation
analysis, and Primary-work reduction.

Important outcome metrics:

```text
Primary work avoided
first-review acceptance rate
local recovery rate
Primary takeover rate
Reviewer unnecessary-rework rate
Coordinator escalation rate
source-evidence convergence
role-qualified model success rate
```

## 24. Recommended Implementation Order

Terminology clarification (2026-09-28): offline Phase 1 implementation is
already permitted. The **live implementation-entry gate** is permission to
start Phase 2, not proof that Phase 2 is implemented. It still requires the
frozen v1.2 exit evidence; neither a targeted repeat nor successful Coder and
Reviewer units can replace the independent Explorer result. Track Phase 1
persistence and Phase 1.5 execution separately. See
`stability-research-2026-09-28.md` for the external-project comparison and the
bounded protocol/diagnostic changes selected from it. No acceptance threshold
is changed by that research.

### Phase 0 — Stability baseline (gate; see `stability-plan-v1.2.md`)

Complete `stability-plan-v1.2.md`.

This includes:

- Coder repair convergence;
- structured repair-focus handling;
- fresh compact repair-context evaluation;
- runtime-materialized Reviewer source evidence;
- request-size preflight and section-level diagnostics;
- infra-failure classification;
- shared bounded exploration;
- model × role compatibility qualification;
- representative-unit baseline measurement.

**Phase 2 does not start until the v1.2 exit criteria are satisfied.**

The separately preregistered §12.9 `localization-v1` assessment can instead
authorize implementation of a **localization-only** Phase 2 slice. It does not
authorize general semantic-investigation routing or deployment. Such a slice
must bind an explicit exploration capability to each dispatch, mechanically
reject unsupported kinds, and send behavior diagnosis/ambiguity to Primary.
The full investigation gate remains independent and cannot be inferred from
runtime-materialized source quotes. The scope restriction is a deliberate
architecture change to avoid making a small local locator impersonate a full
implementation verifier; it must be visible in reports and configuration.

The frozen `localization-v1` implementation-entry gate is GO (2026-09-28;
see `benchmarks/V1.2-LOCALIZATION-CANDIDATE.md`). Phase 2 may implement only
the explicit locator capability, with Primary escalation for semantic
questions. The Coordinator is not yet live. Two protocol-passing runs needed
Primary rework for a duplicate unreachable raise that Reviewer missed; keep
this finding in the first Phase 2 review and validation work. General semantic
routing remains NO-GO.

The shared bounded-exploration matrix in §7.1 belongs to current-v1
hardening work and is implemented/measured here; it is not deferred until
Coordinator routing.

### Phase 1 — Coordinator contract (may run in parallel with Phase 0)

Add `feature-plan.json`, `coordinator-state.json` / current-task extensions,
unit packet generation, explicit Coordinator outcomes, and the Deterministic
Guardrail Layer (§6a) as a schema/contract exercise.

Initial offline slice: `.local-agents/coordinator-contract.py` validates the
Primary feature-plan example's contract registry, unique ownership, dependency
graph, and risk-floor clamp. Its candidate-packet check also binds feature,
unit, dependencies, exact behavior text, acceptance scenarios, ordering,
protected focused tests, validation profile, and Primary risk to the plan.
Primary-owned per-unit scope ceilings bound every proposed read, modify, and
create path. It calls Coder's existing schema-v2 validator on a copy. The
offline archive check revalidates the packet, matches actual changed paths to
the scope ceiling, and binds accepted records to the Primary plan revision and
content fingerprint. The closed decision enum and required reason-code shape
are checked offline. Dependency progression uses matching Primary, Coder, and
Reviewer acceptance archives. `FEATURE_READY` additionally requires a passing
integration archive that covers accepted changed paths and still matches the
current file hashes. The library does not yet write these archives, generate
packets, inspect import changes, persist Coordinator state, or dispatch
workers. It does not accept the feature. Phase 1 still needs those runtime
connections and end-to-end fixtures before live routing.

An additional offline state contract now initializes plan-fingerprint-bound
Coordinator execution memory, checks exact unit identities and bounded event
sequences, and applies decisions only through archive-backed transition
validation with an expected state sequence. It deliberately has no
`accepted_units` authority field: Primary review archives remain the source
of acceptance. Trusted guardrail blocks increment a separate policy counter;
infra failures are not folded into it. This is a pure state transition API,
not a live Coordinator route. A later scoped implementation added a
fail-closed atomic state writer with an exclusive lock and expected-sequence
check, plus a `localization_only` evidence gate. The gate binds
current full Explorer source references to a Primary-authorized schema-v2
packet and rejects semantic capability requests. Coder's diff gate also
rejects newly introduced adjacent duplicate `raise` statements. These are
now connected to a restricted one-unit Coder→Reviewer handoff; cumulative-diff
paths are checked against authorized runtime edits before Reviewer. This is
not autonomous Coordinator routing. Newly added static imports of local
modules are also checked against packet read scope; dynamic imports remain
outside this guarantee. Deterministic process-loss, double-dispatch,
multi-file, and out-of-scope fixtures pass. Model-backed operation of the
new route now passes two targeted frozen runs, including one where Explorer
was not given the implementation path. This is not a repeated statistical
baseline. An immutable dispatch record and read-only restart inspector now
reconcile state with canonical Coder/Reviewer archives; they never auto-retry
or accept. A completed failed Coder run now permits an explicit
Primary-authorized, hash/sequence-bound transition to a fresh non-expanding
rework packet. A Primary-plan-derived bounded packet materializer is now
available, but the route still requires Primary to select a proposal and does
not launch Explorer. Incomplete/uncertain process loss and autonomous rework
remain outstanding. Subsequent frozen route checks passed mapping with and
without implementation-path hints, but the multi-file `sample-identity` case
passed with known paths and failed in two unknown-path attempts despite valid
Explorer evidence. Coder made incorrect semantic edits and Reviewer correctly
did not launch. Primary-authorized rework of one completed-failed snapshot
converted semantic tests on a2 and passed the full Coder→Reviewer route on
a3 after a narrower quality-only packet. The rework also exposed and fixed
a submitted-versus-archived packet hash mismatch. Initial unknown-path
conversion remains 0/2 for this multi-file case; the final rework outcome
must be reported separately. This is a measured implementation-gate gap, not
a transport failure; see `docs/v2.1-localization-slice.md`.

A five-type, same-question-version pilot of the implemented route then measured
Explorer 5/5, first-call Coder 4/5, Reviewer 4/4 reached, and independent
first-pass E2E 4/5 with no explicit infrastructure failures. The recurring
multi-file `sample-identity` semantic failure keeps unattended routing NO-GO;
these five cells are not a substitute for the 11+ type/two-round gate. See
`benchmarks/LOCALIZATION-ROUTE-PILOT-V2.md`.

One targeted two-snapshot comparison then split the recurring failed
`sample-identity` packet into dependent fingerprint and reuse-key units with
separate writable files, protected focused tests, manual Primary review between
units, and the original cross-function integration test afterward. All four
split Coder→Reviewer units passed on the first call, both integrations passed,
and both archive-backed `FEATURE_READY` eligibility checks passed. This
supports cohesive-unit decomposition as the next implementation direction;
it does not erase the unsplit first-call failures or establish the full
two-round/multi-case release gate. See
`benchmarks/SAMPLE-IDENTITY-SPLIT-COMPARISON.md`.

Do not deploy the restricted route for unattended live units yet. Its current
command is an opt-in Primary-supervised implementation slice.

Coordinator schema/protocol fixtures may also consume the model-role
qualification format from Stability, but Coordinator live behavior is not
enabled in this phase.

### Phase 1.5 — Reviewer execution capability (independent track begun during Phase 0)

Add:

```text
RUN_APPROVED_TEST
RUN_APPROVED_STATIC_CHECK
```

to Reviewer on the current v1 architecture, without waiting for Coordinator
routing.

This is a smaller, independently reversible change whose value can be measured
directly:

```text
Does Reviewer approved execution reduce how often Primary must reopen the
repository merely to answer a pass/fail verification question?
```

Do not add `RUN_APPROVED_PYTHON_SNIPPET` (§11).

At the same time:

- make the §7.1 capability matrix explicit in schemas and diagnostics;
- require evidence that Coder and Reviewer can perform bounded role-local
  discovery without recursive worker calls;
- require Reviewer execution to use only registered action ids;
- preserve Explorer success/failure as an independent metric;
- use the canonical `source_ref` evidence protocol established by
  `stability-plan-v1.2.md`;
- do not reintroduce model-authored exact source quotes as a hard protocol
  requirement.

### Phase 2 — Coordinator routing (gated on Phase 0 exit criteria)

Enable live Coordinator routing.

Coordinator may:

- decide Explorer / no Explorer;
- generate bounded Coder packets;
- dispatch Coder;
- dispatch Reviewer;
- manage local rework;
- continue to the next unit;
- escalate to Primary.

Every Coordinator-generated packet and decision remains subject to the
Deterministic Guardrail Layer (§6a).

Low-level Coder runtime repair strategy remains runtime-owned. Coordinator
does not decide whether a Coder should use fresh repair context, request
compaction, validation retry mechanics, or other execution-safety internals.

### Phase 3 — Compact Primary handoff

Primary receives only the information required for its current review level:

- feature status;
- completed units;
- changed paths;
- validation summary;
- resolved / unresolved Reviewer findings;
- escalation reason if any;
- integration risk;
- recommended Primary review level.

Primary should drill into immutable archives only when uncertainty, failure,
policy signal, or risk level requires it.

### Phase 4 — Model evaluation

Only models that pass the current role-compatibility qualification may enter
semantic quality A/B evaluation for that role.

Candidate comparisons may include:

```text
Coordinator:
  gpt-oss
  vs Muse Glimmer
  vs other role-qualified candidates

Reviewer:
  Qwen fresh-context
  vs Muse Glimmer
  vs gpt-oss
  vs other role-qualified candidates
```

Use the same completed tasks / patches.

Evaluate protocol compatibility separately from semantic role quality.

Phase 1.5 execution-capability data should already exist for Reviewer
candidates by this point.

### Phase 5 — Efficiency benchmark

Compare:

```text
patched current architecture
vs
Coordinator architecture
```

against the Phase 0 v1.2 baseline, not against an assumed savings number.

Measure:

- Primary work avoided;
- Primary review depth;
- Primary files/hunks opened;
- local model usage;
- local rework;
- escalation/takeover;
- wall-clock time;
- acceptance quality.

Do not judge efficiency only from local token count.

## 25. Non-Goals

Do not turn Coordinator into another Primary. Do not give Reviewer
unrestricted shell. Do not make local agents responsible for final
acceptance. Do not add generic multi-language/provider support yet. Do not
add parallel multi-coder execution yet. Do not add vector memory unless
evidence shows task memory is insufficient. Do not add UI before the
orchestration behavior is stable. **Do not treat introducing a Coordinator
as a fix for existing Coder/Reviewer convergence problems** — those are
addressed in `stability-plan-v1.2.md` regardless of whether Coordinator
ships.

## 26. Desired Final v2.1 Shape

```text
                   Primary GPT
          architecture / implementation plan
                    │
                    ▼
              Local Coordinator
      execution decomposition / orchestration
                    │
                    ▼
        Deterministic Guardrail Layer (§6a)
                    │
          │          │           │
          ▼          ▼           ▼
      Explorer     Coder      Reviewer
      gpt-oss      Qwen       local model
          │          │           │
          └──── deterministic runtime ────┘
                     │
                     ▼
                Coordinator
                     │
          ┌──────────┴──────────┐
          │                     │
      local continue        escalate
          │                     │
          ▼                     ▼
      next unit            Primary GPT
          │
          └──────────────┐
                         ▼
                    FEATURE_READY
                         │
                         ▼
                    Primary review
```

The guiding principle is unchanged, with one addition:

> Primary decides what the system should become.
> Coordinator manages how the already-approved plan gets executed.
> Specialists perform bounded work.
> The runtime proves what actually happened.
> The Deterministic Guardrail Layer proves the Coordinator stayed inside
> the lines Primary drew — so that claim doesn't rest on the Coordinator's
> own word for it.
