# Set up a trusted project

Primary can complete these steps from the verified release bundle. The user
needs an existing Strata installation and iq3_s model, an existing project Python
environment with its checks, and must start Strata. No model or dependency is
downloaded or started by setup. Currently supported: Windows, trusted Python
projects, unchanged task.34, local Strata, single iq3_s/parallel1. General
cross-machine support and the next release's remote replay are not yet certified.

## Acquire the exact release

Use an explicitly approved tag and SHA256 from the release record, not `latest`.
Primary obtains this script from the reviewed repository/bundle. Verify it before
execution. Checksum verification binds bytes to that chosen release; it does not
establish publisher identity by itself.

```powershell
& $python tools/strata-setup.py fetch --repository Shengtao-Lin/codex-local-workers --tag $tag --asset $asset --sha256 $sha --output $zip
& $python tools/strata-setup.py unpack --archive $zip --sha256 $sha --output $bundle
```

Both operations refuse existing destinations. Unpack checks the complete manifest,
duplicate/case-colliding paths, Windows aliases, path escapes and size limits before
writing. Existing old previews can be downloaded and checked, but are explicitly
rejected by project setup if they lack the supported supervised task runtime.
No implicit upgrade or replacement occurs.

## Map the project's checks once

Primary reads the project's actual pyproject, CI and test instructions, selects
the existing environment, and writes a small JSON mapping. This is trusted setup
data, never a tool offered to the Worker. Do not guess away project requirements.
For nonstandard CI, missing dependencies or ambiguous commands, Primary resolves
the mapping rather than silently dropping checks or installing packages.

```json
{
  "input_roots": ["src", "tests", "pyproject.toml"],
  "focused_tests": ["tests"],
  "commands": [
    {"id":"project-tests","argv":["{python}","-B","-m","pytest","tests","-q","-p","no:cacheprovider","--basetemp=.agent/setup-temp"]},
    {"id":"ruff-check","argv":["{python}","-m","ruff","check","--no-fix","src","tests"]},
    {"id":"ruff-format","argv":["{python}","-m","ruff","format","--check","src","tests"]},
    {"id":"pyright","argv":["{python}","-m","pyright","--pythonpath","{python}"]}
  ]
}
```

This is an example shape, not a replacement for the real project's test selection,
lint/typecheck inputs or integration checks. Non-Python setup is not enabled.

## Install, configure, calibrate

```powershell
& $python "$bundle/tools/strata-setup.py" project --bundle $bundle --project $projectCopy --python $python --checks $checks
```

Setup verifies package hashes before invoking its installer. It discovers Strata
from the existing user's native-instance configuration, or `STRATA_HOME` /
`--strata-home`. Ambiguous/missing locations require Primary to supply the path.
It never scans every disk or changes the Strata installation. Project code and
existing `.local-agents` are not overwritten; an exactly matching installation
can be reused, while any difference requires explicit upgrade review.

Tokenizer discovery uses the existing iq3_s native-instance record, including
nondefault model folders. `--tokenizer-root` is available to Primary for an
ambiguous/missing location; it never moves or downloads the model. The tool
requires the exact tested task.34 runtime and rechecks all encoder pins after
the project baseline before writing READY.

Setup appends one short project AGENTS pointer, preserving its existing bytes and
archiving the preimage. It does not replace project instructions with this kit's
legacy LM Studio rules. Per-attempt artifacts live under `.agent/strata-setup/`.

- `WAITING_FOR_STRATA`: installation/preparation is retained; start iq3_s and
  repeat setup. No model process or load/unload request is issued by setup.
- `READY`: doctor confirmed the right single model, current local pure-counter
  counts matched the resident server on six request shapes, drift negative control
  was rejected, and the full reviewed project baseline passed without changing
  inputs. Use only the returned `config.json`; pending files are unqualified.
- `NEEDS_PRIMARY_ATTENTION`: inspect preserved setup receipts. Missing checks,
  incompatible encoder/template, input drift or a different installation are
  not fixed by deleting bindings, replacing old files or marking READY manually.

Calibration uses the already-resident engine's local count-only endpoint. Existing
local backend credentials stay in memory; they are neither archived nor offered
to Worker tools. Generation remains at the selected local gateway. Installation
updates later require a fresh setup/calibration; old READY records are history,
not proof that today's external files still match. The runtime independently
checks the bindings again before each actual model request.

## Use after setup

Primary reads AGENTS.strata.md and chooses an existing supported profile. Default
setup selects coding; `--profile investigation` preselects its bounded evidence
follow-up. Permissions/skills still require each task's explicit contract.

Copy the READY config into a fresh task request, prepare its scoped contract,
preview/apply/run through installed `.local-agents/strata-task.py`, then perform
independent final acceptance. READY means environment qualified, not task accepted.
No shell, Coordinator, automatic skill loading, recursive permission or budget
expansion is added by installation. The host's checks execute trusted Python
with host permissions; this is not OS isolation.

The install-to-task smoke must be recorded separately from setup READY. Successful
local packaging does not mean an unpublished candidate was downloaded from GitHub.
