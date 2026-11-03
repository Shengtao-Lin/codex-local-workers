# Choose one task profile

The JSON files are explicit examples requiring local path/check adaptation.
Do not copy flags between profiles to increase a budget or bypass a rejection.

|Example|Use|Recovery and review|
|---|---|---|
|config.coding.json|Trusted Python implementation and supplemental tests|Initial16requests/4edits, sealed14/4 for one eligible confirmed return; fresh Reviewer; Primary final acceptance|
|config.investigation.json|Standalone source/data evidence and optional approved skill|Complete report to Primary; no semantic resume added after launch|
|config.investigation-followup.json|Investigation with one preselected same-contract evidence follow-up|Shared original10requests/12evidence/16tools/900s; first4 ordinary requests; max8 ordinary overall plus bounded protocol report recovery|
|config.capabilities.json|Explicit public evidence, fixed operation, or single-level readonly child|Own bounded capability ledger; no continuation/compact-report/skill flags copied in|

The capability flag alone grants no tools. The trusted contract must also contain
the appropriate `capabilities` object. Capabilities are optional; the worker
chooses when approved tools help. An explicit independent-child test does not
prove it chooses delegation well for arbitrary tasks.

- Public web: `web: {public_context: true, hosts: [...], entries: {id: httpsURL}}`.
  Public text only, approved HTTPS hosts and observed links, no login/upload/query
  or search engine. Never mix private source/skills into a public-context task.
  Writable implementations reject web. Web+children is rejected.
- Fixed operation: `operations: {"json-summary": ["exact/approved.json"]}`.
  Finite numeric arrays, count/sum/min/max and input hash; not arbitrary scripts,
  shell or exact financial arithmetic. Inputs must be in the approved manifest.
- Single-level child: `children: {read: ["exact/approved.py"]}`.
  At most2 serial readonly children; each max4requests/8tools. Consumption also
  debits the parent. No child network, operations, writes or descendants.

Public-operation capability tasks have10requests/16tools/12evidence/900s.
Readonly parents with children have16requests/24tools/16evidence/1200s; child
calls are included, not added again. Current native loop and host still enforce
context/output/time and no-progress limits. All figures refer to the explicit
profile, not a promise about end-to-end loading or Primary review time.

Only the core coding and ordinary readonly profiles have the recent complete
workflow evidence. Current capability results and package controls are described
in release-evidence.json. Old capability version results do not certify every
combination on this build. Network+write, network+children, continuation+capabilities,
arbitrary execution and deeper recursion remain outside this candidate.

Model/backend: iq3_s on the configured local Strata endpoint, single residency.
Verified client safe context65536/output12288; a resident server advertising a
larger context does not change the client limit. No LM Studio service is required.
