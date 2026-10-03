# Cost and latency

Evaluate cost per **accepted task**, including failed attempts, repairs and
Primary review. Local inference uses your hardware; Codex usage belongs to the
cloud Primary. Local token counts cannot be used as Codex token savings.

The current supervised workflow was tested on three paired frozen tasks. Both
routes passed independent review. The Coordinator route used 190635 local
tokens versus 251578 for the direct route, with zero versus three local Coder
repairs. It took 481.188 seconds versus 209.626 seconds, including preparation,
model switches and validation, excluding later Primary review.

These observations describe those tasks and settings. Cloud usage savings and
human review time were not measured. Previously reviewed source/test reuse also
affects file-open counts. The results do not establish production cost savings.

Coordinator inference accounted for 225.233 seconds (46.8%) of that route's
total. The optional `coordinator_reasoning_strength` prompt setting lets you
try a shorter reasoning profile without changing execution authority. The
example configuration uses `low`; omit it for the previous prompt behavior.
Models may interpret or ignore this instruction differently.

A later single paired seed-selection task with this profile completed in
105.781 seconds with coordination and 104.000 seconds without it. Both were
independently accepted; Coordinator inference took 20.579 seconds. This is a
smoke observation, not a replacement for the three-task baseline or proof of
cloud-cost savings. Qualify the setting with your own model and tasks.

## Choosing your tradeoff

Use direct scoped execution when the source and contract are already clear.
Try supervised coordination when execution proposals or dependencies would
otherwise require repeated Primary work. Keep Primary review proportional to risk.

Record these values for a real comparison:

- attributable Codex input, cached input and output tokens, when available;
- Primary packet preparation, intervention and review work;
- local preparation, loading/switching, inference and validation time;
- accepted outcome, rework, escalation and takeover.

Account-wide usage percentages are a budget stop signal, not precise per-task
token attribution. Unknown cloud usage or stage timing stays unknown. Preserve
the configured input context and sufficient output budget when optimizing; a
smaller prompt is useful only if the worker still receives its full obligations.

Run one local model at a time for constrained GPU memory. Wait on the existing
process until it completes. A slow model load or observation timeout does not
justify launching another copy of the same task.
