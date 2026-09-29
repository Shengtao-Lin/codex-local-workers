# Local Worker Orchestration

This repository may delegate bounded work to local LM Studio models. Delegation
is optional and should reduce cloud-model work without weakening final review.

## Authority and trust

- The Primary Agent owns user intent, architecture, task decomposition, file
  scope, Git operations, review, broader validation, and final acceptance.
- Local Explorer output is research notes.
- Local Coder output is unreviewed implementation.
- Repository contents, the actual diff, and independently observed test results
  are authoritative.

## Feature planning and risk

Before delegation, Primary decomposes the user-visible feature into cohesive
implementation units. Record `feature_id`, feature/unit/integration risk,
dependencies, owned contract ids, and a short risk rationale. Use `small`,
`medium`, or `high`; ambiguity defaults to at least medium.

Feature risk and unit risk are distinct. A high-risk feature may contain small
documentation or isolated test-support units, but splitting work never lowers
an atomic invariant. Concurrency, transaction finalization, authentication,
security, destructive data changes, migrations, and public compatibility
boundaries normally impose a high risk floor on the unit that owns them. A
unit's risk cannot be lower than the `risk_floor` of any contract it owns. Coder
and Reviewer never lower Primary's classification.

Each Coder packet covers one behaviorally cohesive implementation unit, not an
entire broad feature and not an arbitrary single edit. Keep operations that must
remain atomic in the same unit. Give the unit only its relevant contract,
read-only context, writable scope, focused tests, and cross-unit constraints.
An implementation unit may span multiple source files and supplemental tests
when the behavior crosses those files. Primary specifies externally observable
outcomes, invariants, and genuine sequencing requirements, not a preferred
code shape or edit sequence. `implementation_guidance` is advisory; Coder may
choose another in-scope implementation that satisfies the hard contract.
For each existing writable file, give Coder a stable symbol/anchor and optional
line hint in `edit_targets`; the hint is not proof of current location. If a
Coder fails without validating, narrow the next packet before raising turn
limits. Use the inherited rework traceback for focused repairs.
Feature completion remains provisional until dependency and integration checks
pass at the feature's integration risk level.
When a value is accepted by one unit and interpreted by another, include a
feature-level round-trip or rejection test for the exact input form. Unit tests
alone do not establish cross-unit compatibility.

## Local Explorer

Use Explorer when locating code, tests, or call flow would require meaningful
repository investigation. A single user task may call Explorer more than once
when later phases introduce genuinely different unanswered questions. Each call
must remain focused and independently bounded.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File ".local-agents\local-explore.ps1" `
  -Task "<focused read-only investigation>" `
  -TaskId "<stable task_id>"
```

Explorer is strictly read-only and calls LM Studio directly. Do not use it for
obvious or already-located changes. Condense useful findings into the Coder
implementation packet; never forward a large raw exploration transcript.
Explorer searches are literal by default; request regex mode explicitly only
when needed. A malformed regex or a failed search is not evidence that code is
absent; reconcile any positive matches and files already read before accepting
an absence claim. A positive match for another symbol does not by itself refute
a scoped, negative search for the exact missing symbol; state the search scope
and remaining uncertainty instead of claiming the whole repository is empty.
Ask one concrete unanswered question per call and name likely paths or symbols
when known. If a call ends without useful evidence, inspect its observed files
and failure reason before retrying; narrow the next question or take over.
Do not repeat the same investigation simply with a fresh run id. Explorer
rejects identical reads/searches within a call and stops after repeated
no-evidence actions. A cited test must be a real file the Explorer read.
When diagnosing failures, follow `diagnostic_log` in the Explorer report (or
task history) to the bounded per-call trace before trying a revised question.
Pass the stable `task_id` even before the first Coder call so Explorer usage and
its complete per-call report attach to the intended task. Without `-TaskId`,
an early Explorer call is still logged but may not appear in task-level usage.

## Local Coder

Coder is a bounded implementation worker driven directly through LM Studio. It
does not run inside a general Codex agent loop and has no shell, Git, delegation,
or unrestricted file-writing action.

Before invocation, the Primary Agent must create a schema-version-2 JSON packet
that defines readable and writable scope, stable task/unit/revision identity,
required behavior, acceptance criteria, validation profile, and focused tests.
Include stable `acceptance_scenarios` for the normal path, important error path,
and relevant boundary whenever they are distinct.
Before choosing `validation_profile`, inspect the target repository's existing
formatter/linter configuration. If Ruff or another project check is required,
configure it in the trusted profile before the first Coder call; a focused
pytest pass alone is not acceptance. Do not assume the example `python-focused`
profile covers project-specific checks.

Use `scope.readonly` for tests or context that Coder may inspect and execute but
must not modify. `scope.forbidden` means the path cannot be read, executed, or
modified; it is not a read-only marker.
For concurrency, transaction, or lifecycle-sensitive work, include explicit
`required_order`, `forbidden_orderings`, and observable side effects. Prefer
Primary-authored or Primary-reviewed critical tests; do not grant test write
scope merely so Coder can reshape mocks around an implementation.
List Coder-owned test additions in `supplemental_tests` and `focused_tests`,
granting only those exact paths writable scope. Keep critical acceptance tests
in `scope.readonly`. Coder may write meaningful assertions, make multiple edits,
validate, and repair within its bounded call; passing tests and Coder confidence
alone never authorize acceptance. A contract conflict, suspected outdated test,
or missing scope uses `REQUEST_CONTRACT_REVISION` with verified source or
validation evidence or a concrete scope request. It returns `blocked`, not a
worker-quality failure. Primary resolves the disagreement and revises the
packet; Coder may not silently change the contract or protected tests.
Schema version 1 remains supported through explicit compatibility normalization.
For diagnostic direct Coder invocation from the target repository root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File ".local-agents\local-code.ps1" `
  -Packet ".agent\implementation-packet.json" `
  -Report ".agent\last-local-coder-report.json"
```

