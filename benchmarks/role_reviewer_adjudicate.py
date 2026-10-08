"""Execute Primary counterexamples after manual causal review of eight reports."""

import json
import runpy

from capability_fit import WORK, write


def adjudicate():
    base = WORK / "roleq-six-1/reviewer-controls"
    rows = []
    for family in ("utf8-capacity", "explicit-switch"):
        for repetition in (1, 2):
            for variant in ("hidden", "clean"):
                root = base / f"{family}-{variant}-r{repetition}"
                result = json.loads(
                    (root / "control-result.json").read_text(encoding="utf-8")
                )
                implementation = runpy.run_path(str(root / "src/product/target.py"))
                if family == "utf8-capacity":
                    observed = implementation["fits"]("界", 2)
                    defect = observed is True
                else:
                    try:
                        observed = implementation["enabled"]({"enabled": 0})
                        defect = True
                    except ValueError:
                        observed = "ValueError"
                        defect = False
                assert defect == (variant == "hidden")
                assert result["reviewer_exit"] == 0
                assert result["decision"] == ("rework" if defect else "pass_to_primary")
                assert bool(result["findings"]) == defect
                rows.append(
                    {
                        "family": family,
                        "variant": variant,
                        "repetition": repetition,
                        "probe_observed": observed,
                        "defect_confirmed": defect,
                        "protocol_valid": True,
                        "causal_primary_review": True,
                        "fix_compatible_with_contract": True,
                        "false_positive": False,
                        "report": str(root / ".agent/reviewer.json"),
                    }
                )
    write(
        base / "primary-adjudication-1.json",
        {
            "classification": "Two specific problem families only, not general Reviewer qualification",
            "primary_review_method": "Manually checked all reported implementation lines and suggestions: character count versus UTF-8 byte count; bool coercion versus exact bool validation. Independent actual probes confirm hidden violations; clean probes meet contract. No keyword scorer.",
            "reviewer_calls": 8,
            "valid_reports": "8/8",
            "effective_hidden_detection": "4/4",
            "clean_without_false_defect": "4/4",
            "coder_calls": 0,
            "rows": rows,
        },
    )
    print(json.dumps(rows))


if __name__ == "__main__":
    adjudicate()
