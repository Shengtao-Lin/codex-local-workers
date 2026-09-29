# Local worker protocol

## Coder packet schema v2

Each Coder invocation receives one final packet. Primary feedback must be merged
into a new packet revision rather than supplied as a conflicting side channel.

Required identity fields:

- `schema_version`: `2`
- `task_id`: stable top-level user task
- `feature_id`: stable user-visible feature
- `unit_id`: stable logical work unit across retries
- `run_id`: unique invocation identity
- `attempt`: invocation number for the unit
- `plan_revision`: Primary plan version
- `packet_revision`: current execution instruction version

Scope fields:

- `scope.read`: readable files or directory roots
- `scope.readonly`: explicit readable/executable paths that cannot be modified
- `scope.modify`: existing files the Coder may change
- `scope.create`: new files the Coder may create
- `scope.forbidden`: paths excluded from reading and writing

New packets should include one `edit_targets` item per existing file in
`scope.modify`, with its path, a stable symbol/anchor, and an optional one-based
`line_hint`. The hint is navigation context, not an authorization boundary and
may drift after edits. `require_edit_targets` in trusted config enforces packet
coverage; older configs can leave it off for compatibility.
Strict preflight also verifies that each anchor occurs in its current file;
`line_hint` remains advisory because line numbers drift.
One unit may include multiple source files plus Coder-owned test files when they
form a cohesive behavior. `implementation_guidance` is optional, advisory
navigation/design context; unlike `required_behavior`, acceptance scenarios,
ordering constraints, and read-only tests, it is not an acceptance gate.
Primary describes outcomes and cross-file invariants, not a sequence of text
replacements. `supplemental_tests` lists test files Coder may write; each must
be in `scope.modify/create` and `focused_tests`. Critical Primary-owned tests
remain in `scope.readonly`.

`.agent`, `.local-agents`, and `AGENTS.md` are reserved control paths and are
never writable by Coder, even if a packet lists them.