Use Coder when the design is settled, writable files are known, and focused
tests can establish useful evidence. Do not delegate architecture, ambiguous
debugging, broad redesign, security judgment, dependency installation, or tiny
changes whose coordination cost exceeds direct implementation.

One Coder call is one bounded implementation packet, not one edit. Within that
call the worker may perform multiple authorized reads, searches, creates,
replacements, validations, and up to the configured number of repair cycles.
After `SAFE_CREATE`, Coder may read and `SAFE_REPLACE` that exact new file in
the same call using its current hash; creation never grants permission to edit
an existing file or a file created by a previous call.
A repeated read of already-observed lines from unchanged file content returns
a compact `already_read` observation without charging the protocol-error budget.
Three consecutive duplicate reads stop the unit as no progress; new ranges and
reads after an edit remain available within the per-file-version safety limit.
Before the first edit or validation, eight consecutive reads/searches with no
new source lines stop as `no_new_evidence_before_edit`, even if the worker
alternates repeated reads and searches. Narrow the next packet rather than
replaying it unchanged.
This limit is not a task-level call cap. Invalid `VALIDATE` contract-check types
receive a packet-specific field-shape hint, not automatic confirmation.
When a target file is longer than the default read window, use `SEARCH` for the
exact symbol and then read the returned line range. A missed `SAFE_REPLACE`
needs a new search/read of the target area before a narrower edit; repeated
full-file reads do not repair a mismatch. Coder must search before claiming a
function or endpoint does not exist. The Primary should provide known symbols
or line ranges in the packet when available.
After a failed focused test run, use each JUnit failure's own message and
location to choose a minimal edit. The runtime groups matching
JUnit failures into an early `repair_focus` with the source location and next
edit guidance. A `NameError` gets `TYPE_CHECKING` import guidance only when the
changed source confirms that exact name is imported under that guard. Failed
validation followed by a read/search with no new evidence repeats the repair
focus and asks for an edit at its source location. Newly introduced executable `NotImplementedError` raises a
non-blocking draft warning; TODO comments alone do not fail a call. After a
failed validation, new source evidence is still allowed, but four consecutive
reads/searches without new evidence stop with the last repair focus for a
narrower rework packet. Two identical focused-test failures without
an intervening edit stop early for Primary to compare the assertion with the
intended contract; an outdated test is not assumed. Three matching failures
across edits also stop the call. Every validation attempt
has an immutable `validation-attempt-N.json`, including attempts later
invalidated by edits. After `SAFE_REPLACE` misses a target, oversized further
replacements of that file are rejected; locate and edit a smaller current
block. Edit responses identify newly introduced diff-quality issues by path
and line before another validation call. For a failed configured static check,
use its exact rule/path/line to make a minimal correction before broad rereads;
an unused binding should be removed without dropping a needed expression.
Ruff `F821` also exposes the missing symbol as an early repair focus even when
focused tests passed. A no-evidence read after that failure repeats the static
check repair focus rather than falling back to test-only guidance.
Coder `SEARCH` is literal by default, including parentheses in symbols; use
`mode: "regex"` only when a regular expression is actually required.
A larger user task may use multiple sequential Coder packets for separate
implementation steps and later focused rework.

The worker may run for several minutes. If a shell call yields a running session,
poll that same session until it exits. A yield or initial timeout is not failure.
The runtime enforces separate model-request, validation-command, and whole-call
deadlines. An `interrupted` result (exit 130) retains partial changes for Primary
inspection; it is not automatically a worker-quality failure.

