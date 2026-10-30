"""Opt-in installed experiment entry; frozen semantic engine remains unchanged."""

import argparse
import copy
import json
import sys
from pathlib import Path

import capture_fixture_support as F
import reviewer_canonical_capture as CAPTURE
import reviewer_contract_first as SEMANTIC

_old_facts = SEMANTIC.FACTS.facts
_old_restore = SEMANTIC.TYPED.restore


def _facts(runtime, error):
    if getattr(runtime, "_capture_spec", None) is None:
        return _old_facts(runtime, error)
    try:
        return runtime._read_canonical_capture()
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise error("canonical observation capture rejected: " + str(exc)) from exc


def _restore(runtime, profiles, error):
    if getattr(runtime, "_capture_spec", None) is None:
        return _old_restore(runtime, profiles, error)
    if profiles != runtime._capture_profiles:
        raise error("canonical typed input changed after authentication")
    return copy.deepcopy(profiles), [
        {
            "protocol": CAPTURE.PROTOCOL,
            "policy_sha256": runtime._capture_spec[1],
            "model_semantics_supplied": False,
        }
    ]


def install(module, policy_path, expected_sha, *, forward_reasoning_effort=False):
    base = SEMANTIC.install(module, forward_reasoning_effort=forward_reasoning_effort)
    # Dispatch only explicitly enrolled runtime objects. Old calls retain their
    # exact sealed-source provider and typed-input restoration, fail-closed.
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
                return profiles, provenance
            finally:
                self._capture_loading = False

        def _assert_inputs_current(self):
            super()._assert_inputs_current()
            if hasattr(self, "_canonical_capture_epoch") and not self._capture_loading:
                self._read_canonical_capture()

    module.ReviewerRuntime = CaptureReviewer
    return CaptureReviewer


def main():
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--runtime-dir", required=True)
    parser.add_argument("--capture-policy", required=True)
    parser.add_argument("--capture-policy-sha256", required=True)
    parser.add_argument("--inspect-only", action="store_true")
    parser.add_argument("--forward-reasoning-effort", action="store_true")
    args, remaining = parser.parse_known_args()
    path = Path(args.runtime_dir) / "reviewer-runtime.py"
    module = F.load(path, "installed_capture_reviewer")
    runtime_class = install(
        module,
        args.capture_policy,
        args.capture_policy_sha256,
        forward_reasoning_effort=args.forward_reasoning_effort,
    )
    if args.inspect_only:
        offline = argparse.ArgumentParser(allow_abbrev=False)
        offline.add_argument("--request", type=Path, required=True)
        offline.add_argument("--config", type=Path, required=True)
        offline.add_argument("--report", type=Path, required=True)
        options = offline.parse_args(remaining)
        request = json.loads(options.request.read_text(encoding="utf-8"))
        config = json.loads(options.config.read_text(encoding="utf-8"))
        runtime = runtime_class(Path.cwd(), request, config, object())
        runtime.prepare()
        bundle = runtime.bundle()
        options.report.parent.mkdir(parents=True, exist_ok=True)
        module.RUN_STATE.write_json_once(
            options.report,
            {
                "mode": "offline-input-inspection",
                "model_calls": 0,
                "reviewer_acceptance": False,
                "bundle": bundle,
                "provenance": runtime.observation_provenance,
            },
        )
        return 0
    sys.argv = [str(path), *remaining]
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
