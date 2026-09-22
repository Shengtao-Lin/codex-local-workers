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

## Local Explorer

Use Explorer when locating code, tests, or call flow would require meaningful
repository investigation. A single user task may call Explorer more than once
when later phases introduce genuinely different unanswered questions. Each call
must remain focused and independently bounded.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File ".local-agents\local-explore.ps1" `
  -Task "<focused read-only investigation>"
```

Explorer is strictly read-only and calls LM Studio directly. Do not use it for
obvious or already-located changes. Condense useful findings into the Coder
implementation packet; never forward a large raw exploration transcript.

## Local Coder

Coder is a bounded implementation worker driven directly through LM Studio. It
does not run inside a general Codex agent loop and has no shell, Git, delegation,
or unrestricted file-writing action.

Before invocation, the Primary Agent must create a schema-version-2 JSON packet
that defines readable and writable scope, stable task/unit/revision identity,
required behavior, acceptance criteria, validation profile, and focused tests.
Include stable `acceptance_scenarios` for the normal path, important error path,
and relevant boundary whenever they are distinct.
Schema version 1 remains supported through explicit compatibility normalization.
Invoke from the target repository root:

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

## Required Primary Agent review

After every `ready_for_review` result, inspect reality:

```powershell
git status --short
git diff --check
git diff
```

Review every changed file, test quality, behavior against the packet, accidental
scope expansion, and suspicious error handling. Then run the appropriate broader
regression checks. Do not accept model-authored summaries as proof.

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
- Workers never request Git operations and the runtime never changes Git state
  or rolls back files. The trusted runtime may read HEAD/status for baseline
  evidence. The Primary Agent decides whether partial changes should be retained,
  corrected, or reverted after inspecting the diff.

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

## Efficiency policy

The normal flow is:

```text
Primary understands and designs
→ optional focused Explorer
→ one bounded Coder packet
→ Primary reviews actual diff
→ Primary runs broader validation
→ ACCEPT / focused REWORK / TAKEOVER
```

Avoid worker recursion, broad prompts, repeated exploration without a new
question, and delegation for trivial edits. Only information useful to the
active task belongs in task memory. Track task-level call totals, failure
signatures, progress, and quality-gate streaks in `.agent/current-task.json`.
Per-invocation runtime limits apply independently to every worker call and are
safety boundaries, not task-level fallback triggers.

Normal Coder output is a compact handoff. Read the canonical run archive only
for files/evidence needed by the current review or when the compact result shows
failure, uncertainty, truncation, or unattributed changes. Explorer may reuse an
exact prior task only when its runtime reports a valid unchanged-repository cache
hit; otherwise treat it as a new exploration.

Increment informational Explorer/Coder totals when a worker reaches its first
model turn, whether it later succeeds or fails. Totals do not cause fallback.
A launch/configuration failure before the first model turn is recorded as
infrastructure context but does not affect a worker-quality streak. Planned
Coder steps do not count as review rework. Give every invocation a distinct run
id and retain compact recent outcomes with `unit_id`, `progress`, and a stable
`failure_signature`. Use `.local-agents/task-policy.py` to evaluate the recorded
streaks when the fallback decision is not obvious.