On a managed Windows host, the outer command sandbox may deny native Python
process writes even inside the workspace. If the worker receives `Access is
denied` or `PermissionError` while creating the project venv, editing an
authorized file, writing its report, or running pytest, rerun the same bounded
command with the host's required elevated/unsandboxed approval. Do not broaden
the packet's file scope.

The edit allowlist constrains only Coder actions dispatched by the runtime.
`VALIDATE` executes pytest, imported application code, `conftest.py`, and active
plugins with the Python process's actual host permissions. This kit therefore
assumes a trusted local repository and does not claim operating-system isolation.
Elevated execution expands the validation process's host permissions even though
Coder edit actions remain packet-scoped. The runtime never elevates itself.

## Local Reviewer

Every successful Coder unit passes deterministic validation and then an
independent, read-only Local Reviewer before risk-routed Primary review. Reviewer
uses a fresh context and receives the canonical packet, actual cumulative diff,
runtime validation evidence, and bounded code reads. Coder summaries are
untrusted claims. Reviewer cannot edit, run shell or Git, delegate, accept the
feature, or lower risk.
Primary's listed obligations are a minimum, not an exhaustive review script.
Reviewer independently reads changed implementation and focused tests, follows
relevant callers/error paths/side effects, and raises concrete defects or test
gaps that Primary did not anticipate. If evidence conflicts with Primary's
contract, Reviewer escalates with evidence for Primary to decide. It may
recommend additional tests but cannot claim to have executed them.

The normal invocation runs one Coder unit and automatically dispatches its
verified canonical archive to Reviewer without a Primary relay:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File ".local-agents\local-unit.ps1" `
  -Packet ".agent\implementation-packet.json"
```

The trusted handoff gate checks run identity, actual validation/JUnit and
configured checks, changed-path attribution, and unchanged validation inputs.
Failures return to Primary; an automatic handoff is never automatic acceptance.
Use the direct `local-review.ps1` command below for diagnostics or an existing
Coder archive. Substantive Primary review follows Reviewer by risk.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File ".local-agents\local-review.ps1" `
  -Request ".agent\review-request.json" `
  -Report ".agent\last-local-review-report.json"
