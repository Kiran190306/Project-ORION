"""
Project ORION - Metadata Definitions

Standardized metadata structures for tracking data provenance,
entity metadata, and system metadata across the platform.

Provides:
- Data source metadata
- Entity audit metadata
- System metadata
- Data quality metadata
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass(frozen=True)
class SourceMetadata:
    """Metadata about the source of data or events."""

    source: str = ""
    """Name of the originating service or system."""
    source_version: str = ""
    """Version of the originating service."""
    provider: str = ""
    """External provider name (e.g., broker name)."""
    ingested_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    """Timestamp when data was ingested."""


@dataclass(frozen=True)
class AuditMetadata:
    """Audit trail metadata for entities."""

    created_by: str = ""
    """User or service that created the entity."""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    """Timestamp when entity was created."""
    updated_by: str = ""
    """User or service that last updated the entity."""
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    """Timestamp when entity was last updated."""
    version: int = 1
    """Entity version number for optimistic locking."""


@dataclass(frozen=True)
class SystemMetadata:
    """System-level metadata for internal use."""

    environment: str = "development"
    """Deployment environment."""
    region: str = "local"
    """Geographic region."""
    instance_id: str = ""
    """Unique instance identifier."""
    correlation_id: str = ""
    """Correlation ID for request tracing."""
    request_id: str = ""
    """Unique request identifier."""


@dataclass(frozen=True)
class DataQualityMetadata:
    """Metadata about data quality."""

    quality_score: float = 1.0
    """Overall data quality score (0.0 to 1.0)."""
    completeness: float = 1.0
    """Data completeness ratio."""
    accuracy: float = 1.0
    """Data accuracy score."""
    timeliness: float = 1.0
    """Data timeliness score."""
    consistency: float = 1.0
    """Data consistency score."""
    checked_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    """When quality was last checked."""
    issues: list[str] = field(default_factory=list)
    """List of data quality issues found."""


@dataclass(frozen=True)
class ProcessingMetadata:
    """Metadata about data processing steps."""

    pipeline: str = ""
    """Name of the processing pipeline."""
    pipeline_version: str = ""
    """Version of the processing pipeline."""
    started_at: str = ""
    """Processing start timestamp."""
    completed_at: str = ""
    """Processing completion timestamp."""
    duration_ms: float = 0.0
    """Processing duration in milliseconds."""
    records_processed: int = 0
    """Number of records processed."""
    errors_count: int = 0
    """Number of errors encountered."""


@dataclass(frozen=True)
class Metadata:
    """
    Comprehensive metadata container.
    Combines all metadata types for flexibility.
    """

    source: SourceMetadata = field(default_factory=SourceMetadata)
    audit: AuditMetadata = field(default_factory=AuditMetadata)
    system: SystemMetadata = field(default_factory=SystemMetadata)
    data_quality: DataQualityMetadata = field(default_factory=DataQualityMetadata)
    processing: ProcessingMetadata = field(default_factory=ProcessingMetadata)
    custom: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "source": {
                "source": self.source.source,
                "source_version": self.source.source_version,
                "provider": self.source.provider,
                "ingested_at": self.source.ingested_at,
            },
            "audit": {
                "created_by": self.audit.created_by,
                "created_at": self.audit.created_at,
                "updated_by": self.audit.updated_by,
                "updated_at": self.audit.updated_at,
                "version": self.audit.version,
            },
            "system": {
                "environment": self.system.environment,
                "region": self.system.region,
                "instance_id": self.system.instance_id,
                "correlation_id": self.system.correlation_id,
                "request_id": self.system.request_id,
            },
            "data_quality": {
                "quality_score": self.data_quality.quality_score,
                "completeness": self.data_quality.completeness,
                "accuracy": self.data_quality.accuracy,
                "timeliness": self.data_quality.timeliness,
                "consistency": self.data_quality.consistency,
                "checked_at": self.data_quality.checked_at,
                "issues": self.data_quality.issues,
            },
            "processing": {
                "pipeline": self.processing.pipeline,
                "pipeline_version": self.processing.pipeline_version,
                "started_at": self.processing.started_at,
                "completed_at": self.processing.completed_at,
                "duration_ms": self.processing.duration_ms,
                "records_processed": self.processing.records_processed,
                "errors_count": self.processing.errors_count,
            },
            "custom": self.custom,
        }
