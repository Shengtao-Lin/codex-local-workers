"""Offline-only scheduling candidate; no budget refunds or production changes."""


def make_runtime(worker, parent):
    class PrepareThenCheck(parent):
        def __init__(self, root, packet, config, client):
            if config.get("experimental_prevalidation_format") is not True:
                raise worker.WorkerError(
                    "Prevalidation preparation needs explicit opt-in"
                )
            super().__init__(root, packet, config, client)

        def host_validate(self):
            # Check eligibility with the ORIGINAL guarded policy. Only the
            # already-authorized one-shot whitespace formatter moves earlier.
            # Never decrement validation_count/edit_revision or replay a check.
            if self.validation_count >= self.host_check_cap:
                raise worker.WorkerError("Host validation budget exhausted")
            issues = self._introduced_text_quality_issues()
            profile = self.validation_profile()
            python = self.python_path()
            if self._diff_whitespace_autoformat_eligible(issues, profile, python):
                before = self._validation_facts()
                count = self.validation_count
                revision = self.edit_revision
                changed = self._try_autoformat(python)
                self.RUN_STATE.write_json_once(
                    self.archive.run_root / "prevalidation-format.json",
                    {
                        "kind": "preparation_not_validation",
                        "issues": issues,
                        "before": before,
                        "after": self._validation_facts(),
                        "changed": changed,
                        "validation_count_before": count,
                        "validation_count_after": self.validation_count,
                        "edit_revision_before": revision,
                        "edit_revision_after": self.edit_revision,
                        "acceptance_credit": False,
                    },
                )
                if self.validation_count != count:
                    raise worker.PolicyViolation(
                        "Preparation altered validation budget"
                    )
            return super().host_validate()

    return PrepareThenCheck