`required_behavior` and `acceptance_criteria` are arrays of stable `id`/`text`
objects. `validation_profile` selects a trusted profile from `config.json`;
workers cannot submit arbitrary shell strings.
`risk` records independent `feature`, `unit`, and `integration` levels. Primary
assigns each level as `small`, `medium`, or `high`. `owned_contract_ids` maps the
unit to its relevant requirements; optional contract `risk_floor` values prevent
the unit risk from being lower than a critical invariant. `dependencies` names
other implementation units required before integration.
`acceptance_scenarios` names the normal, important failure, and boundary cases
Primary expects to review. Older packets without it receive compatibility
scenarios derived from their acceptance criteria.
Scenarios may include a JSON `observables` object for required side effects.
Concurrency- or transaction-sensitive packets should also include
`required_order` and `forbidden_orderings`. Such packets require a structured
`contract_check` in the `VALIDATE` action; this focuses the repair loop but is
self-reported evidence, not proof that the implementation is correct.
Coder can edit and validate repeatedly within bounded turn/repair limits.
`REQUEST_CONTRACT_REVISION` returns a blocked report for Primary judgment when
the contract appears inconsistent with observed code or validation, a test
seems outdated, or scope is insufficient. Contract conflicts cite known
contract IDs and source lines actually read from the current file or immutable
validation attempts. Suspected outdated tests require a validation attempt;
scope/context gaps require a concrete `requested_scope`. This route does not
count as a Coder quality failure and never changes the packet automatically.
One narrower range of at most `max_cached_replay_lines` (default 40) may be
replayed from a previously broad read once per file version to restore local
context. Subsequent covered `READ_FILE` ranges return compact `already_read`
feedback without spending the protocol-error budget; a configured consecutive
streak ends the run as no progress. Invalid `VALIDATE` contract-check types receive
the packet's required field shape, but the worker must verify before asserting
any boolean check. A first omission of observable scenario ids receives a
one-shot, packet-specific shape correction without running validation or
consuming the protocol-error budget; repeating it does consume the budget.
`READ_FILE` returns at most 200 lines by default and now includes an unread
line range and symbol-search hint when more lines remain. After a
`SAFE_REPLACE` target mismatch, Coder receives a bounded SEARCH suggestion and
up to three closest current source lines with line numbers when a close match
exists, then instructions to retry a smaller exact edit. This does not bypass
the current-hash check or authorize an automatic edit.
For one-line fixes, `SAFE_REPLACE_LINE` accepts an authorized path, its current
SHA-256, an integer line number already shown by READ_FILE or SEARCH at that
hash, and a single replacement line without a newline. It preserves the file's
line endings and BOM, rejects a no-op, and remains subject to focused validation
and independent review. It does not grant edits to unread or forbidden paths.
Coder `SEARCH` treats the query as literal text by default; `mode: "regex"`
enables a deliberate regular expression. A malformed explicit regex returns a
bounded protocol error rather than proving a symbol absent.
An incomplete JSON response receives a compact one-action retry hint. A
`FINISH_FAILED` claim that a function, endpoint, or symbol is absent is rejected
until the run has performed a scoped symbol search; Primary must still judge
whether the search query and conclusion were sound.
Explorer absence checks compare the claimed term with positive searches for
that term; unrelated positive searches do not refute a specific negative
result. Blanket claims that the repository lacks code still conflict with any
positive matches.
`SAFE_CREATE` content and `SAFE_REPLACE` find/replace text are preserved
exactly, including trailing spaces and newlines. Following a missed exact
replacement, the default `max_replace_chars_after_mismatch` is 300 for the
find block (and twice that for replacement text) in that file for this call;
the worker must narrow its next edit rather than repeat a whole function.
After failed validation, repeated SEARCH hits count as new repair evidence only
when they reveal a source line not previously observed at that file hash. Four
evidence actions are allowed per validation/edit revision before a one-shot
repair nudge. After any successful edit but before its next validation, four
reads/searches are allowed per edit revision; further reads/searches are
rejected, and a structured model request permits only an edit (including the
guarded line edit), VALIDATE,
FINISH_BLOCKED, or REQUEST_CONTRACT_REVISION. A new edit or validation state
resets the relevant window. Neither gate can claim validation success.
A file created successfully in this call can be read and `SAFE_REPLACE`d in the
same call, but only with a current content hash. This permission does not extend
to pre-existing files or future calls.
The default Coder budget is 28 turns with a 40-turn hard ceiling. A successful
edit near the limit may reserve up to six additional pre-validation turns once;
first validation may reserve ten repair turns. Repeated duplicate reads and
identical focused-test failures still stop early, so more turns do not authorize
unbounded wandering or change task-level fallback thresholds.
If focused tests and diff quality pass but a configured Ruff format check says
files would be reformatted, the runtime may once run the fixed Ruff formatter
only on changed, packet-writable Python files. It records the action, checks
other validation inputs did not change, and reruns full validation. Set
`autoformat_on_ruff_failure` to false to disable this recovery.

Explorer `SEARCH` defaults to literal text. Use `mode: "regex"` explicitly for
regular expressions; invalid regexes suggest a literal retry and do not prove
absence. Repository-wide absence claims are rejected when positive search
matches exist and must be reconciled with the observed files.
When a final report omits required observed test paths or source/test line
citations, Explorer gets one finish-only correction request. It may provide
structured `{path, line, claim}` citations; each line must have appeared in an
actual READ_FILE response. Bounded prompt replay does not invalidate an
earlier observed line. The normal final evidence checks still apply; a failed
correction is not scored as success.

Schema version 1 packets remain accepted. Runtime normalizes them to v2 using
the task id as the unit id, revision 1, repository-wide reads, generated
behavior/acceptance IDs, and the `python-focused` validation profile.

## Coder terminal states

- `ready_for_review`: required runtime checks passed after the final worker edit;
  the next normal step is independent Local Reviewer, then risk-routed Primary
  review and acceptance.
- `blocked`: scope, dependency, environment, requirement, or state prevents safe
  continuation. A requested scope expansion is a proposal, not authorization.
- `failed`: the invocation did not meet its automatic quality gate within its
  bounded repair/protocol budget.
