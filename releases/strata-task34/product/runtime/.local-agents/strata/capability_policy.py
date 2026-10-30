"""Trusted task ceilings for optional capabilities; model arguments never grant scope."""

import re

from general_state import StateError
from public_pages import checked_url


def validate_capabilities(request, config, facts):
    caps = request.get("capabilities", {})
    if not isinstance(caps, dict) or set(caps) - {"web", "operations", "children"}:
        raise StateError("Unknown capability; no arbitrary shell or recursive permission")
    child = config.get("strata_capability_child") is True
    if config.get("experimental_strata_capabilities") is True and request.get("mode") not in {
        "investigate",
        "implement",
    }:
        raise StateError("Optional capability reporting does not alter Reviewer mode")
    if (caps or child) and (
        config.get("experimental_strata_capabilities") is not True
        or request.get("mode") not in {"investigate", "implement"}
    ):
        raise StateError("Explicit investigate capability opt-in required")
    if caps and config.get("experimental_native_tools_trial"):
        raise StateError("Do not combine optional evidence and native file-tool trial profiles")
    if child and caps:
        raise StateError("Child cannot enable capabilities or descendants")
    if "web" in caps:
        web = caps["web"]
        if not isinstance(web, dict) or set(web) != {"public_context", "hosts", "entries"}:
            raise StateError("Explicit public context,hosts,entries required")
        if web["public_context"] is not True or request.get("approved_skills"):
            raise StateError("Public-only context; no private skill loading with public networking")
        hosts, entries = web["hosts"], web["entries"]
        if (
            not isinstance(hosts, list)
            or not 1 <= len(hosts) <= 4
            or any(
                not isinstance(h, str)
                or not re.fullmatch(r"[a-z][a-z0-9.-]*\.[a-z]{2,}", h)
                or ".." in h
                for h in hosts
            )
            or not isinstance(entries, dict)
            or not 1 <= len(entries) <= 4
        ):
            raise StateError("Bounded public host/entry catalog required")
        for key, url in entries.items():
            if not isinstance(key, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,40}", key):
                raise StateError("Invalid public entry id")
            checked_url(url, hosts)
    if "operations" in caps:
        ops = caps["operations"]
        if (
            not isinstance(ops, dict)
            or set(ops) != {"json-summary"}
            or not isinstance(ops["json-summary"], list)
            or not ops["json-summary"]
            or any(p not in facts for p in ops["json-summary"])
        ):
            raise StateError("Only json-summary over exact pinned approved files")
    if "children" in caps:
        children = caps["children"]
        if not isinstance(children, dict) or set(children) != {"read"}:
            raise StateError("Child scope must be exact readonly subset")
        paths = children["read"]
        if (
            not isinstance(paths, list)
            or not paths
            or len(set(paths)) != len(paths)
            or any(p not in facts for p in paths)
        ):
            raise StateError("Child readable files must be exact parent subset")
    if "web" in caps and set(caps) - {"web", "operations"}:
        raise StateError("Public-network child composition not approved")
    return caps
