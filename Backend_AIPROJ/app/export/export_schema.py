"""
Export Schema Utilities — Standardized export metadata.

All exports (RAG, CSV, aggregation, summaries) should include:
- export_version: Schema version
- generated_at: ISO timestamp
- export_source: Source type (rag, csv, aggregation, summary)
- export_metadata: Standardized metadata
"""

from typing import Dict, Any, Literal, Optional
from datetime import datetime
from app.core.logging import setup_logger

logger = setup_logger("INFO")

# Current export schema version
EXPORT_SCHEMA_VERSION = "2.0.0"

ExportSource = Literal["rag", "csv", "aggregation", "summary", "agent"]


def create_export_metadata(
    source: ExportSource,
    operation_id: Optional[str] = None,
    user_id: Optional[str] = None,
    additional_metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create standardized export metadata.
    
    Args:
        source: Export source type
        operation_id: Optional operation identifier
        user_id: Optional user identifier
        additional_metadata: Additional custom metadata
        
    Returns:
        Standardized export metadata dict
    """
    from datetime import timezone
    metadata = {
        "export_version": EXPORT_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "export_source": source,
        "operation_id": operation_id,
        "user_id": user_id
    }
    
    if additional_metadata:
        metadata.update(additional_metadata)
    
    return metadata


def wrap_export_response(
    payload: Dict[str, Any],
    source: ExportSource,
    telemetry: Optional[Dict[str, Any]] = None,
    operation_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Wrap response with standardized export metadata.
    
    Args:
        payload: Original response payload
        source: Export source type
        telemetry: Optional telemetry dict
        operation_id: Optional operation ID
        
    Returns:
        Wrapped response with export metadata
    """
    from app.core.telemetry import ensure_complete_telemetry
    
    # Ensure telemetry is complete
    if telemetry:
        telemetry = ensure_complete_telemetry(telemetry)
    else:
        telemetry = ensure_complete_telemetry({})
    
    # Create export metadata
    export_metadata = create_export_metadata(
        source=source,
        operation_id=operation_id
    )
    
    # Build wrapped response
    wrapped = {
        **export_metadata,
        "data": payload,
        "telemetry": telemetry
    }
    
    return wrapped


def validate_export_schema(export: Dict[str, Any]) -> bool:
    """
    Validate export has required schema fields.
    
    Args:
        export: Export dict to validate
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = [
        "export_version",
        "generated_at",
        "export_source"
    ]
    
    if not all(field in export for field in required_fields):
        missing = [f for f in required_fields if f not in export]
        logger.warning(f"Export missing required fields: {missing}")
        return False
    
    if export["export_source"] not in ["rag", "csv", "aggregation", "summary", "agent"]:
        logger.warning(f"Invalid export_source: {export['export_source']}")
        return False
    
    return True