- `policy_violation`: reserved for detected unauthorized or unsafe behavior.
- `interrupted`: the configured whole-run deadline expired or the user
  cancelled the process. Partial changes are retained for Primary inspection.

The compatibility action `FINISH_SUCCESS` maps to `ready_for_review`.

## Preflight

Before the first Coder model turn, runtime verifies:

- packet structure and scope relationships;
- configured validation profile;
- focused test paths;
- project Python executable;
- pytest importability in that Python;
- LM Studio endpoint and configured model visibility.

Environment failures return `blocked` and do not enter an implementation repair
loop.

## S2 execution boundary

- One Coder invocation holds `.agent/local-worker-write.lock` from immediately
  before its first model turn until it finishes. A second managed writer returns
  `blocked`; stale lock files are not silently removed.
- Coder mutations require current lock ownership. Losing the lock or having an
  unconfirmed timed-out validation process stops further writes and returns a
  policy result requiring Primary inspection.
- Reads and writes reject symlinks, Windows junctions, and other reparse-point
  components below the repository root.
- New files use exclusive creation. Replacements are written to a same-directory
  temporary file and installed with `os.replace` after a second content-hash
  check.
- Model requests, validation commands, Explorer calls, and whole Coder calls
  have separate trusted configuration timeouts. A timed-out validation launches
  process-tree cleanup and records whether termination was confirmed.
- Exit code `130` represents `interrupted`; `3` is `blocked`, and `4` is
  `policy_violation`.

## S3 baseline, validation, and run records

Before the first model turn, the runtime exclusively creates:

```text
.agent/tasks/<task_id>/runs/<run_id>/
```

A reused `run_id` returns `blocked/run_id_conflict`; an existing archive is
never overwritten or recycled. Every completed run contains `packet.json`,
`baseline.json`, `preimages.json`, exact authorized-file preimages,
`events.jsonl`, `changes.json`, `cumulative.diff`, `reverse.diff`,
`validation.json`, `post-state.json`, `handoff.json`, and `completed.json`.
Pytest JUnit evidence is stored alongside them. `current-task.json` is only a reconstructable pointer;
the task `state.json` retains execution history, Primary-owned decisions and
open issues.

The baseline records resolved repository identity, Git HEAD/status when Git is
available, packet/config hashes, authorized-file facts, and focused-test facts.
Git probes use a process-local, exact repository `safe.directory` setting and
do not modify global Git configuration. Preimages permit exact restoration of
this run's authorized files without discarding older user changes.
Post-state distinguishes runtime edits from unattributed changes to relevant
files. Existing user changes are not cleaned or rolled back.

Syntax validation uses Python `compile()` without producing `.pyc` files.
Focused pytest runs with cache writes disabled and emits JUnit statistics. Zero
collected tests, all-skipped/all-xfail results, missing JUnit evidence, command
failure, or relevant input changes during validation all fail the quality gate.
Before syntax/tests, the runtime rejects newly introduced trailing whitespace,
conflict markers, and missing final newlines. Historical unchanged violations
do not fail the unit. Trusted validation profiles may add fixed argument-array
commands; their exact status is recorded as runtime evidence, and validation
fails if those commands mutate relevant inputs.
The runtime snapshots authorized files, focused tests, and observed evidence
before/after validation and checks them again before `ready_for_review`.
Validation observations sent back to the model contain a bounded diagnostic
excerpt, failed test identifiers, edit revision, and remaining repair count.
When Coder modifies a focused Python test, the deterministic test-quality gate
requires each test function to contain an assertion, `pytest.raises`, or a
unittest-style assertion call. Primary must still review fixture and mock
semantics.
Each failed pytest case has its own bounded JUnit message and location in the
model-visible diagnostic. Every completed validation is also saved once as
`validation-attempt-N.json`; subsequent edits may clear the current
`validation.json`, but never erase earlier attempts. Two identical focused-test
failures without an intervening edit stop the call for Primary contract review;
three matching failures across edits also stop it. The runtime does not infer
that a failing test is obsolete. Edit observations report newly introduced
diff-quality issues with exact path and line, while `VALIDATE` remains the
authoritative quality gate.

