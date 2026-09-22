# Codex Local Workers — Design Brief

## 1. Goal

Design a small, drop-in orchestration kit that can be copied directly into an existing **Python repository** and used by **Codex / GPT-5.6 Sol** to delegate bounded implementation work to local models running in **LM Studio**.

This is intentionally a narrow v1. The goal is **not** to build a general multi-agent framework.

Target workflow:

```text
GPT-5.6 Sol
  ├─ understands the user request
  ├─ owns architecture and implementation planning
  ├─ defines task scope / file boundaries / acceptance criteria
  ├─ optionally delegates repository exploration
  │
  ▼
Local Explorer
  └─ gpt-oss-20b
     read-only repository investigation
  │
  ▼
GPT-5.6 Sol
  └─ produces a bounded implementation packet
  │
  ▼
Local Coder
  └─ Qwen3-Coder
     implement → test → repair locally
  │
  ├─ success → structured handoff
  └─ repeated failure → structured failure summary
  │
  ▼
GPT-5.6 Sol
  ├─ independently reviews actual git diff
  ├─ runs broader validation
  ├─ ACCEPT → next implementation step
  └─ REWORK → focused feedback back to Qwen
                ↓
             Local Coder
```

The system should support a small number of GPT ↔ Qwen rework loops and then allow GPT to take over if local implementation remains unreliable.

---

# 2. Core Design Principle

```text
GPT = architect + planner + reviewer + final authority
Qwen = bounded implementation agent
gpt-oss = read-only repository explorer
repository + git diff + actual test results = source of truth
```

Do not make Qwen responsible for high-level architecture.
Do not make Qwen decide broad file/module structure unless GPT explicitly leaves that decision open.
Do not trust worker summaries as authoritative evidence. GPT must review the actual repository state.

---

# 3. v1 Scope

v1 only needs to support:

- Windows
- PowerShell
- Python projects
- project-local virtual environment: `\.venv\Scripts\python.exe`
- pytest
- LM Studio on localhost
- GPT-5.6 Sol running through Codex as the primary agent
- Local Explorer model: `openai/gpt-oss-20b`
- Local Coder model: `qwen3-coder-30b-a3b-instruct-i1`
- single repository at a time
- sequential implementation tasks
- local task memory
- bounded retry loops

Explicitly out of scope for v1:

- Linux/macOS
- Node/Java/etc.
- Ollama
- OpenAI API as worker backend
- Anthropic APIs
- remote workers
- multi-repository orchestration
- parallel agents
- web UI
- database-backed memory
- vector memory / RAG memory
- generic plugin framework
- LangGraph/LangChain dependency unless there is a very strong reason
- distributed task queue
- autonomous long-running project manager

Keep dependencies minimal.

---

# 4. Drop-in Repository Layout

The kit should be usable by copying it directly into another Python project.

Preferred target layout:

```text
target-project/
├─ AGENTS.md
├─ .agent/
│  └─ current-task.json
├─ .local-agents/
│  ├─ config.json
│  ├─ local-explore.ps1
│  ├─ local-code.ps1
│  ├─ worker-runtime.py
│  ├─ safe-edit.py
│  └─ README.md
├─ src/
├─ tests/
├─ pyproject.toml
└─ ...
```

Avoid requiring `pip install local-agent-orchestrator` for v1.

`.local-agents/` contains the reusable runtime.
`.agent/` contains mutable task state / short-term shared memory.

---

# 5. Existing Working Components / Lessons Learned

## 5.1 Local Explorer

The Explorer currently works reliably enough when constrained properly.

Model:

```text
openai/gpt-oss-20b
```

Behavior:

- read-only
- targeted repository search
- inspect implementation and focused tests
- return relevant files, call/data flow, important findings, tests, and uncertainties

Important constraints learned from testing:

- explicitly state Windows PowerShell
- forbid `head`, `tail`, `grep`, `sed`, `awk`
- exclude `.venv`, `.git`, `node_modules`, `.pytest_cache`, `.ruff_cache`, `__pycache__`
- avoid recursive repository dumps
- use targeted searches
- keep file/tool-call budgets soft but bounded
- Explorer must remain strictly read-only
- parent Codex must wait for the worker process to fully exit rather than treating an initial shell yield/session ID as failure

