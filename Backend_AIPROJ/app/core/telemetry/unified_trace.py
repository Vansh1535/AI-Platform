"""
Unified Trace — Phase 3

Shared helper module for consistent telemetry and reliability across all pipelines.
Provides structured tracing, error handling, and response finalization.

Key Features:
- Consistent telemetry structure across all components
- Safe error handling with graceful degradation
- Automatic metadata tracking
- Response finalization with telemetry injection

Usage:
    from app.core.telemetry.unified_trace import start_trace, end_trace, finalize_response
    
    trace = start_trace("rag_ask")
    try:
        result = perform_operation()
        end_trace(trace, success=True)
        return finalize_response(result, trace)
    except Exception as e:
        end_trace(trace, success=False, error=e)
        return finalize_response(fallback_result, trace, degradation="failed")
"""

import time
import traceback
from typing import Dict, Any, Optional, Callable
from app.core.logging import setup_logger

logger = setup_logger("INFO")


class UnifiedTrace:
    """
    Structured trace object for tracking operation telemetry.
    
    Automatically tracks timing, steps, metadata, and errors.
    """
    
    def __init__(self, operation_name: str):
        """
        Initialize a new trace.
        
        Args:
            operation_name: Name of the operation being traced
        """
        self.operation_name = operation_name
        self.start_time = time.time()
        self.end_time = None
        self.success = None
        self.error = None
        self.steps = {}
        self.metadata = {
            "operation": operation_name,
            "latency_ms_total": 0,
            "latency_ms_retrieval": 0,
            "latency_ms_embedding": 0,
            "latency_ms_llm": 0,
            "routing_decision": None,
            "confidence_score": None,
            "fallback_triggered": False,
            "retry_count": 0,
            "cache_hit": False,
            "degradation_level": "none",
            "graceful_message": None,
            "error_class": None
        }
    
    def record_step(self, step_name: str, latency_ms: int):
        """
        Record a step in the operation with its latency.
        
        Args:
            step_name: Name of the step (e.g., "retrieval", "embedding", "llm")
            latency_ms: Latency in milliseconds
        """
        self.steps[step_name] = latency_ms
        
        # Update standard latency fields
        if step_name == "retrieval":
            self.metadata["latency_ms_retrieval"] = latency_ms
        elif step_name == "embedding":
            self.metadata["latency_ms_embedding"] = latency_ms
        elif step_name == "llm":
            self.metadata["latency_ms_llm"] = latency_ms
        
        logger.debug(f"Trace [{self.operation_name}] - Step '{step_name}': {latency_ms}ms")
    
    def attach_metadata(self, **meta):
        """
        Attach additional metadata to the trace.
        
        Args:
            **meta: Key-value pairs to add to metadata
        """
        for key, value in meta.items():
            if value is not None:
                self.metadata[key] = value
    
    def finalize(self, success: bool = True, error: Optional[Exception] = None):
        """
        Finalize the trace and calculate total latency.
        
        Args:
            success: Whether the operation succeeded
            error: Exception if operation failed
        """
        self.end_time = time.time()
        self.success = success
        self.error = error
        
        # Calculate total latency
        total_latency_ms = int((self.end_time - self.start_time) * 1000)
        self.metadata["latency_ms_total"] = total_latency_ms
        
        # Set error class if failed
        if error:
            self.metadata["error_class"] = type(error).__name__
            
            # Set degradation if not already set
            if self.metadata["degradation_level"] == "none":
                self.metadata["degradation_level"] = "failed"
        
        logger.info(
            f"Trace [{self.operation_name}] completed - "
            f"Success: {success}, Latency: {total_latency_ms}ms, "
            f"Degradation: {self.metadata['degradation_level']}"
        )
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get the complete metadata dictionary.
        
        Returns:
            Dictionary with all telemetry fields
        """
        return self.metadata.copy()


def start_trace(operation_name: str) -> UnifiedTrace:
    """
    Start a new trace for an operation.
    
    Args:
        operation_name: Name of the operation (e.g., "rag_ask", "summarize")
        
    Returns:
        UnifiedTrace object
        
    Example:
        trace = start_trace("rag_ask")
        # ... perform operation ...
        end_trace(trace, success=True)
    """
    trace = UnifiedTrace(operation_name)
    logger.debug(f"Started trace: {operation_name}")
    return trace


def end_trace(trace: UnifiedTrace, success: bool = True, error: Optional[Exception] = None):
    """
    End a trace and finalize telemetry.
    
    Args:
        trace: The trace object to finalize
        success: Whether the operation succeeded
        error: Exception if operation failed
        
    Example:
        try:
            result = operation()
            end_trace(trace, success=True)
        except Exception as e:
            end_trace(trace, success=False, error=e)
    """
    trace.finalize(success=success, error=error)


def record_step(trace: UnifiedTrace, step_name: str, latency_ms: int):
    """
    Record a step in the trace with its latency.
    
    Args:
        trace: The trace object
        step_name: Name of the step (e.g., "retrieval", "embedding", "llm")
        latency_ms: Latency in milliseconds
        
    Example:
        start_time = time.time()
        results = search(query)
        latency = int((time.time() - start_time) * 1000)
        record_step(trace, "retrieval", latency)
    """
    trace.record_step(step_name, latency_ms)


def attach_metadata(trace: UnifiedTrace, **meta):
    """
    Attach additional metadata to the trace.
    
    Args:
        trace: The trace object
        **meta: Key-value pairs to add to metadata
        
    Example:
        attach_metadata(trace, 
            routing_decision="semantic_search",
            confidence_score=0.85,
            cache_hit=True
        )
    """
    trace.attach_metadata(**meta)


def finalize_response(
    payload: Dict[str, Any],
    trace: UnifiedTrace,
    graceful_message: Optional[str] = None,
    degradation: Optional[str] = None
) -> Dict[str, Any]:
    """
    Finalize a response by injecting telemetry metadata.
    
    Args:
        payload: The response payload (data)
        trace: The trace object with telemetry
        graceful_message: Optional user-friendly message
        degradation: Optional degradation level override
        
    Returns:
        Response with metadata injected
        
    Example:
        result = {"answer": "...", "citations": [...]}
        return finalize_response(result, trace, 
            graceful_message="Answer generated successfully",
            degradation="none"
        )
    """
    # Update graceful message if provided
    if graceful_message:
        trace.attach_metadata(graceful_message=graceful_message)
    
    # Update degradation if provided
    if degradation:
        trace.attach_metadata(degradation_level=degradation)
    
    # Inject metadata into response
    response = {
        **payload,
        "meta": trace.get_metadata()
    }
    
    return response


def safe_try(
    step_name: str,
    trace: UnifiedTrace,
    fn: Callable,
    fallback_value: Any = None,
    fallback_message: str = None
) -> Any:
    """
    Execute a function with safe error handling and telemetry tracking.
    
    If the function fails, returns fallback_value and marks trace as degraded.
    Always returns structured result - never raises exceptions to caller.
    
    Args:
        step_name: Name of the step being executed
        trace: The trace object
        fn: Function to execute
        fallback_value: Value to return if function fails
        fallback_message: User-friendly message for failure
        
    Returns:
        Function result or fallback_value if failed
        
    Example:
        embeddings = safe_try(
            "embedding_generation",
            trace,
            lambda: generate_embeddings(text),
            fallback_value=None,
            fallback_message="Embedding service unavailable, using keyword search"
        )
        
        if embeddings is None:
            # Use fallback search method
            results = keyword_search(text)
            attach_metadata(trace, fallback_triggered=True, routing_decision="keyword_search")
    """
    step_start = time.time()
    
    try:
        result = fn()
        latency_ms = int((time.time() - step_start) * 1000)
        record_step(trace, step_name, latency_ms)
        return result
        
    except Exception as e:
        latency_ms = int((time.time() - step_start) * 1000)
        record_step(trace, step_name, latency_ms)
        
        logger.warning(
            f"Trace [{trace.operation_name}] - Step '{step_name}' failed: {str(e)}",
            exc_info=False  # Don't log full traceback
        )
        
        # Mark trace as degraded
        trace.attach_metadata(
            fallback_triggered=True,
            degradation_level="fallback",
            error_class=type(e).__name__
        )
        
        if fallback_message:
            trace.attach_metadata(graceful_message=fallback_message)
        
        return fallback_value


def ensure_telemetry_fields(metadata: Dict[str, Any]):
    """
    Ensure all required telemetry fields are present with defaults.
    
    Modifies metadata dict in-place.
    
    Args:
        metadata: Partial metadata dictionary (modified in-place)
        
    Example:
        # Merge external telemetry with trace telemetry
        external_meta = {"confidence": 0.8, "chunks": 5}
        ensure_telemetry_fields(external_meta)
        # Now external_meta has all required fields
    """
    defaults = {
        "latency_ms_total": 0,
        "latency_ms_retrieval": 0,
        "latency_ms_embedding": 0,
        "latency_ms_llm": 0,
        "routing_decision": None,
        "confidence_score": None,
        "fallback_triggered": False,
        "retry_count": 0,
        "cache_hit": False,
        "degradation_level": "none",
        "graceful_message": None,
        "error_class": None
    }
    
    # Add missing fields with defaults
    for key, default_value in defaults.items():
        if key not in metadata:
            metadata[key] = default_value


def merge_trace_metadata(trace: UnifiedTrace, external_meta: Dict[str, Any]):
    """
    Merge trace metadata with external metadata (e.g., from service calls).
    
    Takes the more severe degradation level and sums latencies.
    Modifies trace in-place.
    
    Args:
        trace: The trace object (modified in-place)
        external_meta: External metadata to merge
        
    Example:
        # Merge LLM service telemetry with trace
        llm_meta = {"latency_ms_llm": 1200, "confidence_score": 0.9}
        merge_trace_metadata(trace, llm_meta)
        # Now trace has updated metadata
    """
    # Merge latencies (sum them)
    latency_fields = ["latency_ms_retrieval", "latency_ms_embedding", "latency_ms_llm"]
    for field in latency_fields:
        if field in external_meta and external_meta[field]:
            current_value = trace.metadata.get(field, 0) or 0
            trace.metadata[field] = current_value + external_meta[field]
    
    # Take more severe degradation
    degradation_order = ["none", "mild", "fallback", "degraded", "failed"]
    trace_deg = trace.metadata.get("degradation_level", "none")
    external_deg = external_meta.get("degradation_level", "none")
    
    if degradation_order.index(external_deg) > degradation_order.index(trace_deg):
        trace.metadata["degradation_level"] = external_deg
        if external_meta.get("graceful_message"):
            trace.metadata["graceful_message"] = external_meta["graceful_message"]
    
    # Merge other fields (prefer external if set)
    for key, value in external_meta.items():
        if value is not None and key not in latency_fields:
            if key not in ["degradation_level", "graceful_message"]:  # Already handled
                trace.metadata[key] = value


# Context manager for automatic trace lifecycle
class trace_operation:
    """
    Context manager for automatic trace lifecycle management.
    
    Example:
        with trace_operation("rag_ask") as trace:
            results = search(query)
            record_step(trace, "retrieval", 150)
            answer = generate_answer(results)
            record_step(trace, "llm", 1200)
            # Trace automatically finalized on exit
    """
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.trace = None
    
    def __enter__(self) -> UnifiedTrace:
        self.trace = start_trace(self.operation_name)
        return self.trace
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Exception occurred
            end_trace(self.trace, success=False, error=exc_val)
            # Don't suppress exception
            return False
        else:
            # Success
            end_trace(self.trace, success=True)
            return False
