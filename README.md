# codex-local-workers

Run scoped Python coding tasks with local LM Studio models while Codex handles
planning, review and final acceptance.

Codex remains the Primary Agent: it owns user intent, architecture, scope, Git
operations, review, broader validation, and final acceptance. The local
Explorer performs read-only repository investigation. The local Coder receives
a schema-version-2 implementation packet and can only use bounded read, search,
edit, and validation actions implemented by the runtime. A separate read-only
Local Reviewer examines actual diffs and runtime evidence before risk-routed
Primary review.

## Why this exists

The goal is to reduce Codex usage without weakening the final quality gate.
Worker output is never accepted on trust: the repository diff and independently
observed tests remain authoritative.

```text
Codex Primary
  -> feature decomposition + feature/unit/integration risk
  -> optional focused Explorer
  -> bounded implementation-unit packet
  -> local Coder
  -> deterministic gates + Local Reviewer
  -> risk-routed Codex review and feature integration validation
  -> accept / rework / replan / takeover
```

## What you can use

- Explorer locates source and tests with file/line evidence.
- Coder reads, searches, edits authorized files and runs configured validation.
- Reviewer independently checks the actual diff and can run registered tests
  and static checks in a fresh context.
- Optional Coordinator prepares bounded execution proposals for an approved
  feature. Each step requires Primary authorization; completion returns to
  Primary for acceptance.

The default configuration uses OSS Explorer, Qwen Coder and Muse Reviewer;
the optional Coordinator also uses Muse in an independent context. Model IDs
are configuration values. A replacement model must pass the relevant role's
protocol and quality checks. See [model configuration](docs/models.md).

## Quick start

Requirements:

- Windows PowerShell
- Python 3.11 or newer
- LM Studio with an OpenAI-compatible local server
- pytest in the target repository's trusted virtual environment

To install into another repository, preview the file list first. The installer
copies only project-local runtime files and `AGENTS.md`; it never copies
`config.json`, `.agent` logs, or kit-only benchmark tests, and refuses to overwrite a
different existing file (including an existing `AGENTS.md`).

```powershell
python scripts/install_local_agents.py --target F:\path\to\target-repo
python scripts/install_local_agents.py --target F:\path\to\target-repo --apply
```

Review any conflicts and merge them manually. A `legacy_kit_tests` entry means
an older kit-only test remains in the target; the installer reports but never
deletes it. After checking its content, remove or relocate that stale copy so
target self-tests can collect cleanly. The target's local configuration must be
created or updated separately; do not replace an existing one.

Create the local configuration:

```powershell
Copy-Item .local-agents\config.example.json .local-agents\config.json
```

Adjust the LM Studio URL, model identifiers, and Python interpreter in
`.local-agents/config.json`. The default example expects the API at
`http://127.0.0.1:12345/v1`.

Run a focused read-only exploration:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File ".local-agents\local-explore.ps1" `
  -Task "Locate the configuration loader and its tests." `
  -TaskId "configuration-loader"
```

Run a bounded Coder packet with automatic handoff to read-only Reviewer:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File ".local-agents\local-unit.ps1" `
  -Packet ".agent\implementation-packet.json"
```

For diagnostic manual routing, run Coder directly:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File ".local-agents\local-code.ps1" `
  -Packet ".agent\implementation-packet.json" `
  -Report ".agent\last-local-coder-report.json"
```

Review a completed Coder run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File ".local-agents\local-review.ps1" `
  -Request ".agent\review-request.json" `
  -Report ".agent\last-local-review-report.json"
```

See [the local-agent guide](.local-agents/README.md) for the packet contract,
review flow, security boundary, and exit statuses.

## Tests

Most runtime tests use only the standard library; the real-HTTP end-to-end test
uses pytest and skips if the selected interpreter lacks it:

```powershell
python -m unittest discover -s .local-agents\tests -v
```

The source kit also has integration and installer tests that are not copied to
targets:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

The integration example uses pytest:

```powershell
Push-Location example
python -m pytest tests -q
Pop-Location
```

## Security boundary

The Coder edit allowlist is enforced by the runtime, but validation executes
trusted repository code with the Python process's real host permissions. This
is orchestration and write-scope control, not an operating-system sandbox. Use
it only with trusted local repositories. Review depth follows explicit unit
risk, and high-risk feature integration always receives final Primary review.

## Choosing a workflow

Use the direct Coder-to-Reviewer workflow for a known, scoped change. Use
Explorer when source or tests need locating. The opt-in supervised Coordinator
supports localization tasks and dependency-aware proposals; general autonomous
investigation and unattended execution have not been qualified.

Local execution can take several minutes. The kit runs one local model at a
time and preserves failed attempts for review. Compare cloud usage and local
waiting time together: local model tokens are different from Codex usage.
Measured Codex savings have not yet been established.

See [cost and latency](docs/cost-and-latency.md),
[release notes](docs/release-notes.md), [the runtime guide](.local-agents/README.md),
and the [worked example](example/README.md).
The development branch contains engineering plans and historical evaluations.