Explorer currently uses Codex CLI + LM Studio and can remain agentic in v1.

## 5.2 Local Coder Infrastructure

The following now works:

- LM Studio model invocation
- repository reads
- repository writes
- PowerShell commands
- project `.venv`
- focused pytest
- safe file editing
- Codex process waiting / polling
- Windows workspace-write using `windows.sandbox = "unelevated"`

The original Windows `workspace-write` sandbox failed with:

```text
helper_unknown_error: setup refresh had errors
```

Using the unelevated Windows sandbox resolved that infrastructure problem.

## 5.3 Current Local Coder Problem

The remaining problem is model execution reliability when Qwen is given a fully general Codex agent loop.

Observed failures:

- repeatedly re-reading context
- attempting to invoke Local Explorer from inside Local Coder
- not respecting leaf-worker instructions
- stopping after partially implementing a change
- creating a helper but failing to wire it into actual execution
- failing to add required tests
- failing to run syntax validation or focused tests
- exhausting its working budget
- previously using unsafe ad-hoc PowerShell/Python file replacement strategies
- previously creating backup/temp files
- previously causing syntax/indentation damage

This means v1 should preserve Qwen's ability to:

```text
read → reason → edit → test → repair
```

while reducing its ability to:

```text
launch arbitrary agents
invent uncontrolled orchestration
perform dangerous file manipulation
retry indefinitely
```

Do not reduce Qwen to a single-shot code-completion model unless necessary.
The desired solution is a **bounded coding agent/runtime**.

---

# 6. Desired Responsibility Split

## GPT-5.6 Sol / Primary Agent

GPT owns:

- user intent
- architecture
- implementation plan
- task decomposition
- file-level scope
- files allowed to modify
- files allowed to create
- forbidden files/areas
- expected behavior
- acceptance criteria
- focused test targets
- deciding whether Explorer is needed
- deciding whether Qwen is appropriate
- Git operations
- code review
- broader tests
- integration validation
- deciding ACCEPT / REWORK / TAKEOVER
- updating authoritative task memory
- final response to user

GPT should not delegate merely because workers exist. Tiny obvious changes may be done directly.

## Local Explorer

Explorer owns:

- targeted read-only search
- locating relevant files
- understanding call/data flow
- locating tests
- identifying uncertainties

Explorer does not modify files, implement code, run destructive commands, or make final architecture decisions.
Explorer output is research notes, not authority.

## Local Coder / Qwen

Qwen owns bounded implementation within the packet provided by GPT.

Qwen may:

- read authorized/relevant files
- inspect relevant tests
- search within allowed repository context
- create explicitly authorized files
- modify explicitly authorized files
- add/update focused tests
- run Python syntax checks
- run focused pytest
- inspect failures
- repair its own implementation a limited number of times
- produce a structured handoff

Qwen must not:

- invoke Codex
- invoke Local Explorer
- invoke another Local Coder
- delegate to another agent
- use Git
- commit/push
- modify Git config/remotes
- install packages
- create another virtualenv
- broaden architecture on its own
- create unapproved production modules
- rename/delete/move files without explicit authorization
- run full-suite tests unless explicitly allowed
- retry indefinitely

---

# 7. Implementation Packet

GPT should hand Qwen a structured implementation packet. Design an appropriate JSON representation.

Example concept:

```json
{
  "task_id": "lease-fencing-01",
  "goal": "Prevent stale workers from committing job completion after lease loss.",
  "phase": "implementation",
  "attempt": 1,
  "scope": {
    "modify": [
      "src/evaluation_harness/jobs/worker.py",
      "tests/unit/test_worker_heartbeat.py"
    ],
    "create": [],
    "forbidden": [
      "src/evaluation_harness/jobs/queue.py"
    ]
  },
  "required_behavior": [
    "heartbeat lease loss must fence the running worker",
    "a stale worker must not commit success",
    "a stale worker must not commit failure",
    "existing heartbeat cleanup behavior must remain intact"
  ],
  "acceptance_criteria": [
    "modified Python files compile",
    "focused worker heartbeat tests pass"
  ],
  "focused_tests": [
    "tests/unit/test_worker_heartbeat.py"
  ],
  "max_local_repairs": 2
}
```

