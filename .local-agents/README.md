# Local agents

Both workers call LM Studio's OpenAI-compatible chat endpoint directly.
`explorer-runtime.py` exposes read-only repository actions;
`worker-runtime.py` exposes bounded implementation and validation actions.

## Layout and compatibility

The project-local `.local-agents` directory is the default installation and
contains the Python entrypoints, runtime, configuration, and wrappers:

- `local-code.py`
- `local-explore.py`
- `local-code.ps1`
- `local-explore.ps1`
- `explorer-runtime.py`
- `worker-runtime.py`
- `safe-edit.py`
- `run-state.py`
- `record-review.py`
- `evidence-cache.py`
- `task-policy.py`
- `protocol.md`
- `config.example.json` (tracked template)
- `config.json` (local, ignored configuration)

An optional copy under `%USERPROFILE%\.codex\local-workers` may be retained as a
compatibility entry, but project operation must not depend on that global path.

## Setup and requirements

Create the local configuration before the first invocation:

```powershell
Copy-Item .local-agents\config.example.json .local-agents\config.json
```

- Windows PowerShell
- LM Studio listening at the URL in `config.json`
- the configured Qwen model loaded or available in LM Studio
- target repository virtual environment at `.\.venv\Scripts\python.exe`
- pytest installed in that environment

The runtime itself uses only the Python standard library.

## Invocation

Run a focused read-only exploration from the target repository root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File ".local-agents\local-explore.ps1" `
  -Task "Trace how configuration reaches request handling." `
  -Report ".agent\last-local-explorer-report.json"
```

Create a Coder packet based on `example-packet.json`, then run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File ".local-agents\local-code.ps1" `
  -Packet ".agent\implementation-packet.json" `
  -Config ".local-agents\config.json" `
  -Report ".agent\last-local-coder-report.json"
```

`-Config` is optional and defaults to the configuration next to the runtime.
It is useful for isolated benchmark copies or repositories whose trusted Python
interpreter is configured outside their own root.

The Coder exits zero only with `ready_for_review`, after runtime-observed syntax
checks and focused pytest succeed after the final edit. `blocked` exits with code
3, `policy_violation` with 4, and `interrupted` with 130. The Primary Agent must
still review the actual diff and decide acceptance.

Coder requests use LM Studio JSON Schema structured output by default. The
schema guarantees one syntactically valid `{action, arguments}` object; the
runtime still validates action-specific fields, paths, hashes, state, and
authorization. `coder_structured_output` is an explicit backend-compatibility
fallback. Sampling and output limits come from `config.json`, so GUI inference
defaults do not silently change worker behavior.

Some managed Windows command sandboxes prevent child Python processes from
writing even within the workspace. The runtime reports this as an environment
block and never elevates itself. Primary may choose the host's approved execution
path after considering the repository and command.

## Protocol and security boundary

Explorer can request only `LIST_FILES`, `SEARCH`, `READ_FILE`, and finish actions.
Coder can request only `READ_FILE`, `SEARCH`, `SAFE_CREATE`, `SAFE_REPLACE`,
`VALIDATE`, and finish actions. Neither worker can construct commands. Coder
writes are restricted to the packet's exact create/modify allowlists. Existing
files require an exact unique replacement and a current SHA-256 read token.
Managed Coder runs also hold one repository write lock, reject symlink/junction
path components, create files exclusively, and atomically replace existing
files after rechecking their hash. A validation timeout triggers process-tree
termination; uncertain termination prevents further writes.

Each Coder `run_id` owns an immutable archive under
`.agent/tasks/<task_id>/runs/<run_id>/`. It contains the final packet, pre-run
baseline, compact tool events, actual relevant changes, validation evidence,
post-state, and handoff. Reusing a run id is blocked instead of overwriting the
old record. Task state keeps runtime facts separate from Primary-owned accepted
decisions and open-issue conclusions.

After reviewing actual changes and broader validation, Primary records its
decision once:

```powershell
python .local-agents/record-review.py `
  --task-id "task-1" --run-id "task-1-unit-1-a1" `
  --decision accept --summary "Reviewed diff and regression evidence."
```

Review decisions are `accept`, `rework`, `replan`, or `takeover`. `review.json`
is exclusive-create and cannot silently replace an earlier review.

Coder output is compact by default so Primary need not ingest full hashes and
command logs on a normal success. The immutable run archive remains complete;
pass `--full-report` only when detailed diagnostics are needed.

Explorer caches successful results for an exact repeated task in
`.agent/repo-map.json`. Reuse occurs only while the visible repository
fingerprint is unchanged; otherwise Explorer calls the local model again and
refreshes the entry.

Use the smallest path that preserves quality:

- tiny, obvious, already-located edit: Primary implements directly;
- known files and settled behavior: one bounded Coder packet;
- unclear location or call flow: focused Explorer, then Coder if appropriate;
- architecture, security, concurrency, or ambiguous behavior: Primary settles
  invariants first and delegates only a bounded implementation if useful.

Python syntax checks do not emit bytecode. Focused pytest produces JUnit counts;
zero-test and all-skipped runs cannot become `ready_for_review`. Relevant source,
test, and observed evidence facts are bound to the validation result and checked
again when the worker tries to finish.

These action restrictions are not an operating-system sandbox. Pytest executes
trusted repository code, imports, `conftest.py`, and plugins with the actual
Python process permissions and may create side effects outside `safe-edit.py`.
V1 is for trusted local repositories.

Task-level fallback and invocation-level limits are separate. A task may use
multiple Explorer and Coder calls for as many distinct implementation steps as
needed. Each Explorer call has its own turn/read/search budget; each Coder call
has its own turn/protocol/repair budget. These per-call limits stop a single
worker loop but do not impose a total task-call ceiling.

Task fallback is progress based. By default, Primary falls back after the same
failure signature repeats three times without progress, the same unit has three
no-progress outcomes, or a worker fails the same quality gate three times.
Material progress resets the applicable streak. Unsafe or out-of-scope behavior
causes immediate takeover. `task-policy.py` provides a deterministic evaluator
for the state recorded in `.agent/current-task.json`.

Run the zero-dependency boundary tests with:

```powershell
python -m unittest discover -s .local-agents\tests -v
```
