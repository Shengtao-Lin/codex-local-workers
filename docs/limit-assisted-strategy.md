# Primary-reviewed selection strategy for one assisted-mode trial

This is advisory algorithm guidance, not an executable patch or a new hard
contract. The five existing limit contracts, protected tests, scopes and risk
remain authoritative. Coder may use a different in-scope implementation satisfying
them. This experiment measures assisted implementation, not autonomous algorithm
selection, and starts from the unchanged correct legacy implementation.

1. Keep all/random/percentage code and SelectionPolicy unchanged. For limit,
   first materialize each original occurrence's timestamp then identity, once,
   in input order. Finish this complete key pass before doing any ordering
   comparison. Do not catch or wrap callback exceptions.
2. Give every occurrence its original position during that pass; do not recover
   positions with list.index or payload equality. A comparable selection key is
   (timestamp, identity, original_position); keep the original payload separate
   from the comparison key. Build a consistently shaped decorated collection
   once rather than mutating a three-field tuple collection into four fields.
3. Use a trusted standard-library bounded selection helper rather than a new
   custom heap implementation: heapq.nsmallest for oldest and heapq.nlargest for
   newest, supplying only the comparable selection key. Return a new list of
   the selected original payloads in helper-result order. This is a suggested
   algorithm, not a required source layout or edit sequence.
4. The key uses the same positive original position in both directions. For
   oldest, ascending selection chooses earlier equal-key occurrences. For
   newest, descending selection chooses later equal-key occurrences, matching
   legacy sorted-then-reverse. No timestamp/string negation, post-selection
   reverse that changes tie semantics, or payload comparison is needed. Keep
   every occurrence, including repeated references to the same object.
5. Empty input yields a fresh empty list. Limits covering all items still need
   the correct complete ascending/descending order; the library helpers already
   support that. Preserve existing timezone/datetime and arbitrary string keys.
   Use the existing validated limit-policy invariant to narrow Optional[int]
   safely for static typing; do not suppress strict checks or change validation.
6. Small-k work is bounded selection on precomputed keys; key materialization
   may remain linear. Run the unchanged focused tests, then respond to the exact
   current failure/rule/location with a real minimal correction. Keep tuple
   construction, key extraction and payload extraction consistent. Formatting
   and strict typing are acceptance requirements, not optional follow-up work.

Primary checked this reasoning against the real legacy source, SelectionPolicy
validation, the public dataset caller and the existing acceptance tests:
positive position establishes the exact stable/reverse-stable tie order; the
precomputation pass preserves callback side effects and exception identity;
key-only selection excludes payload comparison; enumerated positions remove
quadratic equality scans. No source implementation or expected patch is supplied.
