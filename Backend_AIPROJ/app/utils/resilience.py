"""
Resilience and Fault Tolerance Module

Provides resilient wrappers for common failure scenarios across the platform:
- Timeout handling
- Embedding service failures
- Vector DB unavailability
- Partial failures in multi-step operations
- Weak signal degradation

Design Principles:
- Fail gracefully, never silently
- Always return usable output (even if degraded)
- Preserve metadata for debugging
- No user-facing stack traces
- LLM remains optional
"""

import logging
import functools
from typing import Callable, Any, Optional, Tuple, Dict
from app.utils.telemetry import (
    TelemetryTracker,
    ComponentType,
    DegradationLevel,
    ensure_telemetry_fields
)

logger = logging.getLogger(__name__)


def resilient_operation(
    component: ComponentType,
    fallback_value: Any = None,
    fallback_message: str = "Operation completed with limitations.",
    timeout_seconds: Optional[int] = None
):
    """
    Decorator for making operations resilient to failures.
    
    Handles:
    - Exceptions → graceful fallback
    - Timeouts → degraded response
    - Partial failures → best-effort output
    
    Usage:
        @resilient_operation(ComponentType.RAG_ASK, fallback_value={})
        def ask_question(query: str) -> Tuple[Dict, Dict]:
            result = {"answer": "..."}
            telemetry = {}
            return result, telemetry
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with TelemetryTracker(component) as tracker:
                try:
                    # Execute function
                    result, telemetry = func(*args, **kwargs)
                    
                    # Merge telemetry
                    tracker.merge_telemetry(telemetry)
                    
                    return result, tracker.get_telemetry()
                    
                except TimeoutError as e:
                    logger.warning(f"Timeout in {component.value}: {str(e)}")
                    tracker.trigger_fallback("timeout")
                    tracker.set_degradation(
                        DegradationLevel.DEGRADED,
                        "Operation timed out. Returning partial results.",
                        "timeout"
                    )
                    return fallback_value, tracker.get_telemetry()
                    
                except Exception as e:
                    logger.error(f"Error in {component.value}: {str(e)}")
                    logger.debug(f"Stack trace:", exc_info=True)
                    
                    tracker.trigger_fallback(f"error_{type(e).__name__}")
                    tracker.set_degradation(
                        DegradationLevel.FAILED,
                        fallback_message,
                        f"error_{type(e).__name__}"
                    )
                    return fallback_value, tracker.get_telemetry()
        
        return wrapper
    return decorator


class EmbeddingFallbackHandler:
    """
    Handles embedding service failures with extractive fallbacks.
    
    Usage:
        handler = EmbeddingFallbackHandler(ComponentType.RAG_SEARCH)
        
        with handler as h:
            try:
                embeddings = generate_embeddings(texts)
                results = vector_search(embeddings)
            except EmbeddingError:
                h.trigger_fallback()
                results = h.extractive_fallback(texts)
        
        result, telemetry = handler.get_result(results)
    """
    
    def __init__(self, component: ComponentType):
        self.component = component
        self.tracker = TelemetryTracker(component)
        self.fallback_used = False
    
    def __enter__(self):
        self.tracker.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.tracker.__exit__(exc_type, exc_val, exc_tb)
    
    def trigger_fallback(self, reason: str = "embedding_unavailable"):
        """Trigger extractive fallback mode."""
        self.fallback_used = True
        self.tracker.trigger_fallback(reason)
        self.tracker.set_routing("extractive_fallback")
        logger.info(f"Embedding fallback triggered - component={self.component.value}, reason={reason}")
    
    def set_success(self):
        """Mark operation as successful."""
        self.tracker.set_routing("semantic_search")
    
    def get_result(self, data: Any) -> Tuple[Any, Dict[str, Any]]:
        """Get result with telemetry."""
        if self.fallback_used:
            self.tracker.set_degradation(
                DegradationLevel.FALLBACK,
                "Results generated without semantic analysis.",
                self.tracker.telemetry.get("fallback_reason", "embedding_unavailable")
            )
        
        return data, self.tracker.get_telemetry()


class VectorDBFallbackHandler:
    """
    Handles vector database unavailability with keyword-based fallback.
    
    Usage:
        handler = VectorDBFallbackHandler(ComponentType.RAG_ASK)
        
        with handler as h:
            try:
                results = vectordb.search(query)
                h.set_success()
            except VectorDBError:
                h.trigger_fallback()
                results = keyword_search(query)
        
        result, telemetry = handler.get_result(results)
    """
    
    def __init__(self, component: ComponentType):
        self.component = component
        self.tracker = TelemetryTracker(component)
        self.fallback_used = False
    
    def __enter__(self):
        self.tracker.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.tracker.__exit__(exc_type, exc_val, exc_tb)
    
    def trigger_fallback(self, reason: str = "vectordb_unavailable"):
        """Trigger keyword-based fallback."""
        self.fallback_used = True
        self.tracker.trigger_fallback(reason)
        self.tracker.set_routing("keyword_fallback")
        logger.warning(f"VectorDB fallback triggered - component={self.component.value}, reason={reason}")
    
    def set_success(self):
        """Mark operation as successful."""
        self.tracker.set_routing("vector_search")
    
    def get_result(self, data: Any) -> Tuple[Any, Dict[str, Any]]:
        """Get result with telemetry."""
        if self.fallback_used:
            self.tracker.set_degradation(
                DegradationLevel.DEGRADED,
                "Search completed with reduced accuracy.",
                self.tracker.telemetry.get("fallback_reason", "vectordb_unavailable")
            )
        
        return data, self.tracker.get_telemetry()


class PartialFailureHandler:
    """
    Handles partial failures in multi-step operations (e.g., aggregation).
    
    Returns best-effort results when some operations fail.
    
    Usage:
        handler = PartialFailureHandler(ComponentType.AGGREGATE)
        
        with handler as h:
            successful = []
            failed = []
            
            for doc_id in doc_ids:
                try:
                    result = process_document(doc_id)
                    successful.append(result)
                    h.mark_success()
                except Exception as e:
                    failed.append(doc_id)
                    h.mark_failure(doc_id, str(e))
        
        result, telemetry = handler.get_result(successful, failed)
    """
    
    def __init__(self, component: ComponentType, total_items: int):
        self.component = component
        self.tracker = TelemetryTracker(component)
        self.total_items = total_items
        self.success_count = 0
        self.failure_count = 0
        self.failures = []
    
    def __enter__(self):
        self.tracker.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.tracker.__exit__(exc_type, exc_val, exc_tb)
    
    def mark_success(self):
        """Mark one item as successful."""
        self.success_count += 1
    
    def mark_failure(self, item_id: str, reason: str):
        """Mark one item as failed."""
        self.failure_count += 1
        self.failures.append({"item_id": item_id, "reason": reason})
        logger.warning(f"Item failed - component={self.component.value}, item={item_id}, reason={reason}")
    
    def get_result(self, successful_data: Any, failed_items: Any = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Get result with partial failure handling."""
        # Determine degradation level
        if self.failure_count == 0:
            # Full success
            degradation = DegradationLevel.NONE
            message = None
            reason = None
        elif self.success_count == 0:
            # Total failure
            degradation = DegradationLevel.FAILED
            message = "None of the items could be processed successfully."
            reason = "all_items_failed"
            self.tracker.trigger_fallback(reason)
        elif self.failure_count < self.success_count:
            # Partial failure (more success than failure)
            degradation = DegradationLevel.MILD
            message = f"{self.failure_count} of {self.total_items} items could not be processed."
            reason = "partial_failure_mild"
            self.tracker.trigger_fallback(reason)
        else:
            # Major failure (more failure than success)
            degradation = DegradationLevel.DEGRADED
            message = f"Only {self.success_count} of {self.total_items} items were successfully processed."
            reason = "partial_failure_major"
            self.tracker.trigger_fallback(reason)
        
        if message:
            self.tracker.set_degradation(degradation, message, reason)
        
        # Build result
        result = {
            "data": successful_data,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "total_items": self.total_items
        }
        
        if failed_items is not None:
            result["failed_items"] = failed_items
        
        return result, self.tracker.get_telemetry()


