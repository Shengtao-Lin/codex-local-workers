# codex-local-workers

Experimental, project-local orchestration for delegating bounded Python work
from Codex to models served by LM Studio.

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
  -> optional focused Explorer (gpt-oss)
  -> bounded implementation-unit packet
  -> local Coder (Qwen3-Coder)
  -> deterministic gates + Local Reviewer
  -> risk-routed Codex review and feature integration validation
  -> accept / rework / replan / takeover
```

## Repository layout

- `.local-agents/`: Python runtimes, PowerShell wrappers, protocol, and tests.
- `example/`: small integration example.
- `benchmarks/`: reproducible S5 A/B benchmark harness and aggregate results.
- `docs/design-brief.md`: original architecture brief.
- `docs/improvement-plan-v1.md`: staged implementation and evaluation plan.
- `AGENTS.md`: operating rules for Codex Primary.

## Quick start

Requirements:

- Windows PowerShell
- Python 3.11 or newer
- LM Studio with an OpenAI-compatible local server
- pytest in the target repository's trusted virtual environment

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
  -Task "Trace how configuration reaches request handling."
```

Run a bounded Coder packet:

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

The runtime boundary suite has no third-party dependencies:

```powershell
python -m unittest discover -s .local-agents\tests -v
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

## Status

S0-S5 and the first S6 orchestration layer are implemented. S6 adds
feature/unit risk separation, deterministic diff-quality gates, explicit
read-only scope, inherited rework packets, and a read-only Local Reviewer.
Qwen is the default Reviewer; alternate models should remain shadow evaluation
until benchmark evidence supports routing acceptance through them.
