# codex-local-workers

Experimental, project-local orchestration for delegating bounded Python work
from Codex to models served by LM Studio.

Codex remains the Primary Agent: it owns user intent, architecture, scope, Git
operations, review, broader validation, and final acceptance. The local
Explorer performs read-only repository investigation. The local Coder receives
a schema-version-2 implementation packet and can only use bounded read, search,
edit, and validation actions implemented by the runtime.

## Why this exists

The goal is to reduce Codex usage without weakening the final quality gate.
Worker output is never accepted on trust: the repository diff and independently
observed tests remain authoritative.

```text
Codex Primary
  -> optional focused Explorer (gpt-oss)
  -> bounded implementation packet
  -> local Coder (Qwen3-Coder)
  -> Codex diff review and broader validation
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
it only with trusted local repositories and review every resulting diff.

## Status

S0-S4 of the improvement plan are implemented. The initial S5 quality baseline
is complete: both direct Primary and local-Coder workflows reached 10/10 final
acceptance, but the original local-Coder run required substantial rework and
the experiment did not expose exact Codex token usage. See
[`benchmarks/S5-RESULTS.md`](benchmarks/S5-RESULTS.md) before drawing efficiency
conclusions or starting optional S6 reviewer experiments.
