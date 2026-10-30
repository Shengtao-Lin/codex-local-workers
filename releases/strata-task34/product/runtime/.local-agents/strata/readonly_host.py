"""Opt-in read-only adapter over the qualified native loop and source reader."""

import copy
import difflib
import re
import time
from pathlib import Path
from types import SimpleNamespace

from approved_documents import DOCUMENTS, fetch_document
from general_host import EvidenceScopeError, GeneralHost
from general_prepare import RUNTIME, W, manifest, sha
from general_state import LIMITS, BudgetExhausted, StateError, TaskLedger, fingerprint, read
from report_binding import bind_report
from strata_artifacts import save


class ReadonlyLedger(TaskLedger):
    def __init__(self, root, task_id, role, *, report_repair=False):
        super().__init__(root, task_id)
        requests = 10 if report_repair or role != "investigate" else 8
        self.limits = {
            **LIMITS,
            "model_requests": requests,
            "tool_actions": 16,
            "evidence_actions": 12,
            "edits": 0,
            "initial_checks": 0,
            "post_edit_checks": 0,
            "format_preparations": 0,
            "reserved_output_tokens": requests * 12288,
        }

    def spend(self, key, count=1):
        if type(count) is not int or count < 0 or key not in self.limits:
            raise StateError("Invalid read-only resource reservation")
        if self.state["used"][key] + count > self.limits[key]:
            raise BudgetExhausted("Read-only " + key + " exhausted")
        super().spend(key, count)

    def remaining_seconds(self):
        active = self.state["active"]
        elapsed = max(0, time.time() - active["started"]) if active else 0
        return max(0, 900 - self.state["active_seconds"] - elapsed)

    def current(self):
        return {**super().current(), "limits": self.limits}


class ReportEvidenceError(ValueError):
    def __init__(self, fixes):
        super().__init__(
            "Document citations rejected;use the bounded displayed-line corrections,then resubmit a complete report"
        )
        self.details = {
            "citation_fixes": fixes,
            "acceptance": False,
            "rule": "Exact current fetched line still required;no report was accepted or repaired automatically",
        }


def validate_review_delivery(config, role):
    selected = config.get("experimental_strata_review_delivery")
    if selected is not None and (
        selected != "observed-line-v1"
        or role not in {"implement", "review"}
        or config.get("experimental_strata_capabilities") is True
        or config.get("experimental_strata_report_binding") is not None
        or config.get("experimental_strata_report_receipt") is True
    ):
        raise StateError("Review delivery requires explicit ordinary review/implementation route")


