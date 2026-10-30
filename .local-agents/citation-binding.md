# Contract-bound implementation citations

For a new Python behavior whose implementation must be reviewed, Primary can add
an `implementation_ref` to the feature contract (or direct packet's
`required_behavior`). This is trusted contract metadata, not a model-authored
source selection:

```json
{
  "id": "sequential-trace-batch",
  "text": "The unchanged business contract",
  "risk_floor": "high",
  "implementation_ref": {
    "path": "src/evaluation_harness/trace_sources/mlflow.py",
    "symbol": "MlflowTraceSource.get_many"
  }
}
```

The symbol can be introduced by the implementation; it need not exist before
Coder starts. The formal entry copies the binding from Primary's approved plan
and rejects its removal, addition or alteration in a worker packet. Paths must
be readable ordinary Python source, not tests, control files or forbidden scope.

Reviewer must select at least one actually displayed, current citation from
that file covering an implementation statement of the uniquely resolved Python
symbol. A test citation may supplement it, but a test-only report, another
symbol, a function header, a comment or a docstring does not satisfy the binding.
This requirement applies whenever the binding is present, at any unit risk.
Missing or ambiguous implementations cannot be reported as verified; an
uncertain assessment may still escalate to Primary.

Existing evidence-ID and legacy citation transports use the same gate. A failed
report gets the required binding and eligible displayed IDs, or a bounded read
location. It never gets an automatically filled verdict. Report and source
freshness, identity, actual validation and Primary review remain required.

Legacy packets without this metadata remain compatible and do **not** establish
contract-to-implementation binding. Use explicit bindings in new high-risk
Python packets. The check proves citation identity and relevance to the named
implementation, not semantic correctness, test adequacy or acceptance. Other
languages need a separately supported binding resolver; do not claim the Python
resolver validates them.
