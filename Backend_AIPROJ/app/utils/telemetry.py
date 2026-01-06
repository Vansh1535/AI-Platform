"""
Central Telemetry and Observability Module

Provides unified telemetry tracking, structured logging, and graceful error handling
across all platform components (RAG, summarization, aggregation, CSV insights, agents).

Design Principles:
- Consistent telemetry fields across all endpoints
- Structured metadata for observability
- Zero user-facing stack traces
- Graceful degradation with meaningful messages
- Optional LLM support
- Comprehensive latency tracking

Telemetry Fields (Standardized):
- latency_ms_total: Total operation time
- latency_ms_retrieval: Vector search time
- latency_ms_embedding: Embedding generation time
- latency_ms_llm: LLM call time
- confidence_score: Result quality [0, 1]
- routing_decision: Which processing path taken
- fallback_triggered: Boolean if fallback used
- retry_count: Number of retries
- cache_hit: Boolean if cached
- degradation_level: none|mild|fallback|degraded|failed
- graceful_message: User-friendly message
- fallback_reason: Technical reason for fallback
"""

import time
import logging
import traceback
from typing import Dict, Any, Optional, Callable, Tuple
from enum import Enum
from functools import wraps
from app.utils.graceful_response import DegradationLevel, graceful_fallback, success_message

logger = logging.getLogger(__name__)


class ComponentType(str, Enum):
    """Platform component types for telemetry routing."""
    RAG_ASK = "rag_ask"
    RAG_SEARCH = "rag_search"
    SUMMARIZE = "summarize"
    AGGREGATE = "aggregate"
    CSV_INSIGHTS = "csv_insights"
    AGENT_RUN = "agent_run"


