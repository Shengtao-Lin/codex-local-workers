import copy
from . import reviewer_canonical_capture as CAPTURE
from . import reviewer_contract_first as SEMANTIC


def _facts(runtime, error):
    if getattr(runtime, "_capture_spec", None) is None:
        return SEMANTIC.FACTS.facts_unavailable(runtime, error)
    try:
        return runtime._read_canonical_capture()
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise error("canonical observation capture rejected: " + str(exc)) from exc


def _restore(runtime, profiles, error):
    if getattr(runtime, "_capture_spec", None) is None:
        return SEMANTIC.TYPED.restore_unavailable(runtime, profiles, error)
    if profiles != runtime._capture_profiles:
        raise error("canonical typed input changed after authentication")
    return (
        copy.deepcopy(profiles),
        [
            {
                "protocol": CAPTURE.PROTOCOL,
                "policy_sha256": runtime._capture_spec[1],
                "model_semantics_supplied": False,
            }
        ],
    )


def install(module, policy_path, expected_sha, *, forward_reasoning_effort=False):
    base = SEMANTIC.install(module, forward_reasoning_effort=forward_reasoning_effort)
    SEMANTIC.FACTS.facts = _facts
    SEMANTIC.TYPED.restore = _restore

    class CaptureReviewer(base):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._capture_spec = (policy_path, expected_sha)
            self._capture_loading = False

        def _read_canonical_capture(self):
            self._capture_loading = True
            try:
                profiles, provenance = CAPTURE.load_capture(self, *self._capture_spec)
                self._capture_profiles = copy.deepcopy(profiles)
                return (profiles, provenance)
            finally:
                self._capture_loading = False

        def _assert_inputs_current(self):
            super()._assert_inputs_current()
            if hasattr(self, "_canonical_capture_epoch") and (not self._capture_loading):
                self._read_canonical_capture()

    module.ReviewerRuntime = CaptureReviewer
    return CaptureReviewer
