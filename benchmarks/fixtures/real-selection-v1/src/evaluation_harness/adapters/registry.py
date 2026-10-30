"""In-process registry for immutable adapter name/version pairs."""

from __future__ import annotations

from evaluation_harness.adapters.base import TraceAdapter
from evaluation_harness.errors import ConflictError, NotFoundError


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[tuple[str, str], TraceAdapter] = {}

    def register(self, adapter: TraceAdapter) -> None:
        key = (adapter.name, adapter.version)
        if key in self._adapters:
            raise ConflictError(f"adapter {adapter.name}@{adapter.version} is already registered")
        self._adapters[key] = adapter

    def get(self, name: str, version: str) -> TraceAdapter:
        try:
            return self._adapters[(name, version)]
        except KeyError as exc:
            raise NotFoundError(f"adapter {name}@{version}") from exc

    def list(self) -> list[TraceAdapter]:
        return [self._adapters[key] for key in sorted(self._adapters)]


def default_adapter_registry() -> AdapterRegistry:
    from evaluation_harness.adapters.agent_runtime_kit import AgentRuntimeKitAdapter
    from evaluation_harness.adapters.generic_otel import GenericOtelAdapter

    registry = AdapterRegistry()
    registry.register(GenericOtelAdapter())
    registry.register(AgentRuntimeKitAdapter())
    return registry