class TelemetryTracker:
    """
    Context manager for tracking operation telemetry.
    
    Usage:
        with TelemetryTracker(ComponentType.RAG_ASK) as tracker:
            # Do work
            tracker.set_retrieval_latency(50)
            tracker.set_confidence(0.85)
            result = perform_operation()
            
        telemetry = tracker.get_telemetry()
    """
    
    def __init__(self, component: ComponentType, operation_id: Optional[str] = None):
        self.component = component
        self.operation_id = operation_id
        self.start_time = None
        self.telemetry = self._initialize_telemetry()
        
    def _initialize_telemetry(self) -> Dict[str, Any]:
        """Initialize telemetry with default values."""
        return {
            "component": self.component.value,
            "operation_id": self.operation_id,
            "latency_ms_total": 0,
            "latency_ms_retrieval": None,
            "latency_ms_embedding": None,
            "latency_ms_llm": None,
            "confidence_score": None,
            "routing_decision": None,
            "fallback_triggered": False,
            "retry_count": 0,
            "cache_hit": False,
            "degradation_level": DegradationLevel.NONE.value,
            "graceful_message": None,
            "fallback_reason": None,
            "error_type": None
        }
    
    def __enter__(self):
        """Start tracking."""
        self.start_time = time.time()
        logger.info(f"Starting operation - component={self.component.value}, id={self.operation_id}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Complete tracking and log summary."""
        if self.start_time:
            total_latency = int((time.time() - self.start_time) * 1000)
            self.telemetry["latency_ms_total"] = total_latency
        
        # Log completion
        if exc_type:
            logger.error(
                f"Operation failed - component={self.component.value}, "
                f"error={exc_type.__name__}, latency={self.telemetry['latency_ms_total']}ms"
            )
            self.telemetry["error_type"] = exc_type.__name__
        else:
            logger.info(
                f"Operation complete - component={self.component.value}, "
                f"degradation={self.telemetry['degradation_level']}, "
                f"latency={self.telemetry['latency_ms_total']}ms"
            )
        
        return False  # Don't suppress exceptions
    
    def set_retrieval_latency(self, ms: int):
        """Set retrieval latency."""
        self.telemetry["latency_ms_retrieval"] = ms
    
    def set_embedding_latency(self, ms: int):
        """Set embedding generation latency."""
        self.telemetry["latency_ms_embedding"] = ms
    
    def set_llm_latency(self, ms: int):
        """Set LLM call latency."""
        self.telemetry["latency_ms_llm"] = ms
    
    def set_confidence(self, score: float):
        """Set confidence score [0, 1]."""
        self.telemetry["confidence_score"] = round(score, 3) if score is not None else None
    
    def set_routing(self, decision: str):
        """Set routing decision."""
        self.telemetry["routing_decision"] = decision
    
    def trigger_fallback(self, reason: str):
        """Mark fallback triggered."""
        self.telemetry["fallback_triggered"] = True
        self.telemetry["fallback_reason"] = reason
        logger.warning(f"Fallback triggered - component={self.component.value}, reason={reason}")
    
    def increment_retry(self):
        """Increment retry count."""
        self.telemetry["retry_count"] += 1
    
    def set_cache_hit(self, hit: bool):
        """Mark cache hit/miss."""
        self.telemetry["cache_hit"] = hit
    
    def set_degradation(self, level: DegradationLevel, message: str, reason: Optional[str] = None):
        """Set degradation level with user message."""
        self.telemetry["degradation_level"] = level.value
        self.telemetry["graceful_message"] = message
        if reason:
            self.telemetry["fallback_reason"] = reason
        
        logger.info(
            f"Degradation set - component={self.component.value}, "
            f"level={level.value}, reason={reason}"
        )
    
    def get_telemetry(self) -> Dict[str, Any]:
        """Get current telemetry snapshot."""
        return self.telemetry.copy()
    
    def merge_telemetry(self, other: Dict[str, Any]):
        """Merge additional telemetry fields."""
        for key, value in other.items():
            if key not in self.telemetry or self.telemetry[key] is None:
                self.telemetry[key] = value


def with_telemetry(component: ComponentType):
    """
    Decorator for adding telemetry tracking to functions.
    
    Usage:
        @with_telemetry(ComponentType.RAG_ASK)
        def ask_question(query: str) -> Tuple[Dict, Dict]:
            # Function must return (result, telemetry)
            result = {"answer": "..."}
            telemetry = {"confidence_score": 0.9}
            return result, telemetry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            with TelemetryTracker(component) as tracker:
                try:
                    # Call function - expect (result, telemetry) return
                    result, func_telemetry = func(*args, **kwargs)
                    
                    # Merge function telemetry
                    tracker.merge_telemetry(func_telemetry)
                    
                    # Ensure graceful message if degraded
                    if tracker.telemetry["degradation_level"] != DegradationLevel.NONE.value:
                        if not tracker.telemetry["graceful_message"]:
                            tracker.set_degradation(
                                DegradationLevel(tracker.telemetry["degradation_level"]),
                                "Operation completed with limitations.",
                                tracker.telemetry.get("fallback_reason")
                            )
                    
                    return result, tracker.get_telemetry()
                    
                except Exception as e:
                    # Handle unexpected errors gracefully
                    logger.error(f"Unexpected error in {component.value}: {str(e)}")
                    logger.debug(traceback.format_exc())
                    
                    tracker.set_degradation(
                        DegradationLevel.FAILED,
                        "An unexpected issue occurred during processing.",
                        f"error_{type(e).__name__}"
                    )
                    
                    # Return empty result with error telemetry
                    return {}, tracker.get_telemetry()
        
        return wrapper
    return decorator


def safe_execute(
    operation: Callable,
    component: ComponentType,
    fallback_value: Any,
    timeout_seconds: Optional[int] = None,
    max_retries: int = 0
) -> Tuple[Any, Dict[str, Any]]:
    """
    Execute operation with timeout, retry, and graceful error handling.
    
    Args:
        operation: Function to execute
        component: Component type for telemetry
        fallback_value: Value to return on failure
        timeout_seconds: Optional timeout
        max_retries: Number of retries on failure
        
    Returns:
        Tuple of (result, telemetry)
    """
    with TelemetryTracker(component) as tracker:
        last_error = None
        
        for attempt in range(max_retries + 1):
            if attempt > 0:
                tracker.increment_retry()
                logger.info(f"Retry attempt {attempt}/{max_retries}")
            
            try:
                # Execute with optional timeout
                if timeout_seconds:
                    import signal
                    
                    def timeout_handler(signum, frame):
                        raise TimeoutError(f"Operation exceeded {timeout_seconds}s timeout")
                    
                    # Set timeout (Unix-like systems)
                    try:
                        signal.signal(signal.SIGALRM, timeout_handler)
                        signal.alarm(timeout_seconds)
                        result = operation()
                        signal.alarm(0)  # Clear alarm
                        return result, tracker.get_telemetry()
                    except AttributeError:
                        # Windows doesn't support SIGALRM, fall through to no-timeout
                        result = operation()
                        return result, tracker.get_telemetry()
                else:
                    result = operation()
                    return result, tracker.get_telemetry()
                    
            except TimeoutError as e:
                last_error = e
                tracker.trigger_fallback("timeout")
                logger.warning(f"Operation timeout on attempt {attempt + 1}")
                
            except Exception as e:
                last_error = e
                tracker.trigger_fallback(f"error_{type(e).__name__}")
                logger.warning(f"Operation failed on attempt {attempt + 1}: {str(e)}")
        
        # All retries exhausted, return fallback
        tracker.set_degradation(
            DegradationLevel.FAILED,
            "The operation could not be completed.",
            tracker.telemetry["fallback_reason"]
        )
        
        return fallback_value, tracker.get_telemetry()


def ensure_telemetry_fields(telemetry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure all required telemetry fields are present with valid values.
    
    Args:
        telemetry: Partial telemetry dict
        
    Returns:
        Complete telemetry dict with all required fields
    """
    required_fields = {
        "latency_ms_total": 0,
        "latency_ms_retrieval": None,
        "latency_ms_embedding": None,
        "latency_ms_llm": None,
        "confidence_score": None,
        "routing_decision": None,
        "fallback_triggered": False,
        "retry_count": 0,
        "cache_hit": False,
        "degradation_level": DegradationLevel.NONE.value,
        "graceful_message": None,
        "fallback_reason": None
    }
    
    # Start with defaults
    complete = required_fields.copy()
    
    # Override with provided values
    complete.update({k: v for k, v in telemetry.items() if v is not None})
    
    return complete


def handle_embedding_failure(
    component: ComponentType,
    fallback_operation: Optional[Callable] = None
) -> Tuple[Any, Dict[str, Any]]:
    """
    Handle embedding service failure gracefully.
    
    Args:
        component: Component type
        fallback_operation: Optional extractive fallback
        
    Returns:
        Tuple of (result, telemetry)
    """
    tracker = TelemetryTracker(component)
    tracker.trigger_fallback("embedding_unavailable")
    tracker.set_routing("extractive_fallback")
    
    if fallback_operation:
        try:
            result = fallback_operation()
            tracker.set_degradation(
                DegradationLevel.FALLBACK,
                "Results generated without semantic search.",
                "embedding_unavailable"
            )
            return result, tracker.get_telemetry()
        except Exception as e:
            logger.error(f"Fallback operation also failed: {str(e)}")
    
    tracker.set_degradation(
        DegradationLevel.FAILED,
        "The operation could not be completed without semantic search.",
        "embedding_unavailable"
    )
    
    return None, tracker.get_telemetry()


def handle_vectordb_failure(
    component: ComponentType,
    fallback_operation: Optional[Callable] = None
) -> Tuple[Any, Dict[str, Any]]:
    """
    Handle vector database unavailability.
    
    Args:
        component: Component type
        fallback_operation: Optional keyword-based fallback
        
    Returns:
        Tuple of (result, telemetry)
    """
    tracker = TelemetryTracker(component)
    tracker.trigger_fallback("vectordb_unavailable")
    tracker.set_routing("keyword_fallback")
    
    if fallback_operation:
        try:
            result = fallback_operation()
            tracker.set_degradation(
                DegradationLevel.DEGRADED,
                "Results may be less accurate due to system limitations.",
                "vectordb_unavailable"
            )
            return result, tracker.get_telemetry()
        except Exception as e:
            logger.error(f"Fallback operation also failed: {str(e)}")
    
    tracker.set_degradation(
        DegradationLevel.FAILED,
        "The search service is currently unavailable.",
        "vectordb_unavailable"
    )
    
    return None, tracker.get_telemetry()


def merge_telemetry(*telemetries: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge multiple telemetry dicts, summing latencies and preserving other fields.
    
    Args:
        *telemetries: Variable number of telemetry dicts
        
    Returns:
        Merged telemetry dict
    """
    merged = ensure_telemetry_fields({})
    
    # Sum latencies
    latency_fields = [
        "latency_ms_total",
        "latency_ms_retrieval",
        "latency_ms_embedding",
        "latency_ms_llm"
    ]
    
    for t in telemetries:
        for field in latency_fields:
            if field in t and t[field] is not None:
                if merged[field] is None:
                    merged[field] = 0
                merged[field] += t[field]
        
        # Take highest degradation level
        if t.get("degradation_level"):
            current_level = DegradationLevel(merged["degradation_level"])
            new_level = DegradationLevel(t["degradation_level"])
            
            level_order = {
                DegradationLevel.NONE: 0,
                DegradationLevel.MILD: 1,
                DegradationLevel.FALLBACK: 2,
                DegradationLevel.DEGRADED: 3,
                DegradationLevel.FAILED: 4
            }
            
            if level_order[new_level] > level_order[current_level]:
                merged["degradation_level"] = new_level.value
                merged["graceful_message"] = t.get("graceful_message")
                merged["fallback_reason"] = t.get("fallback_reason")
        
        # Take max retry count
        if t.get("retry_count", 0) > merged["retry_count"]:
            merged["retry_count"] = t["retry_count"]
        
        # OR boolean fields
        merged["fallback_triggered"] = merged["fallback_triggered"] or t.get("fallback_triggered", False)
        merged["cache_hit"] = merged["cache_hit"] or t.get("cache_hit", False)
        
        # Take first non-null routing decision
        if not merged["routing_decision"] and t.get("routing_decision"):
            merged["routing_decision"] = t["routing_decision"]
        
        # Take minimum confidence score (most conservative)
        if t.get("confidence_score") is not None:
            if merged["confidence_score"] is None:
                merged["confidence_score"] = t["confidence_score"]
            else:
                merged["confidence_score"] = min(merged["confidence_score"], t["confidence_score"])
    
    return merged