Runtime execution history records facts and stable failure signatures across
packet revisions. It does not mark a unit accepted, decide material progress,
or clear open issues; those remain Primary review decisions.

After independent review, Primary uses `record-review.py` to append exactly one
`review.json` with `accept`, `rework`, `replan`, or `takeover`. The tool updates
the mutable task summary and policy-facing recent attempt without rewriting the
runtime execution history or handoff. A second review write is rejected.

## S4 compact handoff and evidence reuse

Coder CLI output and `last-*` reports are compact by default. They retain the
decision state, identity, changed-file list, JUnit counts, input-stability flag,
review checklist, blockers, uncertainty, and canonical evidence paths. Full
hashes, commands, events and logs remain in the run archive. `--full-report` is
available for diagnostics, not normal Primary review.

`diagnostic_logging` defaults to `true` and can be set to `false` in the
repository's `.local-agents/config.json` after the reliability investigation.
It adds bounded action metadata to Coder and Reviewer `events.jsonl` files and
creates `.agent/explorer-runs/<run_id>/events.jsonl` for each Explorer model call.
Explorer also retains a full per-call `report.json`. Supplying `-TaskId` to
`local-explore.ps1` links usage and both archive paths to that task even before
the first Coder run; without it, an early call remains unassociated. These
diagnostic entries include action type, scoped path, requested/returned line
range, result count, response length/hash, and error status. They do not store
raw model output, source content, search text, or replacement text. Existing
canonical packets, diffs, validation evidence, and error reports are separate
and remain available even when diagnostic logging is disabled. Cache hits do
not produce a new model-call log.
Protocol-error reports record response length and hash rather than a raw model
response excerpt.

Successful Explorer results are cached in `.agent/repo-map.json` by normalized
exact task text and a fingerprint of every visible repository file. `.agent`,
tool sources, environments and generated caches are excluded. A file add,
delete, size change, or modification-time change invalidates the fingerprint;
the Explorer then performs a fresh model call. Cache hits are marked explicitly
and can succeed without LM Studio being available. Cache writes are runtime
control-state writes; Explorer model actions remain read-only.
For a different question, successful prior observations provide bounded
navigation hints only for files whose current hashes still match. Coder receives
only hints inside its readable scope. Edits invalidate stale hints; after
Primary acceptance, actual changed paths are re-indexed by hash without
copying Coder-authored semantic claims into the map.

## S5 schema-constrained Coder actions

Coder chat-completion requests include an LM Studio JSON Schema response format
that requires one object with exactly `action` and `arguments` at the top level.
This prevents unescaped newlines or surrounding prose from turning an otherwise
valid edit into malformed JSON. The schema is deliberately broad inside
`arguments`: existing runtime dispatch, path scope, read-hash, validation, lock,
and terminal-state checks remain authoritative.

Coder sampling parameters and its output limit are supplied by trusted config,
not inherited from the LM Studio GUI. The default output limit is 4096 tokens.
Structured output may be disabled through trusted config for backend
compatibility, but doing so restores prompt-only JSON compliance.

## S6 unit risk, inherited rework, and Local Reviewer

Primary decomposes a feature into cohesive implementation units. Feature risk
does not force every unit to use the same review depth, but atomic high-risk
invariants remain in one high-risk unit. Small units route from Local Reviewer
to Primary evidence acceptance, medium units to lightweight Primary review, and
high units to full Primary diff review. High integration-risk features still
receive a final cumulative Primary review.

Focused rework may provide only new identity/revision, `parent_run_id`,
`preserve_contract: true`, and non-empty `review_feedback`. Runtime loads the
parent canonical packet from the same task/unit and inherits its goal, scope,
risk, contracts, tests, validation profile, and limits. Other overrides are
rejected, the child revision must increase, and the parent packet hash is stored
in inheritance metadata. The child also receives a compact, bounded traceback
from the immutable parent handoff and validation: changed paths, failed focused
test IDs, failed configured checks, and the last protocol error. It is a repair
hint, not a substitute for reading the current code and validation evidence.

