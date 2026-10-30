"""Immutable dataset manifest and rejection contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from evaluation_harness.canonical.models import CanonicalSample
from evaluation_harness.contracts import SelectionPolicy


class Rejection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_trace_id: str
    reason: str
    message: str


class DatasetManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    dataset_id: str
    version: int
    name: str
    workspace_id: str = "default"
    application_id: str
    environment: str
    source_name: str
    adapter_name: str
    adapter_version: str
    schema_version: Literal["1.0"] = "1.0"
    row_mode: Literal["trace", "turn"]
    selection: SelectionPolicy
    start_time: datetime
    end_time: datetime
    sample_ids: tuple[str, ...]
    fingerprints: tuple[str, ...]
    accepted_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)
    duplicate_count: int = Field(ge=0)
    internal_count: int = Field(ge=0)
    include_feedback: bool
    created_at: datetime
    ready_at: datetime
    mlflow_dataset_uri: str | None = None
    manifest_hash: str


class GeneratedDataset(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    manifest: DatasetManifest
    samples: tuple[CanonicalSample, ...]
    rejections: tuple[Rejection, ...]
