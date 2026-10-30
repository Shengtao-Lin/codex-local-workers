"""Explicit experiment: use the existing low/required REPORT profile from turn1.

No verdict/schema/uncertainty/acceptance or recovery-budget changes. This adapter
is copied only to isolated experiment installations, never production defaults.
"""


def install(module, base, *, enabled=False):
    if type(enabled) is not bool:
        raise ValueError("direct report opt-in must be boolean")
    if not enabled:
        return base

    class DirectReportReviewer(base):
        def _request_phase_completion(self, messages, tools, stage):
            start = self.actual_requests
            if stage == "source_review":
                # Reuse the already tested sticky low/required transport branch.
                self.fallback_active = True
            try:
                return super()._request_phase_completion(messages, tools, stage)
            finally:
                for row in self.request_profiles:
                    if row["request"] > start and row["stage"] == "source_review":
                        row["selection"] = "explicit-direct-report-v1"

    module.ReviewerRuntime = DirectReportReviewer
    return DirectReportReviewer
