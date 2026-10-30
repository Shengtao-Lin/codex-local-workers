import copy
from . import reviewer_semantic_entry as V1

PROTOCOL = "complete-observation-accounting-v1"
TOOLS = copy.deepcopy(V1.TOOLS)
PARAMS = TOOLS[0]["function"]["parameters"]
PARAMS["required"].append("observation_assessments")
PARAMS["properties"]["observation_assessments"] = {
    "type": "array",
    "description": "One explicit semantic judgment for EVERY supplied approved observation, in profile/example order. Actual outcomes are not expected results. Explain the relation to the owned contract; observations are not newly added project tests.",
    "items": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "profile_id": {"type": "string"},
            "case_index": {"type": "integer", "minimum": 0},
            "contract_id": {"type": "string"},
            "verdict": {
                "type": "string",
                "enum": ["consistent", "violation", "outside_contract", "uncertain"],
            },
            "explanation": {"type": "string", "minLength": 1},
        },
        "required": ["profile_id", "case_index", "contract_id", "verdict", "explanation"],
    },
}


def validate_accounting(rows, expected, contract_review, error):
    if not isinstance(rows, list) or len(rows) != len(expected):
        raise error(
            "observation_assessments must account for every supplied profile/example exactly once in input order"
        )
    statuses = {r["obligation_id"]: r["status"] for r in contract_review}
    for item, identity in zip(rows, expected, strict=True):
        if not isinstance(item, dict) or set(item) != {
            "profile_id",
            "case_index",
            "contract_id",
            "verdict",
            "explanation",
        }:
            raise error(
                "observation assessment requires exact profile_id/case_index/contract_id/verdict/explanation fields"
            )
        if (
            type(item["case_index"]) is not int
            or (item["profile_id"], item["case_index"]) != identity
        ):
            raise error(
                "observation identity missing, duplicated or out of order: " + str(identity)
            )
        if (
            item["contract_id"] not in statuses
            or item["verdict"] not in {"consistent", "violation", "outside_contract", "uncertain"}
            or (not isinstance(item["explanation"], str))
            or (not item["explanation"].strip())
        ):
            raise error("invalid observation contract/verdict/explanation")
        if (
            item["verdict"] in {"violation", "uncertain"}
            and statuses[item["contract_id"]] == "verified"
        ):
            raise error(
                "verified obligation contradicts model's own "
                + item["verdict"]
                + " observation judgment; reconcile explicit judgments using unchanged evidence"
            )
    return copy.deepcopy(rows)
