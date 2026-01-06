"""
Telemetry Context — Context manager for tracking operation observability.

Usage:
    with TelemetryContext("csv_insights") as ctx:
        # Do work
        ctx.record_latency("retrieval", 150)
        ctx.set_confidence(0.85)
        
        # Get complete telemetry
        telemetry = ctx.get_telemetry()
"""

import time
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
from datetime import datetime
from app.core.logging import setup_logger
from app.core.telemetry import ensure_complete_telemetry

logger = setup_logger("INFO")


class TelemetryContext:
    """
    Context manager for tracking operation telemetry.
    
    Automatically tracks:
    - Operation start/end time
    - Latency measurements
    - Routing decisions
    - Fallback triggers
    - Degradation levels
    
    Usage:
        with TelemetryContext("operation_name") as ctx:
            # Do work
            ctx.record_latency("retrieval", 100)
            ctx.set_routing("rag_hybrid")
            ctx.set_confidence(0.9)
            
            if fallback_occurred:
                ctx.trigger_fallback("LLM unavailable")
            
            telemetry = ctx.get_telemetry()
    """
    
    def __init__(
        self,
        operation: str,
        initial_telemetry: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize telemetry context.
        
        Args:
            operation: Operation name (e.g., "csv_insights", "rag_query")
            initial_telemetry: Optional initial telemetry dict
        """
        self.operation = operation
        self.start_time = None
        self.end_time = None
        
        # Initialize telemetry with defaults
        self.telemetry: Dict[str, Any] = initial_telemetry or {}
        
        # Set defaults if not present
        if "latency_ms_total" not in self.telemetry:
            self.telemetry["latency_ms_total"] = 0
        if "latency_ms_retrieval" not in self.telemetry:
            self.telemetry["latency_ms_retrieval"] = 0
        if "latency_ms_embedding" not in self.telemetry:
            self.telemetry["latency_ms_embedding"] = 0
        if "latency_ms_llm" not in self.telemetry:
            self.telemetry["latency_ms_llm"] = 0
        if "routing_decision" not in self.telemetry:
            self.telemetry["routing_decision"] = "unknown"
        if "confidence_score" not in self.telemetry:
            self.telemetry["confidence_score"] = 0.0
        if "cache_hit" not in self.telemetry:
            self.telemetry["cache_hit"] = False
        if "retry_count" not in self.telemetry:
            self.telemetry["retry_count"] = 0
        if "fallback_triggered" not in self.telemetry:
            self.telemetry["fallback_triggered"] = False
        if "degradation_level" not in self.telemetry:
            self.telemetry["degradation_level"] = "none"
        if "graceful_message" not in self.telemetry:
            self.telemetry["graceful_message"] = ""
    
    def __enter__(self):
        """Start tracking operation."""
        self.start_time = time.time()
        logger.debug(f"Starting telemetry tracking for: {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Complete tracking and finalize telemetry."""
        self.end_time = time.time()
        
        # Calculate total latency if not already set
        if self.start_time and self.telemetry["latency_ms_total"] == 0:
            self.telemetry["latency_ms_total"] = int(
                (self.end_time - self.start_time) * 1000
            )
        
        # Handle exceptions
        if exc_type is not None:
            self.telemetry["fallback_triggered"] = True
            self.telemetry["degradation_level"] = "failed"
            self.telemetry["graceful_message"] = f"Operation failed: {str(exc_val)}"
            logger.error(f"Operation {self.operation} failed: {exc_val}")
        
        logger.debug(
            f"Completed telemetry tracking for {self.operation}: "
            f"{self.telemetry['latency_ms_total']}ms, "
            f"degradation={self.telemetry['degradation_level']}"
        )
        
        # Don't suppress exceptions
        return False
    
    def record_latency(self, component: str, latency_ms: int):
        """
        Record component latency.
        
        Args:
            component: Component name (retrieval, embedding, llm, total)
            latency_ms: Latency in milliseconds
        """
        key = f"latency_ms_{component}"
        self.telemetry[key] = latency_ms
        
        # Auto-update total if components provided
        if component != "total":
            component_latencies = [
                self.telemetry.get("latency_ms_retrieval", 0),
                self.telemetry.get("latency_ms_embedding", 0),
                self.telemetry.get("latency_ms_llm", 0)
            ]
            total = sum(component_latencies)
            if total > 0:
                self.telemetry["latency_ms_total"] = total
    
    def set_routing(self, routing: str):
        """Set routing decision."""
        self.telemetry["routing_decision"] = routing
    
    def set_confidence(self, confidence: float):
        """Set confidence score (0.0 to 1.0)."""
        self.telemetry["confidence_score"] = max(0.0, min(1.0, confidence))
    
    def set_cache_hit(self, hit: bool):
        """Mark whether cache was hit."""
        self.telemetry["cache_hit"] = hit
    
    def increment_retry(self):
        """Increment retry count."""
        self.telemetry["retry_count"] = self.telemetry.get("retry_count", 0) + 1
    
    def trigger_fallback(self, reason: str):
        """
        Trigger fallback with reason.
        
        Args:
            reason: Why fallback was triggered
        """
        self.telemetry["fallback_triggered"] = True
        if self.telemetry["degradation_level"] == "none":
            self.telemetry["degradation_level"] = "degraded"
        self.telemetry["graceful_message"] = reason
    
    def set_degradation(self, level: str, message: str = ""):
        """
        Set degradation level.
        
        Args:
            level: Degradation level (none, mild, degraded, failed)
            message: Optional user-facing message
        """
        valid_levels = ["none", "mild", "degraded", "failed"]
        if level not in valid_levels:
            logger.warning(f"Invalid degradation level: {level}, defaulting to 'none'")
            level = "none"
        
        self.telemetry["degradation_level"] = level
        if message:
            self.telemetry["graceful_message"] = message
    
    def update(self, telemetry: Dict[str, Any]):
        """
        Update telemetry with additional fields.
        
        Args:
            telemetry: Dict of telemetry fields to add/update
        """
        self.telemetry.update(telemetry)
    
    def get_telemetry(self) -> Dict[str, Any]:
        """
        Get complete telemetry dict.
        
        Returns:
            Complete telemetry with all required fields
        """
        # Ensure completeness before returning
        return ensure_complete_telemetry(self.telemetry)


@contextmanager
def track_operation(
    operation: str,
    initial_telemetry: Optional[Dict[str, Any]] = None
):
    """
    Context manager for tracking operation telemetry.
    
    Args:
        operation: Operation name
        initial_telemetry: Optional initial telemetry
        
    Yields:
        TelemetryContext instance
        
    Example:
        with track_operation("rag_query") as ctx:
            # Do work
            ctx.record_latency("retrieval", 100)
            result = {"answer": "..."}
            return result, ctx.get_telemetry()
    """
    with TelemetryContext(operation, initial_telemetry) as ctx:
        yield ctx


def get_current_telemetry(ctx: TelemetryContext) -> Dict[str, Any]:
    """
    Get current telemetry from context (non-finalized).
    
    Args:
        ctx: Telemetry context
        
    Returns:
        Current telemetry dict
    """
    return ctx.telemetry.copy()


def finalize_telemetry(
    ctx: TelemetryContext,
    success: bool = True,
    message: str = ""
) -> Dict[str, Any]:
    """
    Finalize telemetry with success/failure status.
    
    Args:
        ctx: Telemetry context
        success: Whether operation succeeded
        message: Optional message
        
    Returns:
        Complete finalized telemetry
    """
    if not success:
        ctx.telemetry["fallback_triggered"] = True
        ctx.telemetry["degradation_level"] = "failed"
        if message:
            ctx.telemetry["graceful_message"] = message
    
    return ctx.get_telemetry()


def merge_telemetry_contexts(
    contexts: List[TelemetryContext],
    operation: str = "merged"
) -> Dict[str, Any]:
    """
    Merge multiple telemetry contexts into one.
    
    Useful for multi-step operations that need combined telemetry.
    
    Args:
        contexts: List of telemetry contexts
        operation: Name for merged operation
        
    Returns:
        Merged telemetry dict
    """
    if not contexts:
        return ensure_complete_telemetry({})
    
    merged = TelemetryContext(operation)
    
    # Sum latencies
    total_retrieval = sum(ctx.telemetry.get("latency_ms_retrieval", 0) for ctx in contexts)
    total_embedding = sum(ctx.telemetry.get("latency_ms_embedding", 0) for ctx in contexts)
    total_llm = sum(ctx.telemetry.get("latency_ms_llm", 0) for ctx in contexts)
    
    merged.record_latency("retrieval", total_retrieval)
    merged.record_latency("embedding", total_embedding)
    merged.record_latency("llm", total_llm)
    merged.record_latency("total", total_retrieval + total_embedding + total_llm)
    
    # OR boolean fields
    merged.telemetry["cache_hit"] = any(ctx.telemetry.get("cache_hit", False) for ctx in contexts)
    merged.telemetry["fallback_triggered"] = any(ctx.telemetry.get("fallback_triggered", False) for ctx in contexts)
    
    # Max retry count
    merged.telemetry["retry_count"] = max(ctx.telemetry.get("retry_count", 0) for ctx in contexts)
    
    # Average confidence
    confidences = [ctx.telemetry.get("confidence_score", 0.0) for ctx in contexts]
    merged.set_confidence(sum(confidences) / len(confidences) if confidences else 0.0)
    
    # Worst degradation level
    degradation_order = ["none", "mild", "degraded", "failed"]
    worst_degradation = max(
        (ctx.telemetry.get("degradation_level", "none") for ctx in contexts),
        key=lambda x: degradation_order.index(x) if x in degradation_order else 0
    )
    merged.telemetry["degradation_level"] = worst_degradation
    
    # Combine graceful messages
    messages = [ctx.telemetry.get("graceful_message", "") for ctx in contexts if ctx.telemetry.get("graceful_message")]
    if messages:
        merged.telemetry["graceful_message"] = "; ".join(messages)
    
    # Combine routing decisions
    routings = [ctx.telemetry.get("routing_decision", "") for ctx in contexts if ctx.telemetry.get("routing_decision") != "unknown"]
    if routings:
        merged.telemetry["routing_decision"] = " → ".join(routings)
    
    return merged.get_telemetry()