The exact schema can change. The important property is that GPT defines WHAT and WHERE. Qwen focuses on HOW.

---

# 8. Qwen Local Coding Loop

The Local Coder should behave like a bounded state machine:

```text
LOAD TASK
   ↓
LOAD TASK MEMORY
   ↓
READ / SEARCH
   ↓
PLAN LOCAL IMPLEMENTATION
   ↓
EDIT
   ↓
RE-READ MODIFIED REGION
   ↓
PY_COMPILE
   ↓
FOCUSED PYTEST
   ↓
   ├─ PASS → HANDOFF SUCCESS
   └─ FAIL
        ↓
      inspect failure
        ↓
      repair
        ↓
      retry
        ↓
      max local repairs reached
        ↓
      HANDOFF FAILED
```

Qwen should retain multi-turn reasoning.
Do not simply ask Qwen for one JSON patch and terminate unless that proves necessary.
The runtime should enforce hard capability boundaries rather than relying only on prompt instructions.

---

# 9. Controlled Actions / Tools

Design a small set of actions that Qwen is allowed to perform.

Possible conceptual actions:

```text
READ_FILE
SEARCH
SAFE_CREATE
SAFE_REPLACE
PY_COMPILE
RUN_FOCUSED_TEST
FINISH_SUCCESS
FINISH_FAILED
```

Avoid giving Qwen unrestricted arbitrary shell access if a smaller capability can achieve the same goal.
However, do not over-engineer v1.

The design should decide whether:

1. Qwen should continue running through `codex.cmd exec` with more constrained capabilities, or
2. `worker-runtime.py` should directly drive LM Studio in a bounded multi-turn loop.

Evaluate both and recommend one for v1.
The observed behavior of Qwen repeatedly invoking Explorer inside Codex should be considered strongly in this decision.

---

# 10. Safe Editing

A `safe-edit.py` prototype already exists and works.

Required behavior:

## create

- create a file only if it does not already exist
- refuse overwrite
- path must remain inside repo
- UTF-8
- no automatic `.bak`

## replace

- exact contiguous replacement
- target must appear exactly once
- zero matches → fail
- multiple matches → fail
- preserve newline style
- preserve UTF-8 BOM when present
- path must remain inside repo

Do not support unsafe arbitrary whole-file overwrite for existing files unless there is a compelling reason.
Do not support delete/move/rename in v1 unless required.
Qwen should not create temp source files or backup files.

---

# 11. Python Validation

v1 can assume:

```text
.\.venv\Scripts\python.exe
```

For modified Python files:

```powershell
.\.venv\Scripts\python.exe -m py_compile <file>
```

Focused test command:

```powershell
.\.venv\Scripts\python.exe -B -m pytest <focused test paths> -q
```

Rules:

- syntax validation before pytest
- never claim tests passed unless actually executed successfully
- local worker runs focused tests only
- GPT runs broader regression/integration validation afterward

---

# 12. Local Repair Loop

Qwen should be allowed a limited local repair loop so GPT is not involved in every small test failure.

Recommended default:

```text
max_local_repairs = 2
```

Example:

```text
implementation
→ syntax/test failure
→ repair #1
→ syntax/test
→ repair #2
→ syntax/test
```

After the limit, return `FAILED` with a concise structured failure summary.

Failure summary should include:

- what was attempted
- files changed
- failure observed
- tests/validation run
- why the worker could not safely finish
- current repository state
- whether partial changes remain
- likely next decision for GPT

---

# 13. GPT Review Loop

After Qwen returns, GPT must independently inspect reality.

Required review sequence:

```text
git status --short
git diff --check
git diff
```

Then:

- inspect modified files
- check implementation against original task packet
- run broader relevant tests
- optionally run lint/type checks if appropriate

GPT then decides `ACCEPT` or `REWORK`.

If REWORK:

- GPT writes focused review feedback
- GPT may narrow or expand file scope
- GPT generates a correction packet
- Qwen gets another bounded implementation attempt

Recommended default:

```text
max_review_reworks = 2
```

If Qwen still cannot complete after the allowed review cycles, GPT takes over implementation or redesigns the task.
Avoid uncontrolled back-and-forth.

---

