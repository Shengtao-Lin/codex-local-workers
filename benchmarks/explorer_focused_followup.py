"""Probe bounded follow-up Explorer questions after the frozen first-call audit."""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

import stability_e2e as STABILITY

QUESTIONS = {
    "sample-identity": (
        (
            "fingerprint",
            (
                "READ_FILE src/evaluation_harness/canonical/models.py and READ_FILE "
                "src/evaluation_harness/canonical/fingerprint.py and READ_FILE "
                "tests/test_sample_identity.py. Answer only this: for changing "
                "sample_id, labels, or source_metadata, what does the current "
                "content_fingerprint actually hash and which focused fingerprint "
                "assertions disagree? Determine whether the existing volatile-field "
                "constant is used. Cite observed source and test paths with lines, "
                "put tests/test_sample_identity.py in relevant_tests, then FINISH_SUCCESS."
            ),
        ),
        (
            "reuse-key",
            (
                "READ_FILE src/evaluation_harness/canonical/models.py and READ_FILE "
                "src/evaluation_harness/evaluations/dedup.py and READ_FILE "
                "tests/test_sample_identity.py. Answer only this: for changing "
                "sample_id, labels, source_metadata, or only effective_config key "
                "order, what does the current score_reuse_key hash and which focused "
                "reuse-key assertions disagree or agree? Keep sample row identity "
                "distinct from scoring inputs. Cite observed source and test paths "
                "with lines, put tests/test_sample_identity.py in relevant_tests, "
                "then FINISH_SUCCESS."
            ),
        ),
    ),
    "metadata-key-length": (
        (
            "key-boundary",
            (
                "READ_FILE src/agent_runtime/models.py and READ_FILE "
                "tests/test_metadata_key_length.py. Answer only this: substitute "
                "the test's 128-character, 129-character, and empty keys into the "
                "actual numeric key guard and then the encoded-byte guard. For each, "
                "what return or exception/message follows, and which assertion "
                "agrees or conflicts? Do not infer the threshold from the error text. "
                "Cite source/test paths with lines, include the test in relevant_tests, "
                "then FINISH_SUCCESS."
            ),
        ),
    ),
    "mapping-message-sequence": (
        (
            "container-exceptions",
            (
                "READ_FILE src/agent_runtime/adapters/mapping.py and READ_FILE "
                "tests/test_mapping_message_sequence.py. Answer only this: for the "
                "test's str, bytes, and int messages containers, does each pass the "
                "Sequence guard, and what exact exception follows from subsequent "
                "Message.model_validate if the guard passes? Compare to the asserted "
                "TypeError; also distinguish the invalid-list-element assertion. "
                "Cite source/test paths with lines, include the test in relevant_tests, "
                "then FINISH_SUCCESS."
            ),
        ),
    ),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--output-dir", type=Path, default=STABILITY.WORK)
    args = parser.parse_args()
    if not 1 <= args.rounds <= 3:
        parser.error("rounds must be between 1 and 3")
    source_config = json.loads(
        (STABILITY.KIT / ".local-agents/config.json").read_text(encoding="utf-8-sig")
    )
    batch = (
        args.output_dir.resolve() / f"explorer-focused-followup-{uuid.uuid4().hex[:12]}"
    )
    results: list[dict] = []
    cases = {case.name: case for case in STABILITY.CASES}
    for round_number in range(1, args.rounds + 1):
        for case_name, questions in QUESTIONS.items():
            root = batch / f"round-{round_number}" / case_name
            config_path, _ = STABILITY.prepare(cases[case_name], root, source_config)
            for question_id, task in questions:
                report_path = root / ".agent" / f"explorer-{question_id}.json"
                started = time.perf_counter()
                completed = STABILITY.run_command(
                    root,
                    [
                        sys.executable,
                        str(root / ".local-agents/local-explore.py"),
                        "--task",
                        task,
                        "--task-id",
                        f"stability-{case_name}",
                        "--config",
                        str(config_path),
                        "--report",
                        str(report_path),
                    ],
                    650,
                )
                report = (
                    json.loads(report_path.read_text(encoding="utf-8"))
                    if report_path.is_file()
                    else {}
                )
                result = {
                    "round": round_number,
                    "case": case_name,
                    "question": question_id,
                    "workspace": str(root),
                    "report": str(report_path),
                    "exit_code": completed.returncode,
                    "status": report.get("status"),
                    "failure_reason": report.get("failure_reason"),
                    "infra_failure": report.get("infra_failure"),
                    "wall_seconds": round(time.perf_counter() - started, 2),
                    "semantic_review_required": True,
                }
                results.append(result)
                STABILITY.write_json(batch / "summary.json", {"results": results})
                print(json.dumps(result, ensure_ascii=False), flush=True)
    print(str(batch), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