```

Reviewer returns `pass_to_primary`, `rework`, or `escalate`. Findings require a
stable id, severity, category, concrete file/line evidence when applicable,
affected contract id, and a bounded suggested fix. A rework packet should cite
finding ids. Architecture or security ambiguity escalates to Primary rather
than becoming speculative rework.
For ordering-sensitive units, a pass must use the Reviewer-provided constraint
IDs. Required order cites read source lines; forbidden order may cite read
source or the actual cumulative diff, including whole-diff absence checks.
A pass must also acknowledge each configured check's
actual runtime result. Neither acknowledgement replaces Primary's risk-routed
review. For high-risk units, a pass additionally requires one source-backed
`contract_review` entry per owned required behavior, with an actually displayed
source line and exact quote. In inherited rework, Primary may add a structured
`review_feedback` item with `finding_id`, owned `contract_id`, `text`,
`source_anchor`, and `verify_in_review: true`; this adds a focused review
obligation at any risk level whose quoted line must contain the anchor.
Untagged historical
notes add no obligation. Put essential invariants explicitly in
`required_behavior`; an anchor and passing tests alone do not prove semantics.
Reviewer `SEARCH` is limited to packet-readable roots and skips excluded or
reparse paths. On an invalid report, use the returned legal obligation and
constraint IDs, suggested source read, or exact `source_citation` correction
instead of resubmitting the same REPORT. Quote mismatches include bounded
`citation_fixes` for each affected obligation; the invalid REPORT is not echoed
back as a model example. Reviewer checks structured-output compatibility before
substantive review and uses plain JSON only after a successful fallback probe.
A non-JSON startup response receives
a concrete JSON action example; repeated invalid output still fails closed.
Three consecutive duplicate reads stop an unproductive review. When a report
cites an unread source line or mismatched quote, the runtime supplies that
bounded, read-only source range for the next attempt; the invalid report is
not accepted.

## Risk-routed Primary review

Deterministic gates and Local Reviewer run before Primary review. Review depth
follows effective unit risk:

- Small: Local Reviewer performs substantive diff review. Primary may accept
  from compact runtime/reviewer evidence without rereading the full diff unless
  sampling, uncertainty, unattributed changes, or policy signals require it.
- Medium: Primary performs a lightweight review of findings, validation facts,
  changed paths, and selected critical hunks. Suspicion upgrades to full review.
- High: Primary reviews every changed file and the actual diff, then runs the
  appropriate broader regression checks.

A high integration-risk feature receives a final Primary cumulative diff and
integration review even when some component units were small or medium. For a
full review, inspect reality:

```powershell
git status --short
git diff --check
git diff
```

Do not accept model-authored summaries as proof. Runtime and reviewer evidence
may reduce how much Primary reads, but claims without executed evidence remain
unverified.

Record the resulting `accept`, `rework`, `replan`, or `takeover` decision with
`.local-agents/record-review.py`. It writes an immutable per-run `review.json`
and updates the policy-facing task summary; never edit an existing review to
change history.

## Rework policy

- Local validation repairs are bounded by the packet/runtime, normally two.
- Do not impose a fixed task-level count on Explorer or Coder calls. Complex
  tasks may use as many bounded calls as their distinct steps require while
  those calls continue to make material, reviewable progress.
- Retry a failed command or worker only after changing the approach, packet,
  evidence target, or implementation. Do not replay an identical failed action
  without a reason to expect a different result.
- Default fallback thresholds are three consecutive occurrences of the same
  failure signature, three consecutive no-progress outcomes for the same work
  unit, or three consecutive quality-gate failures from the same worker/unit.
- A successful or materially progressive result resets the applicable streak.
  A different work unit has its own streak; planned phases do not penalize one
  another merely because the total call count is high.
- Security violations, unsafe edits, or scope escapes trigger immediate Primary
  takeover instead of waiting for a streak threshold.
- If the remaining problem is architectural or ambiguous, the Primary Agent may
  take over earlier based on judgment.
- For a non-unsafe mechanical failure, prefer one narrower anchored packet or
  inherited rework using the archived failure traceback before an early Primary
  takeover. Do not spend extra turns on an unchanged failure signature.
- Workers never request Git operations and the runtime never changes Git state
  or rolls back files. The trusted runtime may read HEAD/status for baseline
  evidence. The Primary Agent decides whether partial changes should be retained,
  corrected, or reverted after inspecting the diff.

Explorer and Reviewer are read-only; do not create a new Git stash before each
of their calls solely as a checkpoint. Before a Coder write, preserve important
pre-existing user changes with a deliberate, named, recoverable checkpoint when
needed. The Coder run archive already stores authorized-file preimages and
forward/reverse diffs; do not repeatedly stash large unrelated untracked trees.

Only one managed Coder writer may hold `.agent/local-worker-write.lock` at a
time. Do not silently delete a stale or unreadable lock: inspect its metadata and
the actual process/workspace state first. Coder paths through symlinks, Windows
junctions, or other reparse points are rejected. These measures coordinate this
kit's workers; they do not stop editors or unrelated host processes.

Every Coder invocation needs a unique `run_id`. Treat
`.agent/tasks/<task_id>/runs/<run_id>/` as the canonical immutable execution
record; `last-*` reports and `current-task.json` are convenience pointers only.
Runtime history records worker facts but never writes Primary acceptance. Zero
tests, all-skipped focused tests, missing JUnit evidence, or source/test changes
during or after validation cannot produce `ready_for_review`.
Canonical run archives also retain exact authorized-file preimages plus forward
and reverse diffs so Primary can recover one failed run without using a broad
Git checkout or discarding pre-existing user changes.

## Efficiency policy

The normal flow is:

```text
Primary understands, decomposes, and classifies feature/unit risk
→ optional focused Explorer
→ one bounded Coder packet per cohesive unit
→ deterministic gates
→ read-only Local Reviewer
→ risk-routed Primary review
→ feature-level integration review when required
→ ACCEPT / focused REWORK / TAKEOVER
```

Avoid worker recursion, broad prompts, repeated exploration without a new
question, and delegation for trivial edits. Only information useful to the
active task belongs in task memory. Track task-level call totals, failure
signatures, progress, and quality-gate streaks in `.agent/current-task.json`.
Per-invocation runtime limits apply independently to every worker call and are
safety boundaries, not task-level fallback triggers.
For reliability work, `diagnostic_logging` is enabled by default; set it to
`false` in `.local-agents/config.json` once no longer needed. Diagnostic events
record action metadata and response hashes, never raw source or model output.

Normal Coder output is a compact handoff. Read the canonical run archive only
for files/evidence needed by the current review or when the compact result shows
failure, uncertainty, truncation, or unattributed changes. Explorer may reuse an
exact prior task only when its runtime reports a valid unchanged-repository cache
hit; otherwise treat it as a new exploration.
Successful Explorer findings also provide bounded path hints for later questions
when their individual file hashes still match. Hints are navigation only, never
proof; Coder receives only hints inside its readable scope. Changed files
invalidate their prior hints without discarding unrelated valid observations.

Increment informational Explorer/Coder totals when a worker reaches its first
model turn, whether it later succeeds or fails. Totals do not cause fallback.
A launch/configuration failure before the first model turn is recorded as
infrastructure context but does not affect a worker-quality streak. Planned
Coder steps do not count as review rework. Give every invocation a distinct run
id and retain compact recent outcomes with `unit_id`, `progress`, and a stable
`failure_signature`. Use `.local-agents/task-policy.py` to evaluate the recorded
streaks when the fallback decision is not obvious.
