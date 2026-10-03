# Model configuration

Set model identifiers and role settings in `.local-agents/config.json` after
copying the example configuration. Each role may use a different installed
model; Coordinator and Reviewer may use the same weights with fresh contexts.

| Role | Example model | Configured context |
| --- | --- | --- |
| Explorer | `openai/gpt-oss-20b` | 32768 |
| Coder | `qwen/qwen3-coder-30b` | 24576 |
| Reviewer | `meta/muse-glimmer` | 24576 |
| Coordinator (opt-in) | `meta/muse-glimmer` | 24576 |

These are validated defaults, not requirements for the role contract. Actual
success depends on the model, quantization, chat template, server and settings.
Comparable general capability does not establish equivalent tool or review quality.

## Replacing a model

1. Set the role's model ID and context length to an installed model. Keep
   `single_model_residency: true` when GPU memory is constrained.
2. Match the role's transport to the model: JSON actions or native Reviewer
   tools, output budget and supported reasoning/sampling settings.
   `coordinator_reasoning_strength` and `reviewer_reasoning_strength` are prompt instructions for templates that
   recognize it; omit it for models that do not use that instruction.
3. In the source kit, run `python benchmarks/role_compat.py --config <config>`
   with the benchmark dependencies available. Qualify the actual mode; the
   supervised Coordinator uses Explorer `locate` mode.
4. Check role quality on fixed tasks: relevant source/test evidence for Explorer,
   actual edits and protected validation for Coder, hidden defects and a clean
   control for Reviewer, legal proposals and transitions for Coordinator.

Change one role at a time. Retain the old configuration and results for comparison.
Missing action coverage is incomplete qualification, even when one task passes.

The runtime owns scope, validation, state transitions and acceptance boundaries.
Changing a model never grants additional tools, weakens a contract or changes
Primary's review obligations. Currently the service integration is LM Studio;
model replacement does not imply arbitrary provider compatibility.