class WeakSignalHandler:
    """
    Handles weak signal scenarios (low confidence, insufficient data).
    
    Degrades gracefully instead of failing completely.
    
    Usage:
        handler = WeakSignalHandler(
            ComponentType.CSV_INSIGHTS,
            confidence_threshold=0.3
        )
        
        with handler as h:
            confidence = compute_confidence(data)
            h.check_confidence(confidence)
            
            if h.should_degrade():
                result = simplified_analysis(data)
            else:
                result = full_analysis(data)
        
        result, telemetry = handler.get_result(result)
    """
    
    def __init__(
        self,
        component: ComponentType,
        confidence_threshold: float = 0.3,
        min_data_points: Optional[int] = None
    ):
        self.component = component
        self.tracker = TelemetryTracker(component)
        self.confidence_threshold = confidence_threshold
        self.min_data_points = min_data_points
        self.should_degrade_flag = False
        self.degradation_reason = None
    
    def __enter__(self):
        self.tracker.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.tracker.__exit__(exc_type, exc_val, exc_tb)
    
    def check_confidence(self, confidence: float):
        """Check if confidence meets threshold."""
        self.tracker.set_confidence(confidence)
        
        if confidence < self.confidence_threshold:
            self.should_degrade_flag = True
            self.degradation_reason = "low_confidence"
            logger.info(
                f"Weak signal detected - component={self.component.value}, "
                f"confidence={confidence:.3f}, threshold={self.confidence_threshold}"
            )
    
    def check_data_size(self, size: int):
        """Check if data size is sufficient."""
        if self.min_data_points and size < self.min_data_points:
            self.should_degrade_flag = True
            self.degradation_reason = "insufficient_data"
            logger.info(
                f"Insufficient data - component={self.component.value}, "
                f"size={size}, required={self.min_data_points}"
            )
    
    def should_degrade(self) -> bool:
        """Check if operation should degrade."""
        return self.should_degrade_flag
    
    def get_telemetry(self) -> Dict[str, Any]:
        """Get telemetry from the tracker."""
        return self.tracker.get_telemetry()
    
    def get_result(self, data: Any) -> Tuple[Any, Dict[str, Any]]:
        """Get result with degradation handling."""
        if self.should_degrade_flag:
            self.tracker.trigger_fallback(self.degradation_reason)
            
            if self.degradation_reason == "low_confidence":
                message = "Results have low confidence due to weak signals in the data."
            elif self.degradation_reason == "insufficient_data":
                message = "Results are limited due to insufficient data."
            else:
                message = "Results may be unreliable."
            
            self.tracker.set_degradation(
                DegradationLevel.DEGRADED,
                message,
                self.degradation_reason
            )
        
        return data, self.tracker.get_telemetry()


