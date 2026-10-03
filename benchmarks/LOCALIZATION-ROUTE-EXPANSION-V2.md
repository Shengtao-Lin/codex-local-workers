# Restricted localization route: additional frozen cells

Status: **observational expansion, not a v2.1 release gate**. Each row is a separate unknown-implementation-path snapshot using question version 2 and the configured OSS Explorer, Qwen Coder, and Muse Reviewer. The original five-type pilot remains unchanged; these results do not form a preregistered two-round cohort with it.

| Case | Snapshot | Explorer | First Coder call | Reviewer | Independent pytest/Ruff | Primary |
| --- | --- | --- | --- | --- | --- | --- |
| `selection-random-seed` | `route-unknown-fe704d7c593c` | valid | ready | pass | pass | accept |
| `metadata-key-length` | `route-unknown-32758d44e5b0` | valid | ready | pass | pass | accept |
| `selection-percentage` | `route-unknown-2bd82e13793a` | valid | ready | pass | pass | accept |

The first two cells were run before the provenance-manifest change and are summarized separately as 2/2 Explorer, Coder, Reviewer, and independent first-pass E2E with zero explicit infrastructure failures. Primary inspected their actual one-line diffs and recorded immutable acceptance: the random strategy now uses seed zero rather than a fallback, and metadata keys use the contract's 128-character bound. These are two distinct behavior types, not two rounds of one type.

The third cell exercised the new manifest path. Its `route-result.json` records the kit runtime and role-config fingerprint, Python version, case-input fingerprint, and an unchanged-runtime check. `localization_route_summary.py --require-frozen-manifest` accepted that single cell; Explorer, Coder, Reviewer, independent tests/Ruff, and Primary review also passed. The actual diff changed the percentage threshold multiplier from 10 to 100, matching the protected 10,000-bucket assertions. One manifest-qualified cell is only a plumbing check, not a comparative baseline.

Future candidate cohorts must use `--require-frozen-manifest`, the same runtime fingerprint across all cells, and the same case-input fingerprint for each case across rounds. The manifest protects against accidental code/config/input mixing; it does **not** authenticate LM Studio model weights behind an unchanged model ID or replace source/diff review. At least 11 distinct types in two rounds and separate Reviewer hidden-defect coverage remain outstanding before a broader gate decision.
