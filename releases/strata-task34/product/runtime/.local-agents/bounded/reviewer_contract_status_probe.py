SYSTEM = "Predict the terminal status REQUIRED BY THE HARD CONTRACT for each supplied event sequence. Use PREDICT_STATUS. Unreviewed implementation, when present, is context, not the specification. Explain each prediction briefly. Reasoning strength: medium."
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "PREDICT_STATUS",
            "description": "Predict contractual terminal status, not current implementation behavior.",
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "required": ["predictions"],
                "properties": {
                    "predictions": {
                        "type": "array",
                        "minItems": 6,
                        "maxItems": 6,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["case_index", "status", "reason"],
                            "properties": {
                                "case_index": {"type": "integer", "minimum": 0, "maximum": 5},
                                "status": {
                                    "type": "string",
                                    "enum": ["requested", "succeeded", "failed", "unknown"],
                                },
                                "reason": {"type": "string", "minLength": 1, "maxLength": 400},
                            },
                        },
                    }
                },
            },
        },
    }
]
