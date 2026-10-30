"""Optional mechanical linkage from PASS to Primary-owned implementation refs."""

import ast

from general_state import StateError

FLAG = "experimental_strata_review_impl_binding"
VERSION = "observed-v1"


def validate_profile(config, role):
    selected = config.get(FLAG)
    if selected is None:
        return
    if (
        selected != VERSION
        or role not in {"implement", "review"}
        or config.get("experimental_strata_review_delivery") != "observed-line-v1"
    ):
        raise StateError("Implementation binding requires explicit observed-line review profile")


def obligations(host):
    return [
        {"contract_id": item["id"], **item["implementation_ref"]}
        for item in host.packet["required_behavior"]
        if "implementation_ref" in item
    ]


def _is_existing_class(source, symbol):
    """Recognize only existing class declarations, never guess future edit contents."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        # A syntax-error repair may be a legitimate task. Current checks and the
        # ordinary binding validator still have to pass before final acceptance.
        return False

    def visit(node, prefix=""):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            name = prefix + node.name
            if isinstance(node, ast.ClassDef) and name == symbol:
                return True
            prefix = name + "."
        return any(visit(child, prefix) for child in ast.iter_child_nodes(node))

    return visit(tree)


def require_bound_paths(config, packet, facts, *, read_source):
    """A declared binding never creates permission or an implicit missing file."""
    if config.get(FLAG) != VERSION:
        return
    for item in packet["required_behavior"]:
        ref = item.get("implementation_ref")
        if ref is not None and ref["path"] not in facts:
            raise StateError(
                "Declared implementation binding is outside approved exact source manifest"
            )
        if ref is not None:
            raw, digest = read_source(ref["path"])
            if digest != facts[ref["path"]]:
                raise StateError("Implementation binding source changed during preparation")
            if _is_existing_class(raw.decode("utf-8-sig"), ref["symbol"]):
                raise StateError(
                    "Implementation binding resolves to an unsupported class; select a specific "
                    f"function/method/assignment for {item['id']} ({ref['path']}:{ref['symbol']}) "
                    "before dispatch"
                )


def require_pass_evidence(host, report):
    if host.config.get(FLAG) != VERSION or report["status"] != "pass_to_primary":
        return
    from general_prepare import W

    refs = [
        {"path": item["path"], "start_line": item["line"], "end_line": item["line"]}
        for item in report["evidence"]
    ]
    for item in obligations(host):
        binding = {"path": item["path"], "symbol": item["symbol"]}
        raw, digest = host.editor.read_bytes(binding["path"])
        if digest != host.current_hashes().get(binding["path"]):
            raise StateError("Bound implementation changed during review")
        try:
            covered = W.citation_binding().covers(binding, raw.decode("utf-8-sig"), refs)
        except ValueError as exc:
            raise ValueError(
                f"PASS needs an unambiguous bound implementation for {item['contract_id']}; "
                "use insufficient_evidence when it cannot be verified"
            ) from exc
        if not covered:
            raise ValueError(
                f"PASS requires an observed source citation inside bound implementation "
                f"{item['contract_id']} ({binding['path']}:{binding['symbol']}); "
                "use insufficient_evidence if unavailable"
            )
