# Configuration templates

These four JSON files preserve the exact supported profile settings from the
tested setup candidate. Their machine paths and project checks are examples,
not portable defaults. The project setup tool replaces connection paths,
counter bindings and the Primary-reviewed check map, and qualifies the result
before emitting READY. Do not copy old tokenizer hashes into an active config.

The release builder reads these versioned inputs directly; no benchmark archive
or ignored working directory is needed to reproduce a bundle. Profile changes
require their own review and qualification; do not mix optional permissions.
