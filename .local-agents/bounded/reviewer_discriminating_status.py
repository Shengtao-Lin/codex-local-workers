import copy
from . import reviewer_contract_status_probe as P

TOOLS = copy.deepcopy(P.TOOLS)
ARRAY = TOOLS[0]["function"]["parameters"]["properties"]["predictions"]
ARRAY["minItems"] = ARRAY["maxItems"] = 8
ARRAY["items"]["properties"]["case_index"]["maximum"] = 7
TOOLS[0]["function"]["description"] = (
    "Predict contractual terminal status of target_call_id for each provided sequence, not current implementation behavior."
)
