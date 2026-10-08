"""Read-only language micro-controls, not agent qualification or model switching."""

import argparse
import json
from pathlib import Path

from capability_fit import WORK, load_worker, write
from inherited_context_recovery import digest, read

BASE = WORK / "roleq-semantic-floor-1"
SNAPSHOT = WORK / "roleq-native-wire-candidate-1"
QUESTIONS = [
    {
        "id": "exact-type",
        "question": "In Python 3: class Child(int): pass. For each x in [2, True, Child(2)], give the boolean value of type(x) is int. Return only the three-element JSON array.",
        "expected": [True, False, False],
    },
    {
        "id": "inheritance",
        "question": "In Python 3: class Child(int): pass. For each x in [2, True, Child(2)], give the boolean value of isinstance(x, int). Return only the three-element JSON array.",
        "expected": [True, True, True],
    },
    {
        "id": "missing-null-zero",
        "question": "In Python 3 evaluate c.get('v', 1000) for each c in [{}, {'v': None}, {'v': 0}]. Return only the three-element JSON array, with Python None represented as JSON null.",
        "expected": [1000, None, 0],
    },
]


def run():
    BASE.mkdir(exist_ok=False)
    worker = load_worker(SNAPSHOT)
    config = read(SNAPSHOT / ".local-agents/config.json")
    for relative, sha in read(SNAPSHOT / "freeze.json")["files"].items():
        if digest(SNAPSHOT / relative) != sha:
            raise ValueError("snapshot drift")
    write(
        BASE / "manifest.json",
        {
            "feature_id": "semantic-floor-control",
            "feature_risk": "small",
            "unit_risk": "small",
            "integration_risk": "medium",
            "risk_rationale": "Read-only final-answer micro-controls, no repository dispatch; cannot authorize integration",
            "questions": QUESTIONS,
            "calls_max": 3,
            "retries": 0,
            "classification": "Tiny full-information language facts, no role or qualification credit; not evidence of general capability",
            "model": config["coder_model"],
            "snapshot": str(SNAPSHOT),
            "driver_sha256": digest(Path(__file__)),
            "coordinator_started": False,
            "weekly_used_ceiling": 60,
        },
    )
    client = worker.LMStudioClient(
        config["lmstudio_base_url"],
        config["coder_model"],
        config["model_request_timeout_seconds"],
        max_tokens=256,
        temperature=config["coder_temperature"],
        top_p=config["coder_top_p"],
        top_k=config["coder_top_k"],
        min_p=config["coder_min_p"],
        repeat_penalty=config["coder_repeat_penalty"],
        structured_output=False,
        context_length=config["coder_context_length"],
    )
    with worker.MODEL_RESIDENCY.role_model_lease(client, config):
        for question in QUESTIONS:
            result = {"id": question["id"], "correct": False}
            try:
                raw = client.complete(
                    [
                        {
                            "role": "system",
                            "content": "Answer the Python question accurately. Return only the requested JSON array, no prose or Markdown.",
                        },
                        {"role": "user", "content": question["question"]},
                    ]
                )
                result["final_answer"] = raw
                parsed = json.loads(raw)
                # JSON comparison also distinguishes true from 1 and false from 0.
                result["correct"] = json.dumps(parsed) == json.dumps(
                    question["expected"]
                )
            except (ValueError, worker.WorkerError) as error:
                result["error"] = str(error)
            result["request_stats"] = client.last_request_stats
            write(BASE / (question["id"] + ".json"), result)
            print(json.dumps(result), flush=True)


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    run()
