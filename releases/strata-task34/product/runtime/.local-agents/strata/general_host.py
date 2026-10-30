"""General task adapter over the existing editor, validator and canonical archive."""

import copy
import dataclasses
import difflib
import hashlib
import os
import time
from pathlib import Path
from types import SimpleNamespace

from general_editing import EditTargetError
from general_editing import enabled as line_edits_enabled
from general_editing import render as render_line_edits
from general_memory import coverage_view, observe
from general_prepare import RUNTIME, W, load_contract, sha
from general_state import BudgetExhausted, StateError, fingerprint, identifier
from general_versions import VersionReferences, enabled
from strata_artifacts import save


class EvidenceScopeError(StateError):
    """A well-formed, non-forbidden evidence path is outside the approved manifest."""


class GeneralHost(W.WorkerRuntime):
    RUN_STATE = W.RUN_STATE

    def __init__(self, root, task_id, attempt_id, *, resume=False, primary_feedback=None):
        self.ledger, self.material = load_contract(root, task_id)
        self.contract_digest = fingerprint(self.material)
        self.policy = self.material["policy"]
        if self.policy.get("profile") != getattr(self, "native_profile", "strata-unit-v1"):
            raise StateError("Task profile does not match this host entry")
        packet, config = (
            copy.deepcopy(self.material["packet"]),
            copy.deepcopy(self.material["config"]),
        )
        packet["run_id"] = identifier(attempt_id)
        packet["attempt"] = len(self.ledger.state["attempts"]) + 1
        # A file created by this task remains authorized on a later attempt.
        for path in list(packet["scope"]["create"]):
            if (Path(root) / path).is_file() and path in self.ledger.state.get(
                "expected_hashes", {}
            ):
                packet["scope"]["create"].remove(path)
                packet["scope"]["modify"].append(path)
        super().__init__(Path(root), packet, config, SimpleNamespace())
        self.resume_requested = resume
        self.primary_feedback = primary_feedback
        self.opened = False
        self.completion = None
        self.observation_keys = set(self.ledger.state.get("evidence_keys", []))
        self.observations = []
        # Historical citation provenance is not text delivered in this attempt.
        # Only the opted-in ordinary continuation facade gets a fresh progress
        # window. Native retries/rebuilds on this host do not replenish it.
        self.context_coverage = None
        self.context_keys = set()
        self.versions = VersionReferences(self) if enabled(config) else None
        self.bound_paths = sorted(
            set(self.policy["initial_hashes"])
            | set(self.policy.get("check_hashes", {}))
            | set(self.policy["create"])
        )
        self.ledger.state.setdefault(
            "expected_hashes",
            {
                **self.policy["initial_hashes"],
                **self.policy.get("check_hashes", {}),
                **dict.fromkeys(self.policy["create"], None),
            },
        )

    def current_hashes(self):
        result = {}
        for path in self.bound_paths:
            _, target = self.editor.resolve(path)
            result[path] = sha(target) if target.is_file() else None
        return result

    def assert_bound(self):
        if (
            fingerprint(load_contract(self.repo_root, self.packet["task_id"])[1])
            != self.contract_digest
        ):
            raise StateError("Task contract drift")
        if self.current_hashes() != self.ledger.state["expected_hashes"]:
            raise StateError("Source/validation input changed outside the task")
        for path in self.material["packet"]["scope"]["modify"]:
            before = self.ledger.path / "preimages" / path
            if not before.is_file() or sha(before) != self.policy["initial_hashes"][path]:
                raise StateError("Task preimage drift: " + path)
        if sha(self.python_path()) != self.policy["python"]["sha256"]:
            raise StateError("Check interpreter drift")
        for path, expected in self.policy["runtime"].items():
            if sha(RUNTIME / path) != expected:
                raise StateError("Installed runtime changed: " + path)

    def _validation_paths(self):
        return self.bound_paths

    def _contract_check(self, args, *, diagnostic=False):
        # Host-run checks do not manufacture a model's semantic/order attestation.
        # Ordering remains in the hard contract and Primary's final review.
        if diagnostic and not args:
            return None
        return super()._contract_check(args, diagnostic=diagnostic)

    def _command_cancel_requested(self):
        return self.ledger.cancelled()

    def _validation_environment(self):
        roots = [self.repo_root / "src", self.repo_root]
        return {"PYTHONPATH": os.pathsep.join(str(p) for p in roots if p.is_dir())}

    def guard(self):
        self.write_lock.assert_owned()
        if self.ledger.cancelled():
            raise W.InvocationInterrupted("cancel_requested", "Task cancelled")
        if self.ledger.remaining_seconds() <= 0:
            raise BudgetExhausted("Task time exhausted")

    def _assert_mutation_allowed(self):
        super()._assert_mutation_allowed()
        self.guard()

    def open(self):
        self.write_lock.acquire()
        try:
            self.assert_bound()
            from task_continuation import initialize

            initialize(self)
            if self.ledger.cancelled():
                raise StateError("Prior cancelled attempt requires settled state")
            self.ledger.check_begin(self.packet["run_id"], resume=self.resume_requested)
            if self.primary_feedback is not None:
                from general_return import record_primary_return

                record_primary_return(self, self.primary_feedback)
            self.ledger.begin(self.packet["run_id"], resume=self.resume_requested)
            self._begin_evidence_window()
            if self.versions:
                self.versions.begin()
            self.deadline = time.monotonic() + self.ledger.remaining_seconds()
            self._prepare_run_archive()
            self.opened = True
            self.ledger.state["lock_token"] = self.write_lock.token
            self.ledger.record("host_opened")
            if not self.ledger.state["used"]["initial_checks"]:
                self.check(initial=True)
            return self.context(initial=True)
        except BaseException:
            if not self.opened:
                self.write_lock.release()
            raise

    def _begin_evidence_window(self):
        from task_continuation import enabled as continuation_enabled

        if continuation_enabled(self.config):
            self.context_coverage = {}
            self.context_keys = set()
            self.ledger.state["no_evidence"] = 0
            self.ledger.record(
                "attempt_evidence_window_opened", {"attempt_id": self.packet["run_id"]}
            )

    def check(self, *, initial=False):
        self.guard()
        self.assert_bound()
        self.ledger.spend("initial_checks" if initial else "post_edit_checks")
        focused = self.packet["focused_tests"]
        if initial:
            self.packet["focused_tests"] = [
                p for p in focused if (self.repo_root / p.split("::", 1)[0]).is_file()
            ]
        before = self._validation_facts()
        try:
            self.validate({"phase": "check"})
        finally:
            self.packet["focused_tests"] = focused
        # The shared validator can stop after one failed static check. Complete
        # the remaining configured commands as diagnostic evidence in this host.
        complete = {c["id"] for c in self.validation.configured_checks or []}
        commands = list(self.validation.configured_checks or [])
        for command in self.validation_profile()["commands"]:
            if command["id"] not in complete:
                self.guard()
                argv = [
                    a.replace("{python}", str(self.python_path())).replace(
                        "{repo}", str(self.repo_root)
                    )
                    for a in command["argv"]
                ]
                commands.append({"id": command["id"], **self._run_command(argv)})
        self.validation.configured_checks = commands
        if any(c["status"] != "passed" for c in commands):
            self.validation.status = "failed"
            self.validated_input_facts = None
        self.assert_bound()
        if before != self._validation_facts():
            raise StateError("Checks changed their source inputs")
        ref = f"complete-check-{self.validation_count}.json"
        evidence = {
            "identity": self.identity(),
            "initial": initial,
            "validation": dataclasses.asdict(self.validation),
            "inputs": self.current_hashes(),
            "contract_sha256": self.contract_digest,
        }
        junit_name = (self.validation.focused_tests.get("junit") or {}).get("path")
        if junit_name and (self.repo_root / junit_name).is_file():
            evidence["junit_sha256"] = sha(self.repo_root / junit_name)
        save(self.archive.run_root / ref, evidence)
        self.ledger.state["latest_check"] = {
            "path": (self.archive.run_root / ref).relative_to(self.repo_root).as_posix(),
            "sha256": sha(self.archive.run_root / ref),
            "inputs": self.current_hashes(),
        }
        self.ledger.record(
            "complete_checks_finished",
            {"status": self.validation.status, "initial": initial},
        )

    def identity(self):
        return {k: self.packet[k] for k in ("task_id", "unit_id", "run_id")}

    def context(self, *, initial=False):
        check = self.ledger.state.get("latest_check")
        evidence = None
        if check:
            from general_state import read

            evidence = read(self.repo_root / check["path"])["validation"]
        # No model-written progress summaries; exact current facts after each edit.
        result = {
            "identity": self.identity(),
            "files": {
                p: h
                for p, h in self.current_hashes().items()
                if p in self.policy["initial_hashes"] or p in self.policy["create"]
            },
            "resources": self.ledger.current(),
            "validation": evidence,
            "current_check": check,
            "acceptance": "PRIMARY_PENDING",
        }
        diff = self.task_diff()
        if self.versions:
            result["version_references"] = self.versions.view(self.current_hashes())
        result["work_state"] = {
            "effective_changes": self.ledger.state["used"]["edits"],
            "current_diff": diff[:10000],
            "diff_truncated": len(diff) > 10000,
            "submission": self.submission_state(),
            "semantic_completion": "Worker must reconcile full contract; Primary independently accepts",
            "observed_sources": coverage_view(
                self.ledger.state.get("evidence_coverage", {}), self.current_hashes()
            ),
        }
        if self.policy.get("unit_kind"):
            result["work_state"]["unit_kind"] = self.policy["unit_kind"]
        from task_continuation import context as continuation_context

        result.update(continuation_context(self))
        from recovery_evidence import context as recovery_context

        if recovery := recovery_context(self):
            result["recovery_evidence"] = recovery
        if initial:
            if self.ledger.state.get("primary_return"):
                feedback = copy.deepcopy(self.ledger.state["primary_return"])
                feedback.pop("source_inputs")
                result["primary_return"] = feedback
            result["task"] = {
                k: self.material["packet"][k]
                for k in (
                    "goal",
                    "required_behavior",
                    "acceptance_criteria",
                    "acceptance_scenarios",
                    "scope",
                    "focused_tests",
                    "supplemental_tests",
                    "risk",
                    "edit_targets",
                    "dependencies",
                    "owned_contract_ids",
                )
            }
        return result

    def _evidence_arguments(self, action, args, relative):
        if action == "read":
            if set(args) != {"path", "start_line", "end_line"}:
                raise ValueError("read requires path/start_line/end_line")
            start, end = args["start_line"], args["end_line"]
            if (
                type(start) is not int
                or type(end) is not int
                or not 1 <= start <= end
                or end - start + 1 > 120
            ):
                details = {"max_lines": 120}
                if type(start) is int and start >= 1:
                    details["suggested_read"] = {
                        "path": relative,
                        "start_line": start,
                        "end_line": start + 119,
                    }
                raise W.SafeEditError(
                    "Read1..120 lines; use the supplied legal window", details=details
                )
        elif (
            set(args) != {"path", "query"}
            or not isinstance(args["query"], str)
            or not 1 <= len(args["query"]) <= 200
        ):
            raise ValueError("Search bounded literal query")

    def _absent_creation_evidence(self, relative):
        # Only exact, previously approved create targets may reach this method.
        # Ranges/queries cannot manufacture new evidence about the same absence.
        key = fingerprint(["approved_absence", relative])
        fresh = key not in self.observation_keys
        self.observation_keys.add(key)
        self.ledger.state["evidence_keys"] = sorted(self.observation_keys)
        if self.context_coverage is not None:
            fresh = key not in self.context_keys
            self.context_keys.add(key)
        self.ledger.state["no_evidence"] = 0 if fresh else self.ledger.state["no_evidence"] + 1
        observation = {
            "path": relative,
            "status": "not_created",
            "exists": False,
            "source_observed": False,
            "version_ref": None,
            "available_operation": "create",
            "note": "This exact approved creation target has no content yet. Use kit_propose create if needed; no existing-file version reference is available.",
        }
        self.ledger.record("approved_file_absence_observed", {"path": relative, "fresh": fresh})
        if self.ledger.state["no_evidence"] >= 3:
            raise BudgetExhausted("Repeated reads/searches produced no new evidence")
        self.observations.append({"observation": observation, "hashes": {relative: None}})
        return observation

    def evidence(self, action, args):
        from recovery_evidence import admission

        if denial := admission(self, action, args):
            return denial
        self.ledger.spend("evidence_actions")
        path = args.get("path")
        if not isinstance(path, str):
            raise TypeError("Evidence path required")
        relative, target = self.editor.resolve(path)
        available = [
            p
            for p in self.bound_paths
            if (p in self.policy["initial_hashes"] or p in self.policy["create"])
            and self.current_hashes()[p] is not None
        ]
        selected = [
            p
            for p in available
            if p == relative or (action == "search" and p.startswith(relative + "/"))
        ]
        absent_create = (
            relative in self.policy["create"]
            and not W.path_matches_any(relative, self.packet["scope"]["forbidden"])
            and self.current_hashes()[relative] is None
            and not target.exists()
        )
        if not absent_create and (not selected or (action == "read" and selected != [relative])):
            if W.path_matches_any(relative, self.packet["scope"]["forbidden"]):
                raise StateError("Evidence outside approved exact source manifest")
            raise EvidenceScopeError("Evidence outside approved exact source manifest")
        self._evidence_arguments(action, args, relative)
        if absent_create:
            return self._absent_creation_evidence(relative)
        if action == "read":
            start, end = args["start_line"], args["end_line"]
            raw, digest = self.editor.read_bytes(relative)
            lines = raw.decode("utf-8-sig").splitlines()
            observation = {
                "path": relative,
                "sha256": digest,
                "start_line": start,
                "end_line": min(end, len(lines)),
                "content": "\n".join(
                    f"{i + 1}: {line}" for i, line in enumerate(lines) if start <= i + 1 <= end
                ),
            }
        else:
            matches, scanned = [], []
            for name in selected:
                raw, digest = self.editor.read_bytes(name)
                scanned.append(name)
                for i, line in enumerate(raw.decode("utf-8-sig").splitlines(), 1):
                    if args["query"] in line:
                        matches.append({"path": name, "line": i, "text": line, "sha256": digest})
                        if len(matches) == 10:
                            break
                if len(matches) == 10:
                    break
            observation = {
                "matches": matches,
                "scanned_files": scanned,
                "remaining_files": len(selected) - len(scanned),
            }
        key = fingerprint([action, args, self.current_hashes()])
        memory = self.ledger.state.setdefault("evidence_coverage", {})
        if action == "read":
            fresh = observe(memory, relative, digest, range(start, min(end, len(lines)) + 1))
        else:
            fresh = key not in self.observation_keys
            for match in matches:
                observe(memory, match["path"], match["sha256"], [match["line"]])
        historical_fresh = fresh
        if self.context_coverage is not None:
            if action == "read":
                fresh = observe(
                    self.context_coverage, relative, digest, range(start, min(end, len(lines)) + 1)
                )
            else:
                fresh = key not in self.context_keys
                for match in matches:
                    observe(self.context_coverage, match["path"], match["sha256"], [match["line"]])
            self.context_keys.add(key)
        self.ledger.state["no_evidence"] = 0 if fresh else self.ledger.state["no_evidence"] + 1
        self.observation_keys.add(key)
        self.ledger.state["evidence_keys"] = sorted(self.observation_keys)
        from review_rework_budget import DIAGNOSTIC_VERSION, REFOCUS_VERSION

        refocus = self.config.get("experimental_strata_continuation") in (
            REFOCUS_VERSION,
            DIAGNOSTIC_VERSION,
        )
        duplicate_count = 0
        if refocus:
            previous = self.ledger.state.get("refocus_evidence", {})
            if not fresh and previous.get("key") == key:
                duplicate_count = previous["duplicates"] + 1
            self.ledger.state["refocus_evidence"] = {
                "key": key,
                "duplicates": duplicate_count,
            }
        self.ledger.record(
            "evidence_observed",
            {
                "action": action,
                "request": args,
                "sha256": fingerprint(observation),
                "task_new_evidence": historical_fresh,
                "progress_new_evidence": fresh,
            },
        )
        if refocus and duplicate_count >= 3:
            raise BudgetExhausted("Three exact duplicate evidence attempts;no progress")
        if self.ledger.state["no_evidence"] >= (4 if refocus else 3):
            raise BudgetExhausted("Repeated reads/searches produced no new evidence")
        self.observations.append(
            {"observation": observation, "hashes": {p: self.current_hashes()[p] for p in selected}}
        )
        if self.versions:
            if action == "read" and observation["content"]:
                observation["version_ref"] = self.versions.issue(relative, digest)
            elif action == "search":
                for match in observation["matches"]:
                    match["version_ref"] = self.versions.issue(match["path"], match["sha256"])
        return observation

    def propose(self, args):
        if (
            set(args) != {"changes"}
            or not isinstance(args["changes"], list)
            or not 1 <= len(args["changes"]) <= 6
        ):
            raise ValueError("propose requires1..6 file changes")
        proposal_material = [args, self.current_hashes()]
        if line_edits_enabled(self.config):
            proposal_material.append(self.ledger.state.get("evidence_coverage", {}))
        proposal_key = fingerprint(proposal_material)
        if self.ledger.state.get("last_proposal") == proposal_key:
            raise BudgetExhausted("Repeated unchanged proposal against unchanged source")
        self.ledger.state["last_proposal"] = proposal_key
        self.ledger.record("proposal_received", {"sha256": proposal_key})
        self.ledger.spend("format_preparations")
        number = self.ledger.state["used"]["format_preparations"]
        stage = self.archive.run_root / f"staging-{number}"
        stage.mkdir()
        paths, original, output = set(), {}, {}
        scratch = W.SafeEditor(
            stage,
            allowed_modify=self.packet["scope"]["modify"],
            allowed_create=self.packet["scope"]["create"],
            mutation_guard=self._assert_mutation_allowed,
        )
        for change in args["changes"]:
            if not isinstance(change, dict):
                raise TypeError("Change must be an object")
            path, target = self.editor.resolve(change.get("path"))
            if path in paths:
                raise ValueError("One change object per file")
            paths.add(path)
            if change.get("operation") == "create":
                if set(change) != {"path", "operation", "content"}:
                    raise ValueError("Create fields: path, operation='create', content only")
                if path not in self.packet["scope"]["create"]:
                    if (
                        line_edits_enabled(self.config)
                        and path in self.packet["scope"]["modify"]
                        and target.is_file()
                    ):
                        raise EditTargetError(
                            "Existing approved modify target requires replace, not create",
                            {
                                "path": path,
                                "current_sha256": sha(target),
                                "next_action": "read the current file;use its version_ref and observed line ranges with operation='replace'",
                            },
                        )
                    raise StateError("Unauthorized/conflicting create")
                if target.exists():
                    raise ValueError(
                        "Create target already exists; read its current hash and use replace"
                    )
                original[path] = None
                scratch.create(path, change["content"])
            elif change.get("operation") == "replace":
                version_field = "version_ref" if self.versions else "expected_sha256"
                if set(change) != {"path", "operation", version_field, "edits"}:
                    fields = (
                        "start_line,end_line,replace"
                        if line_edits_enabled(self.config)
                        else "find,replace"
                    )
                    raise ValueError(
                        f"Replace fields: path, operation='replace', {version_field}, edits[{{{fields}}}] only"
                    )
                if path not in self.packet["scope"]["modify"] + self.packet["scope"]["create"]:
                    raise StateError("Unauthorized replace")
                raw, current = self.editor.read_bytes(path)
                expected = (
                    self.versions.resolve(change[version_field], path, current)
                    if self.versions
                    else change[version_field]
                )
                if current != expected:
                    raise ValueError("Stale target hash; read current source")
                original[path] = current
                tmp = stage / path
                tmp.parent.mkdir(parents=True, exist_ok=True)
                tmp.write_bytes(raw)
                if path in self.packet["scope"]["create"]:
                    scratch.created_this_run.add(path)
                edits = change["edits"]
                if not isinstance(edits, list) or not 1 <= len(edits) <= 16:
                    raise ValueError("Use1..16 unique exact block replacements")
                if line_edits_enabled(self.config):
                    old_text, new_text = render_line_edits(self, path, raw, current, edits)
                    scratch.replace(path, old_text, new_text, sha(tmp))
                else:
                    for edit in edits:
                        if not isinstance(edit, dict) or set(edit) != {"find", "replace"}:
                            raise ValueError("Exact find/replace fields required")
                        scratch.replace(path, edit["find"], edit["replace"], sha(tmp))
            else:
                raise ValueError("Only replace/create operations")
        self.guard()
        formatted = self._run_command(
            [
                str(self.python_path()),
                "-B",
                "-m",
                "ruff",
                "format",
                *[str(stage / p) for p in sorted(paths)],
            ]
        )
        save(self.archive.run_root / f"format-{number}.json", formatted)
        if formatted["status"] != "passed":
            return {"status": "proposal_rejected", "format": formatted}
        for path in paths:
            output[path] = (stage / path).read_bytes()
        if all(hashlib.sha256(raw).hexdigest() == original[p] for p, raw in output.items()):
            self.ledger.state["noops"] += 1
            self.ledger.record("noop_proposal")
            if self.ledger.state["noops"] >= 2:
                raise BudgetExhausted("Repeated unchanged proposal")
            return {"status": "no_op", "edits_applied": 0}
        self.assert_bound()
        self._require_write_check_opportunity()
        from recovery_evidence import before_write

        before_write(self, output)
        self.ledger.spend("edits")
        transaction = {
            p: {"before": original[p], "after": hashlib.sha256(output[p]).hexdigest()}
            for p in sorted(paths)
        }
        self.ledger.state["pending_transaction"] = transaction
        self.ledger.record("transaction_started", transaction)
        for path in sorted(paths):
            self._assert_mutation_allowed()
            _, target = self.editor.resolve(path)
            actual = sha(target) if target.exists() else None
            if actual != original[path]:
                raise StateError("Concurrent change during transaction")
            if original[path] is None:
                self.editor.create(path, output[path].decode("utf-8"))
            else:
                self.editor._atomic_replace(target, output[path])
            self.changed[path] = {
                "path": path,
                "sha256": sha(target),
                "operation": "created" if original[path] is None else "modified",
            }
        self.edit_revision += 1
        self.ledger.state["pending_transaction"] = None
        self.ledger.state["expected_hashes"] = self.current_hashes()
        if self.versions:
            self.versions.invalidate(paths)
        self.ledger.state["noops"] = self.ledger.state["no_evidence"] = 0
        self.ledger.record("transaction_completed", transaction)
        self.check()
        result = {"status": "changed_and_checked", "changes": transaction}
        from recovery_evidence import refresh

        if current := refresh(self, paths):
            save(self.archive.run_root / f"postwrite-source-{self.edit_revision}.json", current)
            result["current_source"] = current
        from postwrite_evidence import feedback

        if repair_sources := feedback(self, paths):
            save(
                self.archive.run_root / f"failed-check-source-{self.edit_revision}.json",
                repair_sources,
            )
            result["repair_sources"] = repair_sources
        return result

    def _require_write_check_opportunity(self):
        # Use the effective stage limits as well as the shared task limits. This
        # records a preflight refusal, not an extra reservation or a new credit.
        budget = self.ledger.current()
        blocked = [
            key
            for key in ("post_edit_checks", "edits")
            if budget["used"][key] >= budget["limits"][key]
        ]
        if blocked:
            self.ledger.state["exhausted_resource"] = blocked[0]
            self.ledger.record(
                "resource_exhausted",
                {"resource": blocked[0], "blocked_resources": blocked, "before_mutation": True},
            )
            raise BudgetExhausted(
                "No complete post-edit check opportunity: " + ",".join(blocked) + " exhausted"
            )

    def submission_state(self):
        self.assert_bound()
        latest = self.ledger.state.get("latest_check")
        returned = self.ledger.state.get("primary_return")
        if returned and self.ledger.state["used"]["edits"] <= returned["edit_count"]:
            return {
                "status": "submission_rejected",
                "reason": "Primary-confirmed defect needs an effective repair;unchanged green evidence is insufficient",
            }
        if (
            not self.ledger.state["used"]["edits"]
            or not latest
            or self.ledger.state.get("pending_transaction")
        ):
            return {
                "status": "submission_rejected",
                "reason": "No complete current effective edit/check",
            }
        from general_state import read

        if (
            sha(self.repo_root / latest["path"]) != latest["sha256"]
            or latest["inputs"] != self.current_hashes()
        ):
            raise StateError("Current check receipt changed/stale")
        receipt = read(self.repo_root / latest["path"])
        if (
            receipt["identity"]["task_id"] != self.packet["task_id"]
            or receipt["contract_sha256"] != self.contract_digest
        ):
            raise StateError("Check receipt belongs to a different task/contract")
        value = receipt["validation"]
        junit = value["focused_tests"].get("junit", {})
        checks = value.get("configured_checks") or []
        tests_exist = all((self.repo_root / p).is_file() for p in self.packet["supplemental_tests"])
        executed_supplemental = set()
        if junit.get("path"):
            junit_file = self.repo_root / junit["path"]
            if not junit_file.is_file() or sha(junit_file) != receipt.get("junit_sha256"):
                raise StateError("Canonical JUnit evidence changed")
            for case in W.ET.parse(junit_file).getroot().iter("testcase"):
                if case.find("skipped") is not None:
                    continue
                classname = case.get("classname", "")
                for path in self.packet["supplemental_tests"]:
                    prefixes = (
                        path.removesuffix(".py").replace("/", "."),
                        Path(path).stem,
                    )
                    if any(classname == p or classname.startswith(p + ".") for p in prefixes):
                        executed_supplemental.add(path)
        if (
            receipt["initial"]
            or value["status"] != "passed"
            or not tests_exist
            or executed_supplemental != set(self.packet["supplemental_tests"])
            or junit.get("executed", 0) <= 0
            or {c["id"] for c in checks} != set(self.config["required_check_ids"])
            or any(c["status"] != "passed" for c in checks)
        ):
            return {
                "status": "submission_rejected",
                "reason": "Required tests/checks incomplete or failed",
            }
        return {
            "status": "submission_available",
            "next_action": "kit_submit",
            "acceptance": False,
            "meaning": "All mechanical checks are current; submit when the entire contract is implemented. More reads alone do not advance checks.",
        }

    def submit(self):
        eligibility = self.submission_state()
        if eligibility["status"] != "submission_available":
            return eligibility
        self.completion = "ready_for_primary"
        return {
            "status": self.completion,
            "host_handoff_verified": True,
            "acceptance": False,
        }

    def action(self, action, args):
        self.guard()
        self.assert_bound()
        if self.completion:
            raise StateError("Terminal task rejects further actions")
        self.ledger.spend("tool_actions")
        self.ledger.state["last_action"] = action
        result = None
        if action in {"read", "search"}:
            result = self.evidence(action, args)
        elif action == "propose":
            result = self.propose(args)
        elif action == "submit" and args == {}:
            result = self.submit()
        elif action == "blocked" and set(args) == {"reason"} and isinstance(args["reason"], str):
            self.completion = "blocked"
            result = {"status": "blocked", "reason": args["reason"]}
        else:
            raise ValueError("Unknown tool/arguments")
        self.assert_bound()
        result = {"observation": result, "context": self.context()}
        save(
            self.archive.run_root
            / f"host-tool-result-{self.ledger.state['used']['tool_actions']}.json",
            result,
        )
        return result

    def finish(self, status=None, reason=None):
        status = status or self.completion or "failed"
        if self.ledger.state.get("pending_transaction"):
            status = "conflicted"
        if self.opened:
            # On a resumed, unchanged draft the prior complete check remains
            # explicitly task-bound, rather than becoming an invented new run.
            if self.validation is None and self.ledger.state.get("latest_check"):
                from general_state import read

                self.validation = W.ValidationResult(
                    **read(self.repo_root / self.ledger.state["latest_check"]["path"])["validation"]
                )
            report = self.report(status, ["General Strata task result"], reason, [])
            report.update(
                acceptance=False,
                review_route="primary_full_independent_review",
                general_profile="strata-unit-v1",
                ledger=self.ledger.current(),
            )
            if self.policy.get("unit_kind"):
                report["unit_kind"] = self.policy["unit_kind"]
            report["task_check_ref"] = self.ledger.state.get("latest_check")
            report["primary_return_used"] = bool(self.ledger.state.get("primary_return"))
            report["assisted"] = bool(
                (self.ledger.state.get("primary_return") or {}).get("assisted")
            )
            report["semantic_order_verification"] = "PRIMARY_REQUIRED_NOT_HOST_INFERRED"
            self.RUN_STATE.write_bytes_once(
                self.archive.run_root / "task-cumulative.diff",
                self.task_diff().encode("utf-8"),
            )
            report = self._complete_run(report)
            status = report["status"]
            if status not in {
                "ready_for_primary",
                "failed",
                "blocked",
                "budget_exhausted",
                "conflicted",
                "cancelled",
                "interrupted",
            }:
                status = "conflicted"
            self.ledger.end(status)
            self.opened = False
        self.close()
        return {
            "status": status,
            "reason": reason,
            "stop_details": {
                "last_action": self.ledger.state.get("last_action"),
                "last_rejection": self.ledger.state.get("last_rejection"),
                "exhausted_resource": self.ledger.state.get("exhausted_resource"),
            },
            "acceptance": False,
            "primary_return_used": bool(self.ledger.state.get("primary_return")),
            "assisted": bool((self.ledger.state.get("primary_return") or {}).get("assisted")),
            "archive": str(self.archive.run_root),
            "ledger": self.ledger.current(),
            **({"unit_kind": self.policy["unit_kind"]} if self.policy.get("unit_kind") else {}),
        }

    def task_diff(self):
        lines = []
        for path in self.material["packet"]["scope"]["modify"] + self.policy["create"]:
            preimage = self.ledger.path / "preimages" / path
            before = (
                preimage.read_text(encoding="utf-8-sig").splitlines(True)
                if preimage.exists()
                else []
            )
            _, actual = self.editor.resolve(path)
            after = (
                actual.read_text(encoding="utf-8-sig").splitlines(True) if actual.exists() else []
            )
            lines.extend(
                difflib.unified_diff(before, after, fromfile="a/" + path, tofile="b/" + path)
            )
        return "".join(lines)
