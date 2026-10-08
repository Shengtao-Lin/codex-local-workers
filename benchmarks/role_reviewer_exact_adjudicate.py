"""Primary-adjudicated known exact-type controls; no keyword or model self-score."""

import json
import runpy

from capability_fit import WORK, write


class IntChild(int):
    pass


def adjudicate():
    base = WORK / "roleq-six-1/reviewer-controls"
    rows = []
    for mode in ("low", "high", "focused"):
        for repetition in (1, 2):
            for variant in ("hidden", "clean"):
                root = base / f"window-groups-{variant}-r{repetition}-{mode}"
                result = json.loads(
                    (root / "control-result.json").read_text(encoding="utf-8")
                )
                function = runpy.run_path(str(root / "src/product/target.py"))["groups"]
                try:
                    observed = function([], IntChild(2))
                    defect = True
                except ValueError:
                    observed, defect = "ValueError", False
                assert defect == (variant == "hidden")
                # Manual report review: ordinary hidden passes miss; high r2's
                # redundant-check diagnosis/fix is wrong. Focused r2 detects but
                # includes a bool-only alternative that still accepts subclasses.
                causal = variant == "clean" or mode == "focused"
                compatible = variant == "clean" or (
                    mode == "focused" and repetition == 1
                )
                rows.append(
                    {
                        "mode": mode,
                        "repetition": repetition,
                        "variant": variant,
                        "probe_observed": observed,
                        "defect_confirmed": defect,
                        "protocol_valid": result["reviewer_exit"] == 0,
                        "decision": result["decision"],
                        "causal_detection": causal if defect else None,
                        "all_suggested_fixes_compatible": compatible
                        if defect
                        else None,
                        "clean_without_false_defect": result["decision"]
                        == "pass_to_primary"
                        and not result["findings"]
                        if not defect
                        else None,
                        "report": str(root / ".agent/reviewer.json"),
                    }
                )
    write(
        WORK / "roleq-reviewer-exact-adjudication-1.json",
        {
            "classification": "Known family only; focused is guided recovery, low/high are text labels NOT real reasoning-budget control",
            "method": "Primary manually read findings and source citations and checked proposed repairs against exact-int contract; independent subtype probes verify actual defect. No keyword scoring, no automatic acceptance.",
            "ordinary_hidden_effective": "0/4",
            "ordinary_clean_without_false_defect": "4/4",
            "focused_hidden_causal_detection": "2/2",
            "focused_hidden_fully_compatible_suggestions": "1/2",
            "focused_clean_without_false_defect": "2/2",
            "rows": rows,
        },
    )
    print(json.dumps(rows))


if __name__ == "__main__":
    adjudicate()
