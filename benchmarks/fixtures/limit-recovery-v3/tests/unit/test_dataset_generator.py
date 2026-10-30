from datetime import UTC, datetime

from evaluation_harness.adapters.generic_otel import GenericOtelAdapter
from evaluation_harness.contracts import DatasetGenerationRequest, SelectionPolicy
from evaluation_harness.datasets.generator import generate_dataset
from tests.conftest import load_trace


def test_dataset_generation_deduplicates_and_excludes_internal(application) -> None:
    trace = load_trace("generic_multi_turn.json")
    internal = load_trace("generic_multi_turn.json", trace_id="internal")
    internal.raw["metadata"]["service.name"] = "evaluation-worker"
    request = DatasetGenerationRequest(
        application_id=application.application_id,
        name="daily",
        start_time=datetime(2026, 1, 1, tzinfo=UTC),
        end_time=datetime(2026, 1, 3, tzinfo=UTC),
        row_mode="turn",
        selection=SelectionPolicy(),
        adapter_name="generic-otel",
        adapter_version="1.0.0",
    )
    first = generate_dataset(
        dataset_id="ds-1",
        version=1,
        source_name="fixture",
        application=application,
        request=request,
        adapter=GenericOtelAdapter(),
        traces=[trace, trace, internal],
        created_at=datetime(2026, 1, 3, tzinfo=UTC),
    )
    second = generate_dataset(
        dataset_id="ds-1",
        version=1,
        source_name="fixture",
        application=application,
        request=request,
        adapter=GenericOtelAdapter(),
        traces=[trace, trace, internal],
        created_at=datetime(2026, 1, 3, tzinfo=UTC),
    )
    assert first.manifest.accepted_count == 2
    assert first.manifest.duplicate_count == 2
    assert first.manifest.internal_count == 1
    assert first.manifest.manifest_hash == second.manifest.manifest_hash
