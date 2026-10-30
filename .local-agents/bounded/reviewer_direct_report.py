"""Explicit low/required source-review transport; verdict gates are unchanged."""


def install(module, base, *, enabled=False):
    if type(enabled) is not bool:
        raise ValueError("direct report opt-in must be boolean")
    if not enabled:
        return base

    class DirectReportReviewer(base):
        def _request_phase_completion(self, messages, tools, stage):
            start = self.actual_requests
            if stage == "source_review":
                self.fallback_active = True
            try:
                return super()._request_phase_completion(messages, tools, stage)
            finally:
                for row in self.request_profiles:
                    if row["request"] > start and row["stage"] == "source_review":
                        row["selection"] = "explicit-direct-report-v1"

    module.ReviewerRuntime = DirectReportReviewer
    return DirectReportReviewer