def prepare(root, request, config, *, apply=False):
    root = Path(root).resolve(strict=True)
    request, config = copy.deepcopy(request), copy.deepcopy(config)
    role = request.get("mode")
    from recovery_evidence import validate as validate_recovery_evidence

    validate_recovery_evidence(config, role)
    from failed_draft_diagnostic import FLAG, PURPOSE, validate_profile

    validate_profile(config, role)
    if config.get("experimental_strata_unit_kind") is not None:
        raise StateError("Test-repair unit kind is implementation-only")
    validate_review_delivery(config, role)
    from review_impl_binding import validate_profile as validate_review_impl_binding

    validate_review_impl_binding(config, role)
    if (
        role not in {"investigate", "review"}
        or config.get("experimental_strata_readonly") is not True
    ):
        raise StateError("Explicit experimental read-only role required")
    if (
        config.get("strata_execution_profile") != "strata-unit-v1"
        or config.get("coder_model") != "iq3_s"
    ):
        raise StateError("Current local iq3_s configuration required")
    if config.get("coordinator_enabled"):
        raise StateError("Read-only task cannot enable Coordinator")
    skills = request.pop("approved_skills", [])
    documents = request.pop("approved_documents", [])
    capabilities = request.pop("capabilities", {})
    if (
        not isinstance(documents, list)
        or len(documents) > 2
        or any(not isinstance(doc, str) or doc not in DOCUMENTS for doc in documents)
        or len(set(documents)) != len(documents)
        or (documents and config.get("experimental_strata_documents") is not True)
    ):
        raise StateError("Explicit fixed approved document capability required")
    if skills and config.get("experimental_strata_skills") is not True:
        raise StateError("Explicit approved skill capability required")
    if not isinstance(skills, list) or len(skills) > 4:
        raise StateError("At most four fixed approved skills")
    names = set()
    for skill in skills:
        if not isinstance(skill, dict) or set(skill) != {"name", "description", "content"}:
            raise StateError("Skill fields must be name,description,content")
        if (
            not isinstance(skill["name"], str)
            or not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", skill["name"])
            or skill["name"] in names
            or not isinstance(skill["description"], str)
            or not 1 <= len(skill["description"]) <= 500
            or not isinstance(skill["content"], str)
            or not 1 <= len(skill["content"]) <= 12000
        ):
            raise StateError("Invalid bounded approved skill")
        names.add(skill["name"])
    packet = {
        **request,
        "schema_version": 2,
        "run_id": "prepare-" + request["task_id"],
        "scope": {
            "read": request["read"],
            "readonly": [],
            "modify": [],
            "create": [],
            "forbidden": list(
                dict.fromkeys(
                    [
                        ".agent",
                        ".local-agents",
                        ".git",
                        "acceptance_private",
                        *request.get("scope", {}).get("forbidden", []),
                    ]
                )
            ),
        },
        "focused_tests": [],
        "supplemental_tests": [],
        "edit_targets": [],
        "required_behavior": request.get(
            "required_behavior", [{"id": "contract", "text": request["goal"]}]
        ),
        "acceptance_criteria": [
            {"id": "source-evidence", "text": "Only observed source and bounded uncertainty"}
        ],
        "validation_profile": "project-strict",
    }
    if any(request.get("scope", {}).get(key) for key in ("modify", "create")):
        raise StateError("Read-only request cannot grant writes")
    packet = W.validate_packet(packet)
    runtime = W.WorkerRuntime(root, packet, config, SimpleNamespace())
    facts = manifest(root, packet, runtime.editor)
    from review_impl_binding import require_bound_paths

    require_bound_paths(config, packet, facts, read_source=runtime.editor.read_bytes)
    from capability_policy import validate_capabilities

    capabilities = validate_capabilities(
        {**request, "capabilities": capabilities, "approved_skills": skills}, config, facts
    )
    if role == "review":
        before = request.get("preimages")
        if not isinstance(before, dict) or not before or not set(before) <= facts.keys():
            raise StateError("Review needs approved exact source preimages")
        diff = []
        for path, old in before.items():
            if not isinstance(old, str):
                raise StateError("Text preimages required")
            diff.extend(
                difflib.unified_diff(
                    old.splitlines(True),
                    (root / path).read_text(encoding="utf-8-sig").splitlines(True),
                    fromfile="a/" + path,
                    tofile="b/" + path,
                )
            )
        checks_path = request.get("checks_path")
        if checks_path not in facts:
            raise StateError("Review check receipt must be approved evidence")
        checks = read(root / checks_path)
        if config.get(FLAG) == PURPOSE:
            binding = checks.get("failed_draft_binding", {})
            if (
                checks.get("purpose") != PURPOSE
                or checks.get("commands", {}).get("status") != "failed"
                or not binding.get("identity")
                or not binding.get("check")
                or checks.get("canonical_sha256") != binding["check"].get("sha256")
            ):
                raise StateError("Diagnostic requires bound failed-check receipt")
        hashes = checks.get("source_hashes", {})
        if (
            not hashes
            or not set(before) <= hashes.keys()
            or any(facts.get(path) != digest for path, digest in hashes.items())
        ):
            raise StateError("Supplied check receipt stale/unbound")
        packet["review_material"] = {
            "actual_diff": "".join(diff),
            "checks": checks,
            "changed_paths": sorted(before),
        }
    policy = {
        "profile": "strata-readonly-v1",
        "role": role,
        "task_id": packet["task_id"],
        "initial_hashes": facts,
        "readonly_hashes": facts,
        "check_hashes": {},
        "approved_skills": skills,
        "approved_documents": documents,
        "capabilities": capabilities,
        "create": [],
        "python": {"path": str(runtime.python_path()), "sha256": sha(runtime.python_path())},
        "runtime": {
            p.relative_to(RUNTIME).as_posix(): sha(p)
            for p in RUNTIME.rglob("*")
            if p.is_file() and p.suffix in {".py", ".mjs"}
        },
    }
    material = {"packet": packet, "config": config, "policy": policy}
    from investigation_delivery import repair_enabled
    from investigation_delivery import validate as validate_delivery

    validate_delivery(config, role)
    ledger = ReadonlyLedger(root, packet["task_id"], role, report_repair=repair_enabled(config))
    if ledger.path.exists():
        raise StateError("Read-only task identity already prepared")
    if apply:
        lock = W.RepoWriteLock(root, "prepare-" + packet["task_id"])
        lock.acquire()
        try:
            save(
                ledger.path / "contract.json",
                {"material": material, "sha256": fingerprint(material)},
            )
            ledger.record("readonly_prepared")
        finally:
            lock.release()
    return {
        "status": "prepared" if apply else "preview",
        "source_count": len(facts),
        "task_id": packet["task_id"],
    }


