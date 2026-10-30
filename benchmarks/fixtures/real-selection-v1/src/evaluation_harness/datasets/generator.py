"""Pure, deterministic dataset construction used by workers."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from evaluation_harness.adapters.base import AdapterContext, AdapterError, TraceAdapter
from evaluation_harness.canonical.fingerprint import canonical_json, content_fingerprint
from evaluation_harness.contracts import ApplicationSpec, DatasetGenerationRequest
from evaluation_harness.datasets.models import DatasetManifest, GeneratedDataset, Rejection
from evaluation_harness.datasets.selection import select_records
from evaluation_harness.telemetry.classification import is_internal_trace
from evaluation_harness.trace_sources.base import SourceTrace


def generate_dataset(
    *,
    dataset_id: str,
    version: int,
    source_name: str,
    application: ApplicationSpec,
    request: DatasetGenerationRequest,
    adapter: TraceAdapter,
    traces: list[SourceTrace],
    created_at: datetime | None = None,
) -> GeneratedDataset:
    selected = select_records(
        traces,
        request.selection,
        identity=lambda item: item.source_trace_id,
        timestamp=lambda item: item.observed_at,
    )
    context = AdapterContext(application=application, row_mode=request.row_mode)
    accepted = []
    rejections: list[Rejection] = []
    seen: set[tuple[str, str]] = set()
    duplicates = 0
    internal = 0
    for trace in selected:
        if is_internal_trace(trace.raw):
            internal += 1
            continue
        try:
            if not adapter.can_handle(trace):
                raise AdapterError("adapter_mismatch", "selected adapter cannot handle this trace")
            normalized = adapter.normalize(trace, context=context)
            for sample in normalized:
                fingerprint = content_fingerprint(sample)
                identity = (sample.sample_id, fingerprint)
                if identity in seen:
                    duplicates += 1
                    continue
                seen.add(identity)
                accepted.append((sample, fingerprint))
        except AdapterError as exc:
            rejections.append(
                Rejection(
                    source_trace_id=trace.source_trace_id,
                    reason=exc.reason,
                    message=str(exc),
                )
            )
        except Exception:
            rejections.append(
                Rejection(
                    source_trace_id=trace.source_trace_id,
                    reason="normalization_failed",
                    message="Trace normalization failed.",
                )
            )
    accepted.sort(key=lambda item: (item[0].event_time, item[0].sample_id))
    now = created_at or datetime.now(UTC)
    material = {
        "dataset_id": dataset_id,
        "version": version,
        "name": request.name,
        "workspace_id": application.workspace_id,
        "application_id": application.application_id,
        "environment": application.environment,
        "adapter": f"{adapter.name}@{adapter.version}",
        "row_mode": request.row_mode,
        "selection": request.selection.model_dump(mode="json"),
        "window": [request.start_time, request.end_time],
        "samples": [(sample.sample_id, fingerprint) for sample, fingerprint in accepted],
        "rejections": [item.model_dump(mode="json") for item in rejections],
        "duplicate_count": duplicates,
        "internal_count": internal,
    }
    manifest_hash = hashlib.sha256(canonical_json(material)).hexdigest()
    manifest = DatasetManifest(
        dataset_id=dataset_id,
        version=version,
        name=request.name,
        workspace_id=application.workspace_id,
        application_id=application.application_id,
        environment=application.environment,
        source_name=source_name,
        adapter_name=adapter.name,
        adapter_version=adapter.version,
        row_mode=request.row_mode,
        selection=request.selection,
        start_time=request.start_time,
        end_time=request.end_time,
        sample_ids=tuple(sample.sample_id for sample, _ in accepted),
        fingerprints=tuple(fingerprint for _, fingerprint in accepted),
        accepted_count=len(accepted),
        rejected_count=len(rejections),
        duplicate_count=duplicates,
        internal_count=internal,
        include_feedback=request.include_feedback,
        created_at=now,
        ready_at=now,
        manifest_hash=manifest_hash,
    )
    return GeneratedDataset(
        manifest=manifest,
        samples=tuple(sample for sample, _ in accepted),
        rejections=tuple(rejections),
    )
