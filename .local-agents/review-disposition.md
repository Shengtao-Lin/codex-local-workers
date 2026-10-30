# Confirming Reviewer findings

Reviewer recommendations do not authorize another Coder call. Primary inspects
the report and actual source/tests, then records each finding's disposition.
Use the canonical `.agent/tasks/<task>/reviews/<review>/handoff.json`, not a
convenience last-report pointer. Compute its SHA-256 after it is complete.

Example Primary-authored JSON (replace identities, hash and evidence):

```json
{
  "schema_version": 1,
  "authority": "primary",
  "identity": {"task_id": "task", "unit_id": "unit", "run_id": "run", "review_id": "review"},
  "report_sha256": "<canonical handoff SHA-256>",
  "resolution": "cleared",
  "evidence": ["Inspected source path/lines and independently observed relevant checks."],
  "findings": [
    {"finding_id": "F1", "disposition": "confirmed_defect", "evidence": "Concrete input, expected result, actual result and causal source."}
  ]
}
```

Finding types: `confirmed_defect`, `required_test_gap`, `nonblocking`,
`contract_revision`, `unresolved`. Include every finding exactly once. Empty
findings are appropriate only if the report has no findings. Overall resolution
is `cleared`, `contract_revision` or `unresolved`; unclear contracts/evidence
require Primary replan even when there are no findings. Missing tests block
only for explicit requirements or unresolved material risk, not solely because
the model prefers more assertions. Protected test changes require Primary scope
handling; a test-gap verdict never grants Coder extra writable paths.

```powershell
python .local-agents/record-review.py --repo . --task-id task --run-id run `
  --decision rework --summary "Primary confirmed F1" `
  --disposition .agent/primary-disposition.json
```

The immutable run `review.json` retains the disposition, exact report hash and
raw Reviewer recommendation. Changed read-source hashes or missing/stale/foreign
findings fail closed. Contract revision or unresolved evidence cannot authorize
rework. Primary may conservatively replan/take over instead of repairing.
Inherited rework also checks the parent's immutable Primary decision, report hash
and confirmed finding IDs before Coder starts; its review_feedback must cite those
IDs. Ordinary Coder validation-error repairs are not blocked by this Reviewer rule.

`primary_decision: accept` from the disposition helper means no confirmed blocker
remains and Primary review is next; it is not acceptance. Existing deterministic
validation, independent Reviewer pass and risk-routed Primary review still apply.
A false-positive dismissal cannot waive those gates. These files are trusted
Primary inputs, not an authentication mechanism or a semantic proof.