Local Reviewer has a separate LM Studio request and fresh context. It can only
`READ_FILE`, `SEARCH`, registered `RUN_APPROVED_TEST`/
`RUN_APPROVED_STATIC_CHECK`, and `REPORT`; it cannot edit or issue arbitrary
commands. With `reviewer_native_tools: true`, the request advertises exactly
those five OpenAI function tools. One returned tool call is normalized to the
same validated action protocol; malformed or multiple calls fail closed. This
transport prevents Muse's unparsed `to=READ_FILE` completion from becoming an
LM Studio `peg-native` HTTP 400 in the repeated frozen probes. It
reviews the actual cumulative diff and runtime evidence, not Coder claims, and
returns `pass_to_primary`, `rework`, or `escalate`. Immutable review archives
are stored under:

```text
.agent/tasks/<task_id>/reviews/<review_id>/
```

Findings contain stable ids, severity, category, concrete evidence, optional
file/line, affected owned contract, and a suggested bounded fix. Reviewer usage
and decisions are appended to task state. The example Reviewer model is
`meta/muse-glimmer`; compare its live findings and false positives on
representative cases before relying on compact Primary review. Reviewer reads
changed source and focused tests, independently checks adjacent behavior, and
reports concrete bugs or test gaps beyond the supplied obligations. Contract
conflicts escalate to Primary. The trusted `local-unit.py` dispatcher checks
the canonical Coder archive and unchanged validation inputs before automatically
starting Reviewer. Primary performs full or lightweight review afterward by
risk; an anomaly interrupts this route. Reviewer may request only registered
approved test and static-check ids; the trusted runtime executes them.
For a high-risk pass, `contract_review` must cover every owned required behavior
with `source_ref` (`path`, `start_line`, `end_line`) covering at most 20 lines
actually shown by `READ_FILE`, and contract-specific reasoning. The runtime
materializes `canonical_quote` and `source_hash`; the model need not copy exact
source text. Legacy `path`/`line`/`source_quote` reports remain accepted when
the quote matches the current line. Primary can mark a structured
rework note with `verify_in_review: true`, a stable `finding_id`, owned
`contract_id`, `text`, and `source_anchor` to require a separate focused
review at any risk level; the canonical cited text must contain that anchor. Untagged history remains
context only. Put essential requirements in `required_behavior` as well:
evidence accounting does not prove semantic correctness, and Primary still
reviews the full diff.
For a pass, ordering-sensitive packets use stable `RO-1`/`FO-1` IDs supplied
in `ordering_constraints`, not copies of constraint prose. Required-order
items need read source path/line evidence. Forbidden-ordering items may use
source evidence or cumulative-diff evidence; whole-diff absence checks need
not invent a source line. Invalid reports receive a packet-specific template
and valid IDs for repair, with repeated identical errors stopped early.
An empty `SEARCH` query receives a concrete `READ_FILE` suggestion for a changed
path when available; it remains a protocol error and identical repeats stop early.
Reviewer default `SEARCH` traverses only the packet's readable roots and skips
excluded or reparse paths. Invalid REPORT feedback lists legal obligation and
ordering IDs, names unknown/duplicate obligations, and suggests the missing
`READ_FILE` range for unread source-line evidence. Diff evidence must not
include a source line.
Three consecutive duplicate `READ_FILE` actions stop the review. If a REPORT
cites an unread source line, the runtime performs the suggested bounded
read-only source read and includes it in repair feedback; Reviewer must still
submit a new, valid REPORT. Before Coder's first edit or validation, eight
consecutive `READ_FILE`/`SEARCH` actions without new source-line evidence stop
the call, including alternating repetitions of both action types.
The report also acknowledges every `configured_checks` id that actually passed
in runtime validation. These protocol checks force evidence accounting; they
do not guarantee the local model's semantic judgment, so Primary still follows
the risk-routed review depth.

## Trust boundary

Action allowlists constrain model-dispatched runtime operations. They are not an
operating-system sandbox. Focused pytest executes trusted repository code,
imports, `conftest.py`, and plugins with the Python process's actual permissions.
