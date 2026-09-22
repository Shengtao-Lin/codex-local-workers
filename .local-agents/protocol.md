# Local worker protocol

## Coder packet schema v2

Each Coder invocation receives one final packet. Primary feedback must be merged
into a new packet revision rather than supplied as a conflicting side channel.

Required identity fields:

- `schema_version`: `2`
- `task_id`: stable top-level user task
- `unit_id`: stable logical work unit across retries
- `run_id`: unique invocation identity
- `attempt`: invocation number for the unit
- `plan_revision`: Primary plan version
- `packet_revision`: current execution instruction version

Scope fields:

- `scope.read`: readable files or directory roots
- `scope.modify`: existing files the Coder may change
- `scope.create`: new files the Coder may create
- `scope.forbidden`: paths excluded from reading and writing

`.agent`, `.local-agents`, and `AGENTS.md` are reserved control paths and are
never writable by Coder, even if a packet lists them.

`required_behavior` and `acceptance_criteria` are arrays of stable `id`/`text`
objects. `validation_profile` selects a trusted profile from `config.json`;
workers cannot submit arbitrary shell strings.
`acceptance_scenarios` names the normal, important failure, and boundary cases
Primary expects to review. Older packets without it receive compatibility
scenarios derived from their acceptance criteria.

Schema version 1 packets remain accepted. Runtime normalizes them to v2 using
the task id as the unit id, revision 1, repository-wide reads, generated
behavior/acceptance IDs, and the `python-focused` validation profile.

## Coder terminal states

- `ready_for_review`: required runtime checks passed after the final worker edit;
  Primary must still review and accept.
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
`baseline.json`, `events.jsonl`, `changes.json`, `validation.json`,
`post-state.json`, `handoff.json`, and `completed.json`. Pytest JUnit evidence is
stored alongside them. `current-task.json` is only a reconstructable pointer;
the task `state.json` retains execution history, Primary-owned decisions and
open issues.

The baseline records resolved repository identity, Git HEAD/status when Git is
available, packet/config hashes, authorized-file facts, and focused-test facts.
Post-state distinguishes runtime edits from unattributed changes to relevant
files. Existing user changes are not cleaned or rolled back.

Syntax validation uses Python `compile()` without producing `.pyc` files.
Focused pytest runs with cache writes disabled and emits JUnit statistics. Zero
collected tests, all-skipped/all-xfail results, missing JUnit evidence, command
failure, or relevant input changes during validation all fail the quality gate.
The runtime snapshots authorized files, focused tests, and observed evidence
before/after validation and checks them again before `ready_for_review`.

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

Successful Explorer results are cached in `.agent/repo-map.json` by normalized
exact task text and a fingerprint of every visible repository file. `.agent`,
tool sources, environments and generated caches are excluded. A file add,
delete, size change, or modification-time change invalidates the fingerprint;
the Explorer then performs a fresh model call. Cache hits are marked explicitly
and can succeed without LM Studio being available. Cache writes are runtime
control-state writes; Explorer model actions remain read-only.

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

## Trust boundary

Action allowlists constrain model-dispatched runtime operations. They are not an
operating-system sandbox. Focused pytest executes trusted repository code,
imports, `conftest.py`, and plugins with the Python process's actual permissions.
