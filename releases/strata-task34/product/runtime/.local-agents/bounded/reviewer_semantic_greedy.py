from . import reviewer_semantic_transport as BASE


def install(module):
    base = BASE.install(module)

    class GreedyReviewer(base):
        def validate_report(self, args):
            report = super().validate_report(args)
            report["reviewer_decoding_experiment"] = {
                "archived_temperature": self.config.get("reviewer_temperature"),
                "effective_temperature": self.client.temperature,
                "axis": "temperature 1 to 0 only",
                "production_promoted": False,
            }
            return report

        def run(self):
            if self.client.temperature != 1.0:
                raise module.ReviewError("greedy experiment requires frozen temperature-one origin")
            previous = self.client.temperature
            self.client.temperature = 0.0
            try:
                return super().run()
            finally:
                self.client.temperature = previous

    module.ReviewerRuntime = GreedyReviewer
    return GreedyReviewer