def with_timeout_fallback(
    timeout_seconds: int,
    fallback_value: Any,
    component: ComponentType
):
    """
    Decorator for operations with timeout fallback.
    
    Usage:
        @with_timeout_fallback(timeout_seconds=5, fallback_value={}, component=ComponentType.RAG_ASK)
        def expensive_operation(query: str) -> Tuple[Dict, Dict]:
            # Long-running operation
            result = process(query)
            return result, {}
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with TelemetryTracker(component) as tracker:
                import signal
                
                def timeout_handler(signum, frame):
                    raise TimeoutError(f"Operation exceeded {timeout_seconds}s")
                
                try:
                    # Try to set timeout (Unix-like systems)
                    signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(timeout_seconds)
                    
                    result, telemetry = func(*args, **kwargs)
                    
                    signal.alarm(0)  # Clear alarm
                    tracker.merge_telemetry(telemetry)
                    return result, tracker.get_telemetry()
                    
                except (AttributeError, ValueError):
                    # Windows or signal not supported - run without timeout
                    logger.debug(f"Timeout not supported on this platform, running without timeout")
                    result, telemetry = func(*args, **kwargs)
                    tracker.merge_telemetry(telemetry)
                    return result, tracker.get_telemetry()
                    
                except TimeoutError:
                    logger.warning(f"Operation timeout after {timeout_seconds}s")
                    tracker.trigger_fallback("timeout")
                    tracker.set_degradation(
                        DegradationLevel.DEGRADED,
                        f"Operation timed out after {timeout_seconds} seconds.",
                        "timeout"
                    )
                    return fallback_value, tracker.get_telemetry()
                    
                except Exception as e:
                    logger.error(f"Unexpected error: {str(e)}")
                    tracker.trigger_fallback(f"error_{type(e).__name__}")
                    tracker.set_degradation(
                        DegradationLevel.FAILED,
                        "An unexpected error occurred.",
                        f"error_{type(e).__name__}"
                    )
                    return fallback_value, tracker.get_telemetry()
        
        return wrapper
    return decorator
