"""
Telemetry standardization utilities for unified observability.

Ensures all subsystems emit consistent telemetry with required fields:
- latency_ms_total
- latency_ms_retrieval
- latency_ms_embedding
- latency_ms_llm
- routing_decision
- confidence_score
- cache_hit
- retry_count
- fallback_triggered
- degradation_level
- graceful_message
"""

from typing import Dict, Any, Optional


# Required telemetry fields for unified observability
REQUIRED_TELEMETRY_FIELDS = [
    "latency_ms_total",
    "latency_ms_retrieval",
    "latency_ms_embedding",
    "latency_ms_llm",
    "routing_decision",
    "confidence_score",
    "cache_hit",
    "retry_count",
    "fallback_triggered",
    "degradation_level",
    "graceful_message"
]


def ensure_complete_telemetry(telemetry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure telemetry dict has all required fields with safe defaults.
    
    This function fills in missing fields to guarantee consumers
    can safely access all standard telemetry fields without checks.
    
    Args:
        telemetry: Partial telemetry dict from subsystem (can be None)
        
    Returns:
        Complete telemetry dict with all required fields
        
    Example:
        >>> raw_telemetry = {"latency_ms_total": 150, "mode": "rag"}
        >>> complete = ensure_complete_telemetry(raw_telemetry)
        >>> complete["cache_hit"]  # Safe access, returns False
        False
    """
    # Handle None input
    if telemetry is None:
        telemetry = {}
    
    # Create copy to avoid mutating input
    complete = dict(telemetry)
    
    # Default values for each required field
    defaults = {
        "latency_ms_total": complete.get("latency_ms", 0),  # Fallback to old name
        "latency_ms_retrieval": 0,
        "latency_ms_embedding": 0,
        "latency_ms_llm": 0,
        "routing_decision": complete.get("mode", "unknown"),  # Fallback to mode
        "confidence_score": complete.get("confidence_top", 0.0),  # Fallback to retrieval confidence
        "cache_hit": complete.get("cache_used", False),  # Fallback to old name
        "retry_count": complete.get("retries", 0),  # Fallback to old name
        "fallback_triggered": complete.get("fallback_used", False),  # Fallback to old name
        "degradation_level": complete.get("degradation", "none"),  # Fallback to old name
        "graceful_message": ""  # Default to empty string
    }
    
    # Fill in missing fields
    for field, default_value in defaults.items():
        if field not in complete:
            complete[field] = default_value
    
    # Ensure degradation_level is valid
    if complete["degradation_level"] not in ["none", "degraded", "fallback", "failed"]:
        complete["degradation_level"] = "none"
    
    # Set graceful_message from fallback_reason if present
    if not complete["graceful_message"] and complete.get("fallback_reason"):
        complete["graceful_message"] = f"Degraded: {complete['fallback_reason']}"
    
    return complete


def merge_telemetry(*telemetry_dicts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge multiple telemetry dictionaries intelligently.
    
    Rules:
    - Sum all latency fields
    - Take maximum degradation level
    - OR boolean fields (cache_hit, fallback_triggered)
    - Sum retry_count
    - Use last non-null value for others
    
    Args:
        *telemetry_dicts: Variable number of telemetry dicts
        
    Returns:
        Merged telemetry dict
        
    Example:
        >>> t1 = {"latency_ms_total": 100, "cache_hit": False}
        >>> t2 = {"latency_ms_total": 50, "cache_hit": True}
        >>> merged = merge_telemetry(t1, t2)
        >>> merged["latency_ms_total"]
        150
        >>> merged["cache_hit"]
        True
    """
    if not telemetry_dicts:
        return {}
    
    merged = {}
    
    # Fields to sum
    sum_fields = [
        "latency_ms_total",
        "latency_ms_retrieval",
        "latency_ms_embedding",
        "latency_ms_llm",
        "retry_count"
    ]
    
    # Boolean fields to OR
    or_fields = ["cache_hit", "fallback_triggered"]
    
    # Process all telemetry dicts
    for telemetry in telemetry_dicts:
        if not telemetry:
            continue
        
        for key, value in telemetry.items():
            if key in sum_fields:
                merged[key] = merged.get(key, 0) + (value or 0)
            elif key in or_fields:
                merged[key] = merged.get(key, False) or value
            else:
                # Last non-null wins
                if value is not None:
                    merged[key] = value
    
    # Take most severe degradation level
    degradation_levels = ["none", "degraded", "fallback", "failed"]
    all_degradations = [t.get("degradation_level", "none") for t in telemetry_dicts if t]
    max_degradation = "none"
    for level in reversed(degradation_levels):
        if level in all_degradations:
            max_degradation = level
            break
    merged["degradation_level"] = max_degradation
    
    return ensure_complete_telemetry(merged)


def compute_total_latency(*component_latencies: Optional[int]) -> int:
    """
    Compute total latency from component latencies.
    
    Args:
        *component_latencies: Variable number of latency values (ms)
        
    Returns:
        Total latency in milliseconds
        
    Example:
        >>> compute_total_latency(100, 50, None, 25)
        175
    """
    return sum(lat for lat in component_latencies if lat is not None)


def extract_standard_telemetry(
    trace_or_telemetry: Dict[str, Any],
    component: str = "unknown"
) -> Dict[str, Any]:
    """
    Extract standard telemetry fields from UnifiedTrace or legacy telemetry.
    
    Bridges between unified_trace.py format and legacy telemetry formats.
    
    Args:
        trace_or_telemetry: UnifiedTrace dict or legacy telemetry
        component: Component name for logging
        
    Returns:
        Standardized telemetry dict
    """
    # Check if it's a UnifiedTrace format (has 'operation_name')
    if "operation_name" in trace_or_telemetry:
        # Extract from UnifiedTrace
        trace = trace_or_telemetry
        return {
            "latency_ms_total": trace.get("duration_ms", 0),
            "latency_ms_retrieval": trace.get("latency_ms_retrieval", 0),
            "latency_ms_embedding": trace.get("latency_ms_embedding", 0),
            "latency_ms_llm": trace.get("latency_ms_llm", 0),
            "routing_decision": trace.get("routing_decision", component),
            "confidence_score": trace.get("confidence_score", 0.0),
            "cache_hit": trace.get("cache_hit", False),
            "retry_count": trace.get("retry_count", 0),
            "fallback_triggered": trace.get("fallback_triggered", False),
            "degradation_level": trace.get("degradation_level", "none"),
            "graceful_message": trace.get("graceful_message"),
            "error_class": trace.get("error_class"),
            "component": component
        }
    else:
        # Legacy telemetry format - ensure completeness
        return ensure_complete_telemetry(trace_or_telemetry)
