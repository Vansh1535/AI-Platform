"""__init__.py for telemetry package"""
from app.core.telemetry.unified_trace import (
    start_trace,
    end_trace,
    record_step,
    attach_metadata,
    finalize_response,
    safe_try,
    ensure_telemetry_fields,
    merge_trace_metadata,
    trace_operation,
    UnifiedTrace
)
from app.core.telemetry.telemetry_standards import (
    ensure_complete_telemetry,
    merge_telemetry,
    compute_total_latency,
    extract_standard_telemetry,
    REQUIRED_TELEMETRY_FIELDS
)

__all__ = [
    "start_trace",
    "end_trace",
    "record_step",
    "attach_metadata",
    "finalize_response",
    "safe_try",
    "ensure_telemetry_fields",
    "merge_trace_metadata",
    "trace_operation",
    "UnifiedTrace",
    "ensure_complete_telemetry",
    "merge_telemetry",
    "compute_total_latency",
    "extract_standard_telemetry",
    "REQUIRED_TELEMETRY_FIELDS"
]
