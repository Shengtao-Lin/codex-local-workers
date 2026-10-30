"""Normalize a nullable legacy check list only in the temporary presentation view."""

import copy

import behavior_unit_candidate as V1


def wrap(parent):
    class NullableCheckView(parent):
        def proposal_context(self):
            actual = self.validation
            if (
                self.enabled()
                and actual is not None
                and actual.configured_checks is None
            ):
                view = copy.copy(actual)
                view.configured_checks = []
                self.validation = view
            try:
                return super().proposal_context()
            finally:
                self.validation = actual

    return NullableCheckView


def make_runtime(worker, host):
    return wrap(V1.make_runtime(worker, host))
