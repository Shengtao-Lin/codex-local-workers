"""Focused offline applicability controls, not model or semantic qualification."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))
import harness_protocol as old
import preserved_import_guard as candidate

HISTORY = ROOT / "benchmarks/work/harness-convergence/unified-transfer-20261018-1"
TOPICS = {
    "request_keys": ("src/product/request_keys.py", "request_hash"),
    "single_content": ("src/evaluation_harness/adapters/common.py", "parse_message"),
}


@pytest.mark.parametrize("topic", TOPICS)
def test_frozen_normal_task_current_guard_rejects_even_unchanged_source(topic):
    path, symbol = TOPICS[topic]
    source = (HISTORY / "fixtures" / topic / path).read_text(encoding="utf-8-sig")
    with pytest.raises(ValueError, match="import|Import"):
        old.guard(source, source, symbol, old.IMPORT_CEILING)


@pytest.mark.parametrize("topic", TOPICS)
def test_prototype_preserves_baseline_and_accepts_frozen_reference_body(topic):
    path, symbol = TOPICS[topic]
    source = (HISTORY / "fixtures" / topic / path).read_text(encoding="utf-8-sig")
    reference = (HISTORY / "private" / topic / "reference.py").read_text(
        encoding="utf-8-sig"
    )
    candidate.guard(source, source, symbol, set())
    candidate.guard(source, reference, symbol, set())
    # References stay offline. A passing guard is not a passing implementation.


BASE = "import hashlib\nfrom typing import Any\n\nVALUE = 1\n\ndef target(x: Any):\n    return x\n"


@pytest.mark.parametrize(
    "proposed",
    [
        BASE.replace("import hashlib", "import os"),
        BASE.replace("import hashlib", "import hashlib as other"),
        BASE.replace("import hashlib\n", ""),
        BASE.replace("from typing import Any", "from typing import Any, Literal"),
        BASE.replace("VALUE = 1", "VALUE = 2"),
        BASE.replace("target(x: Any)", "target(x: Any, y=None)"),
        BASE.replace("    return x", "    import os\n    return x"),
        BASE.replace("    return x", "    from typing import cast\n    return x"),
        BASE + "\nimport os\n",
        BASE + "\n# type: ignore\n",
    ],
)
def test_no_new_import_or_other_authority(proposed):
    with pytest.raises(ValueError):
        candidate.guard(BASE, proposed, "target", old.IMPORT_CEILING)


def test_existing_local_import_frozen_not_rejected():
    source = BASE.replace("    return x", "    import math\n    return math.floor(x)")
    candidate.guard(source, source.replace("floor(x)", "ceil(x)"), "target", set())
    with pytest.raises(ValueError):
        candidate.guard(
            source, source.replace("import math", "import os"), "target", set()
        )


def test_only_old_approved_additions_and_removals():
    proposed = BASE.replace("from typing import Any", "from typing import Any, cast")
    candidate.guard(BASE, proposed, "target", old.IMPORT_CEILING)
    candidate.guard(proposed, BASE, "target", old.IMPORT_CEILING)
    with pytest.raises(ValueError):
        candidate.guard(BASE, proposed, "target", set())
    with pytest.raises(ValueError, match="ceiling"):
        candidate.guard(BASE, BASE, "target", {("os", "system", None)})