# 14. Task Memory

The system should maintain a small shared working memory.

Preferred location:

```text
.agent/current-task.json
```

The memory is:

- readable by GPT
- writable/authoritative by GPT
- readable by Qwen
- not freely writable by Qwen

Qwen should return a handoff report. GPT decides what becomes authoritative shared memory.
The repository and actual diff remain the source of truth.

---

# 15. Suggested Task Memory Contents

Design a compact structure similar to:

```json
{
  "task_id": "lease-fencing-01",
  "status": "in_progress",
  "phase": "rework",
  "attempt": 2,
  "goal": "...",
  "scope": {
    "modify": [],
    "create": [],
    "forbidden": []
  },
  "acceptance_criteria": [],
  "explorer_findings": [],
  "history": [
    {
      "attempt": 1,
      "worker": "qwen",
      "result": "failed",
      "summary": [
        "helper was inserted",
        "helper was not connected to Worker.execute",
        "required tests were not added"
      ]
    }
  ],
  "primary_review": {
    "status": "rework",
    "findings": [],
    "next_instruction": "..."
  }
}
```

Do not allow this file to grow forever.
Keep only information useful for the active task and the most relevant recent attempts.
When a task is accepted, compress its state into a small final summary or archive it.

---

# 16. Memory Precedence

Qwen should receive task memory, but history must not override current instructions.

Use precedence equivalent to:

```text
1. current GPT implementation packet
2. latest GPT review feedback
3. actual current repository state
4. current task memory
5. historical attempts
```

Explicitly tell Qwen:

```text
Previous attempts are historical context, not authoritative design.
The current implementation packet and Primary Agent review take precedence.
```

---

# 17. Explorer Handoff

If Explorer is used, avoid making Qwen repeat all exploration from scratch.
GPT should be able to place concise Explorer findings into the implementation packet or task memory.

Example:

```json
{
  "explorer_findings": [
    "Worker._heartbeat_loop stops after heartbeat() returns false",
    "Worker.execute continues independently and may later commit state",
    "existing tests cover heartbeat renewal, lease loss stop, and cancellation cleanup"
  ]
}
```

Qwen may still inspect source files directly, but should not launch Explorer itself.

---

# 18. Handoff Report

Qwen should return a structured result.

Success concept:

```json
{
  "status": "success",
  "task_id": "lease-fencing-01",
  "attempt": 1,
  "changed_files": [
    "src/evaluation_harness/jobs/worker.py",
    "tests/unit/test_worker_heartbeat.py"
  ],
  "summary": ["..."],
  "validation": {
    "py_compile": "passed",
    "focused_tests": {
      "command": "...",
      "result": "5 passed"
    }
  },
  "remaining_uncertainty": []
}
```

Failure concept:

```json
{
  "status": "failed",
  "task_id": "lease-fencing-01",
  "attempt": 1,
  "changed_files": [],
  "attempts": ["..."],
  "failure_summary": ["..."],
  "validation": {
    "py_compile": "...",
    "focused_tests": "..."
  },
  "current_repo_state": "...",
  "recommended_escalation": "..."
}
```

Keep it useful and compact.

---

# 19. AGENTS.md Role

`AGENTS.md` should describe orchestration policy for GPT/Sol.

It should establish:

- GPT is Primary Agent and final authority
- Explorer is optional and read-only
- Coder is bounded implementation worker
- GPT defines task scope before Coder invocation
- workers may run for several minutes
- initial shell timeout/session ID is not worker failure
- parent must poll the same worker process until exit
- Git belongs to GPT
- local coder performs focused validation
- GPT performs code review and broader validation
- worker result is untrusted until GPT checks repository state
- bounded retry behavior
- no uncontrolled worker recursion
- ACCEPT / REWORK / TAKEOVER flow

Keep `AGENTS.md` relatively short. It should act as a map/policy, not contain the entire runtime implementation manual.

---

# 20. Configuration

Keep configuration minimal.

Example:

```json
{
  "lmstudio_base_url": "http://127.0.0.1:1234/v1",
  "explorer_model": "openai/gpt-oss-20b",
  "coder_model": "qwen3-coder-30b-a3b-instruct-i1",
  "python": ".\\.venv\\Scripts\\python.exe",
  "max_local_repairs": 2,
  "max_review_reworks": 2
}
```