class ReadonlyHost(GeneralHost):
    native_profile = "strata-readonly-v1"

    def review_delivery_enabled(self):
        return (
            self.policy["role"] == "review"
            and self.config.get("experimental_strata_review_delivery") == "observed-line-v1"
        )

    def report_delivery_enabled(self):
        return (
            self.policy["role"] == "investigate"
            and self.config.get("experimental_strata_report_receipt") is True
        )

    def report_binding_enabled(self):
        return (
            self.report_delivery_enabled()
            and self.config.get("experimental_strata_report_binding") == "observed-line-v1"
            and self.config.get("experimental_strata_capabilities") is not True
        )

    def __init__(self, root, task_id, attempt_id, *, resume=False):
        super().__init__(root, task_id, attempt_id, resume=resume)
        validate_review_delivery(self.config, self.policy["role"])
        if (
            self.config.get("experimental_strata_report_binding") is not None
            and not self.report_binding_enabled()
        ):
            raise StateError(
                "Observed-line binding requires explicit ordinary readonly receipt profile"
            )
        if self.policy.get("profile") != self.native_profile or self.policy.get("role") not in {
            "investigate",
            "review",
        }:
            raise StateError("Not an approved read-only task")
        if self.packet["scope"]["modify"] or self.packet["scope"]["create"]:
            raise StateError("Read-only source scope contains writes")
        from investigation_delivery import repair_enabled
        from investigation_delivery import validate as validate_delivery

        validate_delivery(self.config, self.policy["role"])
        self.ledger = ReadonlyLedger(
            root, task_id, self.policy["role"], report_repair=repair_enabled(self.config)
        )
        self.ledger.state.setdefault("expected_hashes", dict(self.policy["initial_hashes"]))
        self.readonly_report = None
        self.result = None

    def open(self):
        self.write_lock.acquire()
        try:
            self.assert_bound()
            from task_continuation import initialize

            initialize(self)
            self.ledger.begin(self.packet["run_id"], resume=self.resume_requested)
            self._begin_evidence_window()
            if self.versions:
                self.versions.begin()
            self.deadline = time.monotonic() + self.ledger.remaining_seconds()
            self._prepare_run_archive()
            self.opened = True
            self.ledger.record("readonly_opened")
            return self.context(initial=True)
        except BaseException:
            self.write_lock.release()
            raise

    def submission_state(self):
        return {"status": "read_only_report_required", "acceptance": False}

    def context(self, *, initial=False):
        value = super().context(initial=initial)
        from investigation_delivery import delivery_context

        value.update(delivery_context(self))
        if self.report_delivery_enabled() or self.review_delivery_enabled():
            value["report_limits"] = {
                "summary_max_characters": 6000,
                "array_max_items": 24,
                "unknown_max_characters": 2000,
                "read_max_lines": 120,
            }
            if self.report_binding_enabled() or self.review_delivery_enabled():
                value["report_limits"]["citation_fields"] = ["path", "line"]
                value["report_limits"]["citation_binding"] = (
                    "Host supplies exact quote only for current observed approved line;does not verify semantic claims"
                )
            if self.review_delivery_enabled():
                value["report_limits"]["legal_statuses"] = [
                    "pass_to_primary",
                    "rework",
                    "insufficient_evidence",
                ]
                from review_impl_binding import FLAG, VERSION, obligations

                if self.config.get(FLAG) == VERSION:
                    value["report_limits"]["bound_implementations"] = obligations(self)
                    value["report_limits"]["bound_implementation_rule"] = (
                        "PASS requires an observed source citation inside every declared bound "
                        "implementation; use insufficient_evidence if unavailable. "
                        "A citation does not prove behavior."
                    )
                if (
                    self.config.get("experimental_strata_failed_draft_diagnostic")
                    == "failed-draft-v1"
                ):
                    value["report_limits"]["legal_statuses"] = ["rework", "insufficient_evidence"]
        if initial:
            value["task"]["mode"] = self.policy["role"]
            if "review_material" in self.packet:
                value["task"]["review_material"] = self.packet["review_material"]
        value["work_state"]["semantic_completion"] = (
            "Source-backed report; no implementation or execution"
        )
        if self.policy.get("approved_skills"):
            value["approved_skill_catalog"] = [
                {"name": s["name"], "description": s["description"]}
                for s in self.policy["approved_skills"]
            ]
        if self.policy.get("approved_documents"):
            value["approved_document_catalog"] = [
                {"id": doc, **DOCUMENTS[doc]} for doc in self.policy["approved_documents"]
            ]
        return value

    def validate_report(self, args):
        from investigation_delivery import normalize_answer

        args = normalize_answer(self, args)
        if self.config.get(
            "experimental_strata_failed_draft_diagnostic"
        ) == "failed-draft-v1" and args.get("status") not in {"rework", "insufficient_evidence"}:
            raise ValueError("Diagnostic cannot PASS or accept;use rework or insufficient_evidence")
        if self.report_binding_enabled():
            args = bind_report(self, args)
        elif self.review_delivery_enabled():
            args = bind_report(self, args, role="review")
        if set(args) != {"status", "summary", "findings", "evidence", "unknowns"}:
            raise ValueError("report fields: status,summary,findings,evidence,unknowns")
        status = args["status"]
        legal = (
            {"answered", "insufficient_evidence"}
            if self.policy["role"] == "investigate"
            else {"pass_to_primary", "rework", "insufficient_evidence"}
        )
        if (
            status not in legal
            or not isinstance(args["summary"], str)
            or not 1 <= len(args["summary"]) <= 6000
        ):
            raise ValueError("Invalid read-only status/summary")
        for field in ("findings", "evidence", "unknowns"):
            if not isinstance(args[field], list) or len(args[field]) > 24:
                if self.report_delivery_enabled():
                    raise ValueError(
                        f"Report {field} must be an array with at most24 items;received {len(args[field]) if isinstance(args[field], list) else 'non-array'}"
                    )
                raise ValueError("Bounded arrays required")
        if any(not isinstance(s, str) or not 1 <= len(s) <= 2000 for s in args["unknowns"]):
            raise ValueError("unknowns must be bounded strings")
        if status == "insufficient_evidence" and not args["unknowns"]:
            raise ValueError("Missing evidence must be stated in unknowns")
        if status != "insufficient_evidence" and not args["evidence"]:
            raise ValueError("Read source and cite displayed lines")
        memory = self.ledger.state.get("evidence_coverage", {})
        citation_fixes = []
        for index, citation in enumerate(args["evidence"]):
            if not isinstance(citation, dict) or set(citation) != {"path", "line", "quote"}:
                raise ValueError("evidence entry: path,line,quote")
            path, line, quote = citation["path"], citation["line"], citation["quote"]
            document = (
                self.ledger.state.get("document_evidence", {}).get(path)
                if isinstance(path, str)
                else None
            )
            if document:
                lines = document["content"].splitlines()
                if (
                    type(line) is not int
                    or not 1 <= line <= len(lines)
                    or not quote
                    or quote != lines[line - 1].strip()
                ):
                    actual = (
                        lines[line - 1].strip()
                        if type(line) is int and 1 <= line <= len(lines)
                        else None
                    )
                    citation_fixes.append(
                        {
                            "evidence_index": index,
                            "path": path,
                            "requested_line": line,
                            "exact_displayed_quote": actual,
                            "exact_quote_matches": [
                                i for i, text in enumerate(lines, 1) if text.strip() == quote
                            ][:3],
                            "content_sha256": document["content_sha256"],
                            "evidence_scope": "Already displayed approved fetched document only",
                        }
                    )
                continue
            if (
                not isinstance(path, str)
                or path not in self.policy["initial_hashes"]
                or type(line) is not int
                or not isinstance(quote, str)
            ):
                raise ValueError("Invalid citation location")
            seen = memory.get(path, {})
            if seen.get("sha256") != self.current_hashes()[path] or line not in seen.get(
                "lines", []
            ):
                raise ValueError("Citation line not observed; read the source range")
            actual = (self.repo_root / path).read_text(encoding="utf-8-sig").splitlines()
            if not 1 <= line <= len(actual) or quote != actual[line - 1].strip() or not quote:
                if self.report_delivery_enabled():
                    citation_fixes.append(
                        {
                            "evidence_index": index,
                            "path": path,
                            "requested_line": line,
                            "exact_displayed_quote": actual[line - 1].strip()
                            if 1 <= line <= len(actual)
                            else None,
                            "source_sha256": self.current_hashes()[path],
                            "evidence_scope": "Already observed source line only;report remains rejected until model resubmits exact citation",
                        }
                    )
                    continue
                raise ValueError("Citation quote must equal the exact trimmed source line")
        if citation_fixes:
            raise ReportEvidenceError(citation_fixes)
        ids = {r["id"] for r in self.packet["required_behavior"]}
        for finding in args["findings"]:
            if not isinstance(finding, dict) or set(finding) != {
                "contract_id",
                "severity",
                "description",
                "evidence_index",
            }:
                raise ValueError("finding entry: contract_id,severity,description,evidence_index")
            if (
                finding["contract_id"] not in ids
                or finding["severity"] not in {"critical", "major", "info"}
                or not isinstance(finding["description"], str)
                or not 1 <= len(finding["description"]) <= 3000
            ):
                raise ValueError("Invalid finding contract/severity/description")
            index = finding["evidence_index"]
            if type(index) is not int or not 0 <= index < len(args["evidence"]):
                raise ValueError("Finding needs zero-based source evidence_index")
        if status == "rework" and not args["findings"]:
            raise ValueError("Rework requires a concrete contract defect")
        from investigation_delivery import enabled as delivery_enabled

        if args["findings"] and (
            status == "pass_to_primary"
            or (status == "answered" and not delivery_enabled(self.config))
        ):
            raise ValueError("Answer/pass cannot contain defect findings")
        if self.policy["role"] == "review" and status == "pass_to_primary":
            changed = self.packet["review_material"]["changed_paths"]
            if not set(changed) <= {e["path"] for e in args["evidence"]}:
                raise ValueError("Pass needs source evidence for each changed file")
            from review_impl_binding import require_pass_evidence

            require_pass_evidence(self, args)
        return copy.deepcopy(args)

    def action(self, action, args):
        self.guard()
        self.assert_bound()
        if self.completion:
            raise StateError("Terminal read-only task")
        self.ledger.spend("tool_actions")
        if action in {"read", "search"}:
            if (
                self.report_delivery_enabled() or self.review_delivery_enabled()
            ) and self.ledger.state["used"]["evidence_actions"] >= self.ledger.limits[
                "evidence_actions"
            ]:
                observation = {
                    "status": "evidence_limit_reached",
                    "source_observed": False,
                    "new_evidence": False,
                    "remaining_evidence_actions": 0,
                    "available_actions": ["report", "blocked"],
                    "note": "No more reads/searches;report only existing observed evidence with explicit gaps,or block. Tool/request/time budgets still apply.",
                }
            else:
                requested = None
                if (
                    self.report_delivery_enabled() or self.review_delivery_enabled()
                ) and action == "read":
                    start, end = args.get("start_line"), args.get("end_line")
                    if (
                        type(start) is int
                        and type(end) is int
                        and start >= 1
                        and end >= start
                        and end - start + 1 > 120
                    ):
                        requested = {"start_line": start, "end_line": end}
                        args = {**args, "end_line": start + 119}
                try:
                    observation = self.evidence(action, args)
                except EvidenceScopeError as exc:
                    # A manifest miss contains no source data. The native bridge
                    # returns a bounded rejection; forbidden paths and all other
                    # state/integrity errors still terminate the read-only task.
                    raise ValueError(str(exc)) from exc
                if requested:
                    observation["read_window"] = {
                        "requested": requested,
                        "clipped_to_max_lines": 120,
                        "next_start_line": args["end_line"] + 1,
                        "note": "Only displayed lines are evidence;remaining lines require another read.",
                    }
        elif action == "skill":
            if set(args) != {"name"} or not isinstance(args["name"], str):
                raise StateError("Exact approved skill name required")
            skill = next(
                (s for s in self.policy.get("approved_skills", []) if s["name"] == args["name"]),
                None,
            )
            if skill is None:
                raise StateError("Unknown or disabled skill")
            self.ledger.spend("evidence_actions")
            observation = {
                "skill": {
                    **skill,
                    "provider": "kit-approved",
                    "source": "custom",
                    "invocation": {"modelInvocable": True, "userInvocable": False},
                },
                "permissions": "Instructions never grant tools, execution or additional source scope",
            }
        elif action == "document":
            if (
                set(args) != {"id"}
                or not isinstance(args["id"], str)
                or args["id"] not in self.policy.get("approved_documents", [])
            ):
                raise StateError("Only an exact preapproved document id is accepted")
            self.ledger.spend("evidence_actions")
            documents = self.ledger.state.setdefault("document_evidence", {})
            key = "document:" + args["id"]
            cached = key in documents
            if not cached:
                document = fetch_document(args["id"])
                save(self.archive.run_root / ("fetched-" + args["id"] + ".json"), document)
                documents[key] = document
                self.ledger.record(
                    "approved_document_fetched",
                    {"id": args["id"], "content_sha256": document["content_sha256"]},
                )
            document = documents[key]
            observation = {
                "document": {k: v for k, v in document.items() if k != "content"},
                "lines": [
                    {"line": i, "text": text}
                    for i, text in enumerate(document["content"].splitlines(), 1)
                ],
                "content": document["content"],
                "cached": cached,
            }
        elif action == "report":
            self.readonly_report = self.validate_report(args)
            self.completion = "ready_for_primary"
            observation = {"status": "report_recorded", "acceptance": False}
        elif action == "blocked" and set(args) == {"reason"} and isinstance(args["reason"], str):
            self.completion = "blocked"
            observation = {"status": "blocked", "reason": args["reason"]}
        else:
            raise StateError("Read-only action denied")
        self.assert_bound()
        result = {"observation": observation, "context": self.context()}
        save(
            self.archive.run_root
            / f"host-tool-result-{self.ledger.state['used']['tool_actions']}.json",
            result,
        )
        return result

    def finish(self, status=None, reason=None):
        if self.result is not None:
            return self.result
        status = status or self.completion or "failed"
        hashes = None
        try:
            if self.opened:
                self.assert_bound()
                hashes = self.current_hashes()
        except (ValueError, OSError) as exc:
            status, reason = "conflicted", str(exc)
        if self.opened:
            self.ledger.end(status)
            self.opened = False
            save(
                self.archive.run_root / "readonly-report.json",
                {
                    "identity": self.identity(),
                    "mode": self.policy["role"],
                    "report": self.readonly_report,
                    "status": status,
                    "reason": reason,
                    "acceptance": False,
                    **(
                        {"purpose": "failed-draft-v1"}
                        if self.config.get("experimental_strata_failed_draft_diagnostic")
                        == "failed-draft-v1"
                        else {}
                    ),
                    "source_hashes": hashes,
                    "contract_sha256": self.contract_digest,
                    **(
                        {
                            "wire_profile": "compact-v1;canonical findings=[];summary/evidence/unknowns preserved"
                        }
                        if self.config.get("experimental_strata_answer_transport") == "compact-v1"
                        else {}
                    ),
                    **(
                        {
                            "citation_binding": "observed-line-v1;quote generated by host from approved observed current source"
                        }
                        if self.report_binding_enabled() or self.review_delivery_enabled()
                        else {}
                    ),
                },
            )
        self.close()
        self.result = {
            "status": status,
            "acceptance": False,
            "report": self.readonly_report,
            "archive": str(self.archive.run_root),
            "ledger": self.ledger.current(),
            "reason": reason,
        }
        return self.result
