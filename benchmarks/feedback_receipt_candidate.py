"""One experimental difference: restore the host's explicit unchanged receipt."""


def wrap(parent, host):
    class Receipt(parent):
        def proposal_context(self):
            messages, binding = super().proposal_context()
            if (
                self.config.get("experimental_explicit_noop_receipt")
                and self.noop_streak
            ):
                facts = host.INTERFACE.restore_literal(messages[1]["content"])
                facts["host_receipt"]["recent"] = (
                    facts["host_receipt"]["recent"]
                    + [{"status": "no_op", "source_sha256": binding["sha256"]}]
                )[-2:]
                messages[1]["content"] = host.INTERFACE.literal_input(facts)
            return messages, binding

    return Receipt
