"""
Telemetry Context Manager — Unified observability tracking.

Provides context manager and utilities for tracking operation telemetry
across all platform services (RAG, CSV, summarizer, aggregation, agents).
"""

from .telemetry_context import (
    TelemetryContext,
    track_operation,
    get_current_telemetry,
    finalize_telemetry
)

__all__ = [
    "TelemetryContext",
    "track_operation",
    "get_current_telemetry",
    "finalize_telemetry"
]
