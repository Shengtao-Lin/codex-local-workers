from . import reviewer_semantic_greedy as BASE

MAPPING = {
    "satisfied": "consistent",
    "implementation_defect": "implementation_defect",
    "required_test_gap": "required_test_gap",
    "contract_conflict": "contract_conflict",
    "uncertain": "insufficient_evidence",
}
PROTOCOL = "reviewer-canonical-policy-v1"


def definitions(prompt, error):
    original = {}
    for line in prompt.splitlines():
        if line.startswith("- ") and ": " in line:
            key, value = line[2:].split(": ", 1)
            original[key] = value
    if not set(MAPPING.values()) | {"optional_test_gap"} <= set(original):
        raise error("canonical Reviewer issue definitions missing")
    result = {
        target: original[source].replace("unverified_claims", "uncertainties with contract_id=null")
        for target, source in MAPPING.items()
    }
    result["satisfied"] += " Optional advice: " + original["optional_test_gap"].replace(
        "unverified_claims", "uncertainties with contract_id=null"
    )
    return result


def install(module):
    base = BASE.install(module)

    class PolicyReviewer(base):
        def bundle(self):
            result = super().bundle()
            result["verdict_definitions"] = definitions(self.system_prompt(), module.ReviewError)
            return result

        def validate_report(self, args):
            report = super().validate_report(args)
            report["semantic_policy_protocol"] = PROTOCOL
            report["semantic_policy_provenance"] = (
                "Canonical definitions from this frozen original Reviewer system_prompt; enum names/uncertainty field mechanically adapted, no case-specific policy."
            )
            return report

    module.ReviewerRuntime = PolicyReviewer
    return PolicyReviewer
