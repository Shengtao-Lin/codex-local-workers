"""One narrow inherited repair of the actual eighteen-test failed draft."""

import argparse

import tool_contract_rework as repair
from capability_fit import WORK


def configure(arm):
    repair.BASE = WORK / "tool-context-scope-1"
    repair.FIXTURE_VERSION = 10
    repair.FEEDBACK = (
        "Primary read the actual current execute block and the four failing protected tests. "
        "The expression tool.handler(**values) invokes the synchronous callable immediately "
        "on the event-loop thread. Moving lambda: result to a thread afterwards moves only "
        "the computed value, not the invocation; this also loses caller ContextVar isolation. "
        "Repair ownership of the actual handler invocation, not delivery of the result. "
        "Keep exactly one handler call, with caller context visible off-thread and its "
        "mutations isolated. Returned-awaitable completion remains on the caller loop. "
        "The existing direct async return branch, single outer deadline, imports, error "
        "causes, hooks and all already-passing cases must remain valid. Read the current "
        "bounded execute area, edit its responsible call, then validate current code. "
        "No new loop, no recursive async final-value consumption, no protected test edits."
    )
    if arm == "fresh-1":
        repair.FEEDBACK = (
            "Primary inspected your actual execute block: synchronous tool.handler is "
            "called immediately once on the caller loop, and plain results then trigger "
            "a second invocation in the worker thread. The first call must not happen on "
            "the caller loop; deciding from the returned object's type is too late to "
            "choose invocation ownership. Every synchronous callable is invoked once "
            "off-thread, regardless of what type it eventually returns. Its returned "
            "awaitable, if any, completes once on the caller loop. Keep the working direct "
            "async branch and the shared outer deadline. Source-backed advisory: Primary "
            "read this environment's standard-library asyncio.to_thread: it propagates "
            "copy_context to the callable, whereas plain run_in_executor alone does not. "
            "This is context/thread API evidence, not a required code shape; another "
            "implementation is valid if it preserves all original behavior. Locate and "
            "repair the double call in the current execute area, then validate all eighteen "
            "protected tests and existing static checks. Do not rewrite unrelated code."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "register-actual", "run"))
    parser.add_argument("--arm", choices=("fresh-1", "fresh-2"), required=True)
    args = parser.parse_args()
    configure(args.arm)
    {
        "prepare": repair.prepare,
        "register-actual": repair.register_actual,
        "run": repair.run,
    }[args.action](args.arm)
