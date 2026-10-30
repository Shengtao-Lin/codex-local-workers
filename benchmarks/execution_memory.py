"""Host-observed short-term continuity; never a model-authored success claim."""

import copy
import difflib


class ExecutionMemory:
    def __init__(self):
        self.previous = None
        self.attempts = []

    @staticmethod
    def checks(validation):
        result = {
            str(c["id"]): str(c["status"]) for c in validation.configured_checks or []
        }
        result["focused_tests"] = str(validation.focused_tests.get("status", "unknown"))
        return result

    def observe(self, binding, validation, feedback, ledger):
        current = {
            "request": ledger["requests"],
            "sha256": binding["sha256"],
            "source": binding["source"],
            "checks": self.checks(validation),
            "ledger": dict(ledger),
        }
        old = self.previous
        if old is not None and current["request"] > old["request"]:
            delta = {
                k: ledger[k] - old["ledger"].get(k, 0)
                for k in ("edits", "noops", "protocol_recoveries", "post_edit_checks")
            }
            changes = {
                k: {"before": old["checks"].get(k, "not_observed"), "after": v}
                for k, v in current["checks"].items()
                if old["checks"].get(k) != v
            }
            diff = "\n".join(
                difflib.unified_diff(
                    old["source"].splitlines(),
                    binding["source"].splitlines(),
                    fromfile="previous",
                    tofile="current",
                    n=2,
                )
            )
            self.attempts.append(
                {
                    "request": current["request"],
                    "source_before": old["sha256"],
                    "source_after": binding["sha256"],
                    "observed_counts": delta,
                    "check_status_changes": changes,
                    "diff_excerpt": diff[:2400],
                    "diff_truncated": len(diff) > 2400,
                    "feedback": feedback,
                    "interpretation": "Observed changes only; passing checks or fewer failures do not prove semantic correctness.",
                }
            )
        self.previous = current
        return {
            "origin": "host-observed previous attempts, not additional task requirements",
            "attempts_recorded": len(self.attempts),
            "older_attempts_omitted": max(0, len(self.attempts) - 3),
            "recent_attempts": copy.deepcopy(self.attempts[-3:]),
        }
