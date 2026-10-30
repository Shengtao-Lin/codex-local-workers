"""Retain initial offline failure and observations; repair lookup before live."""

from pathlib import Path

import reviewer_fixed_observations as F

B = F.B
old_path = F.BATCH / "observations.json"
old = B.read(old_path)
producer = str(Path(F.__file__))
archived = F.BATCH / "observation-producer-v1.py"
assert B.sha(archived) == old["pins"][producer]
pins = {p: sha for p, sha in old["pins"].items() if p != producer}
pins.update(
    {
        str(archived): B.sha(archived),
        str(old_path): B.sha(old_path),
        producer: B.sha(Path(producer)),
        str(Path(__file__)): B.sha(Path(__file__)),
    }
)
B.save(
    F.SEAL,
    {
        **old,
        "pins": pins,
        "prelive_amendment": "First no-model test found lookup hashed absent paths of unrelated fixture families. Skip absent manifests, then fail closed if none match. Existing observations unchanged; original 12-pass/2-fail XML and producer retained. No live call preceded this fix.",
    },
)
