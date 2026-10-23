from . import reviewer_evidence_state as OBS

SWITCHES = {"reviewer_compact_report", "reviewer_evidence_state"}


def install(module):
    original = module.ReviewerRuntime

    class ArchivedConfigReviewer(original):
        def __init__(self, repo_root, request, config, client):
            if any((config.get(key) is not True for key in SWITCHES)):
                raise module.ReviewError(
                    "Both registered diagnostic adapters must be explicitly enabled"
                )
            trusted = {key: value for key, value in config.items() if key not in SWITCHES}
            super().__init__(repo_root, request, trusted, client)
            self.config = dict(config)

    module.ReviewerRuntime = ArchivedConfigReviewer
    return OBS.install(module)