Do not create a generic provider abstraction in v1. LM Studio only.

---

# 21. LM Studio Compatibility

Current LM Studio `/v1/models` returns an OpenAI-style object with a `data` array.
Codex CLI currently logs compatibility warnings because it expects a different model metadata shape.

Observed warning:

```text
failed to decode models response: missing field `models`
```

and:

```text
Model metadata for MODEL not found.
Defaulting to fallback metadata
```

These warnings have not prevented actual model execution.
Treat this as non-fatal unless the new design depends on Codex model metadata.

If `worker-runtime.py` talks directly to LM Studio, prefer the normal LM Studio OpenAI-compatible endpoint rather than reproducing Codex's metadata expectations.

---

# 22. Current Models

## Explorer

```text
openai/gpt-oss-20b
```

Good at repository investigation when constrained.

## Coder

```text
qwen3-coder-30b-a3b-instruct-i1
```

Good local coding model, but currently unreliable when given a fully general Codex agent loop.
The design should preserve its coding/reasoning ability while constraining orchestration capabilities.

---

# 23. Important Non-Goals

Do not attempt to make Qwen equal to GPT in authority.
Do not create a fully autonomous software company.
Do not make agents negotiate endlessly.
Do not build a generic workflow engine.
Do not add complexity solely for future extensibility.

This project exists to reduce expensive GPT coding work while preserving GPT-level architecture, review, and judgment.

---

# 24. Desired End-to-End Example

```text
User:
"Add feature X."

GPT:
- understands request
- inspects project
- optionally invokes Explorer
- decides architecture
- breaks work into Step 1 / Step 2 / Step 3

GPT writes Step 1 packet:
- modify A.py
- modify test_A.py
- no new files
- behavior requirements
- focused tests

Qwen:
- reads task + memory
- reads A.py and test_A.py
- implements
- py_compile
- pytest
- test fails
- repairs
- pytest passes
- returns structured success

GPT:
- git status
- diff check
- diff review
- broader tests
- ACCEPT

GPT:
- writes Step 2 packet

...

If GPT review fails:
- GPT writes focused correction packet
- Qwen repairs
- GPT reviews again

If repeated rework fails:
- GPT takes over.
```

That is the target experience.

---

# 25. Design Questions for Codex

Before implementing, please evaluate and answer:

1. Should v1 Local Coder continue using `codex.cmd exec`, or should `worker-runtime.py` call LM Studio directly?
2. How should a bounded multi-turn Qwen coding loop be implemented while preserving model reasoning but preventing nested-agent behavior?
3. What is the smallest practical action/tool set Qwen needs?
4. How should file read/search results be passed back into the Qwen conversation without exploding context?
5. Should Qwen request actions through strict JSON, tool/function calling, or another protocol?
6. How should malformed model output be handled?
7. How should the runtime guarantee that Qwen cannot modify files outside the GPT-authorized scope?
8. How should local repair attempts be counted?
9. How should partial edits be handled when a local attempt fails?
10. Should failed Qwen attempts automatically revert their own changes, or should GPT always decide rollback after inspecting the diff?
11. What exact fields belong in `current-task.json`?
12. Should completed task history be archived or compressed?
13. How should Explorer findings be injected into the Coder task without duplicating large context?
14. How should the handoff report be validated?
15. What should the minimum acceptance-test suite for this orchestration kit itself include?

---

# 26. Requested Output From Codex

For the first pass, **do not immediately implement the entire system**.

First produce a design proposal containing:

1. recommended v1 architecture
2. final proposed repository layout
3. responsibility boundaries
4. Local Coder state machine
5. Qwen action/tool protocol
6. implementation packet schema
7. handoff report schema
8. task memory schema
9. retry / rework policy
10. failure handling / rollback policy
11. security and file-scope enforcement
12. how existing `safe-edit.py` should be integrated
13. whether to keep Codex CLI for Qwen or call LM Studio directly
14. implementation phases
15. test plan
16. major risks / tradeoffs

Prefer the simplest design that satisfies the target workflow.

After presenting the design, identify the smallest useful implementation milestone for v1.

Do not commit or push unless explicitly requested.
