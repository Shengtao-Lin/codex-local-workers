"""Bind a Primary acceptance record to the existing Strata workflow and fresh review."""

import copy
from pathlib import Path

import task_workflow as flow
from general_host import GeneralHost
from general_prepare import sha
from general_state import StateError, fingerprint, identifier, read
from readonly_host import ReadonlyHost


def required(root, task_id):
    task = Path(root) / ".agent/tasks" / identifier(task_id)
    if (task / "workflow").exists():
        return True
    material = task / "general/contract.json"
    return (
        material.exists()
        and read(material).get("material", {}).get("config", {}).get("experimental_strata_task")
        is True
    )


class AcceptanceGuard:
    """Hold the existing writer lock until the immutable Primary record is written."""

    def __init__(self, root, task_id, run_id):
        self.root = Path(root).resolve(strict=True)
        self.task_id, self.run_id = identifier(task_id), identifier(run_id)
        self.host = GeneralHost(self.root, self.task_id, "primary-acceptance-gate")
        try:
            self.host.write_lock.acquire()
            self.binding = self.verify()
        except (KeyError, TypeError, IndexError) as exc:
            self.close()
            raise StateError("Malformed independent review evidence") from exc
        except BaseException:
            self.close()
            raise

    def close(self):
        self.host.close()

    def verify(self):
        meta, _, _ = flow.load(self.root, self.task_id)
        if meta["kind"] != "implement" or meta["review_required"] is not True:
            raise StateError("Primary code acceptance requires an implementation workflow")
        state = self.host.ledger.state
        if state["status"] != "ready_for_primary" or state["active"] or state.get("pending_model"):
            raise StateError("Worker is not terminal and ready for Primary acceptance")
        if not state["attempts"] or state["attempts"][-1] != self.run_id:
            raise StateError("Primary acceptance must refer to the current worker attempt")
        home = flow.home(self.root, self.task_id)
        if (home / "cancel.json").exists():
            raise StateError("Cancelled workflow cannot be accepted")
        attempt = home / "runs" / self.run_id
        outcome_path = attempt / "result.json"
        outcome = read(outcome_path)
        self.require_pass(outcome)
        expected_worker = self.root / ".agent/tasks" / self.task_id / "runs" / self.run_id
        if Path(outcome["worker"]["archive"]).resolve() != expected_worker.resolve():
            raise StateError("Workflow worker identity does not match acceptance attempt")
        binding_path = attempt / "review-binding.json"
        binding = read(binding_path)["binding"]
        self.host.assert_bound()
        if (
            self.host.current_hashes() != binding["inputs"]
            or self.host.contract_digest != binding["contract_sha256"]
            or state.get("latest_check") != binding["check"]
            or self.host.submission_state()["status"] != "submission_available"
        ):
            raise StateError("Sources, contract or full check changed after independent review")

        origin, reviewed = attempt, outcome
        visited = set()
        while reviewed.get("review_reused"):
            if origin.name in visited or len(visited) >= len(state["attempts"]):
                raise StateError("Invalid review reuse chain")
            visited.add(origin.name)
            reuse = read(origin / "review-reuse.json")
            prior = Path(reuse["prior_result"]).resolve(strict=True)
            if prior.name != "result.json" or prior.parent.parent != (home / "runs").resolve():
                raise StateError("Review reuse must remain in the same workflow")
            if sha(prior) != reuse["sha256"]:
                raise StateError("Reused review result changed")
            identifier(prior.parent.name)
            if read(prior.parent / "review-binding.json")["binding"] != binding:
                raise StateError("Reused review inputs do not match")
            origin, reviewed = prior.parent, read(prior)
            self.require_pass(reviewed)
            if reviewed["review"] != outcome["review"]:
                raise StateError("Reused review payload does not match its origin")

        review_root = (
            self.root
            / ".agent/reviews"
            / fingerprint({"task": self.task_id, "attempt": origin.name})[:16]
        )
        origin_binding = read(origin / "review-binding.json")
        if Path(origin_binding["project"]).resolve() != review_root.resolve():
            raise StateError("Independent review project identity changed")
        review_task = (
            "review-" + fingerprint({"task": self.task_id, "check": binding["check"]})[:20]
        )
        archive = review_root / ".agent/tasks" / review_task / "runs/fresh"
        recorded = read(origin / "review.json")
        if (
            recorded != reviewed["review"]
            or Path(recorded["archive"]).resolve() != archive.resolve()
        ):
            raise StateError("Independent review archive does not match workflow result")
        report_path = archive / "readonly-report.json"
        canonical = read(report_path)
        if (
            canonical["identity"]
            != {"task_id": review_task, "unit_id": review_task, "run_id": "fresh"}
            or canonical["mode"] != "review"
            or canonical["status"] != "ready_for_primary"
            or canonical["report"] != recorded["report"]
        ):
            raise StateError("Canonical independent report identity or content changed")
        reviewer = ReadonlyHost(review_root, review_task, "primary-evidence-gate")
        try:
            reviewer.write_lock.acquire()
            reviewer.assert_bound()
            if (
                reviewer.ledger.state["status"] != "ready_for_primary"
                or reviewer.ledger.state["active"]
                or reviewer.ledger.state.get("pending_model")
                or canonical["source_hashes"] != reviewer.current_hashes()
                or canonical["contract_sha256"] != reviewer.contract_digest
            ):
                raise StateError("Independent review inputs or state changed")
            supplied = copy.deepcopy(canonical["report"])
            if reviewer.review_delivery_enabled():
                for citation in supplied["evidence"]:
                    citation.pop("quote", None)
            if reviewer.validate_report(supplied) != canonical["report"]:
                raise StateError("Independent report no longer validates against observed evidence")
            evidence = read(review_root / "workflow-evidence/checks.json")
            if (
                evidence["canonical_sha256"] != binding["check"]["sha256"]
                or evidence["contract_sha256"] != binding["contract_sha256"]
                or any(binding["inputs"].get(p) != h for p, h in evidence["source_hashes"].items())
            ):
                raise StateError("Independent review used different implementation evidence")
        finally:
            reviewer.close()
        self.host.assert_bound()
        return {
            "review_task_id": review_task,
            "review_run_id": "fresh",
            "workflow_result": outcome_path.relative_to(self.root).as_posix(),
            "workflow_result_sha256": sha(outcome_path),
            "review_binding_sha256": sha(binding_path),
            "report": report_path.relative_to(self.root).as_posix(),
            "report_sha256": sha(report_path),
            "review_reused": bool(outcome.get("review_reused")),
        }

    def require_pass(self, outcome):
        review = outcome.get("review") or {}
        if (
            outcome.get("task_id") != self.task_id
            or outcome.get("kind") != "implement"
            or outcome.get("status") != "ready_for_primary"
            or review.get("status") != "ready_for_primary"
            or (review.get("report") or {}).get("status") != "pass_to_primary"
        ):
            raise StateError("Primary acceptance requires the completed matching independent PASS")
