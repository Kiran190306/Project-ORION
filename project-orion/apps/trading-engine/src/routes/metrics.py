"""Metrics endpoint exposing Prometheus-compatible application metrics."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from libraries.observability.metrics import MetricsRegistry

from ..dependencies import get_metrics_registry

router = APIRouter(tags=["Metrics"])


@router.get(
    "/metrics",
    summary="Prometheus Metrics",
    description="Returns application and business metrics in standard Prometheus text format.",
    response_class=Response,
)
async def get_metrics(
    registry: Annotated[MetricsRegistry, Depends(get_metrics_registry)],
) -> Response:
    """Export all registered metrics in Prometheus text exposition format."""
    prometheus_data = registry.export_prometheus()
    return Response(
        content=prometheus_data,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
