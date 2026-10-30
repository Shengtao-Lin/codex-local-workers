"""Built-in trace adapters."""

from evaluation_harness.adapters.agent_runtime_kit import AgentRuntimeKitAdapter
from evaluation_harness.adapters.generic_otel import GenericOtelAdapter
from evaluation_harness.adapters.registry import AdapterRegistry, default_adapter_registry

__all__ = [
    "AdapterRegistry",
    "AgentRuntimeKitAdapter",
    "GenericOtelAdapter",
    "default_adapter_registry",
]
