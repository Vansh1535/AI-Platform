"""
Resilience and retry logic for production-grade error handling.
Provides timeout management, retry policies, and graceful degradation.
"""

import time
import functools
from typing import Any, Callable, Optional, Tuple
from app.core.logging import setup_logger

logger = setup_logger()

# Error taxonomy
class ErrorClass:
    """Structured error classification for observability."""
    RETRIEVAL_WEAK_SIGNAL = "RETRIEVAL_WEAK_SIGNAL"
    LLM_PROVIDER_UNAVAILABLE = "LLM_PROVIDER_UNAVAILABLE"
    CACHE_RECOVERY = "CACHE_RECOVERY"
    SAFE_MODE_FALLBACK = "SAFE_MODE_FALLBACK"
    TIMEOUT_EXCEEDED = "TIMEOUT_EXCEEDED"
    NETWORK_ERROR = "NETWORK_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"


# Transient error types that should be retried
RETRYABLE_ERRORS = (
    ConnectionError,
    TimeoutError,
    OSError,
)


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    timeout_seconds: Optional[float] = None
):
    """
    Decorator for retry logic with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries (seconds)
        backoff_factor: Multiplier for delay on each retry
        timeout_seconds: Optional timeout for the entire operation
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Tuple[Any, dict]:
            """
            Execute function with retry logic.
            
            Returns:
                Tuple of (result, meta_dict) where meta_dict contains:
                - retry_count
                - timeout_triggered
                - error_class (if applicable)
            """
            meta = {
                "retry_count": 0,
                "timeout_triggered": False,
                "error_class": None
            }
            
            start_time = time.time()
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    # Check timeout
                    if timeout_seconds and (time.time() - start_time) > timeout_seconds:
                        meta["timeout_triggered"] = True
                        meta["error_class"] = ErrorClass.TIMEOUT_EXCEEDED
                        logger.warning(
                            f"timeout_triggered=true function={func.__name__} "
                            f"elapsed={time.time() - start_time:.2f}s"
                        )
                        # Return last known result or raise
                        if last_exception:
                            raise last_exception
                        raise TimeoutError(f"Operation exceeded timeout of {timeout_seconds}s")
                    
                    # Execute function
                    result = func(*args, **kwargs)
                    
                    # Log retry success if not first attempt
                    if attempt > 0:
                        logger.info(
                            f"retry_success=true function={func.__name__} "
                            f"attempt={attempt + 1}"
                        )
                    
                    return result, meta
                    
                except RETRYABLE_ERRORS as e:
                    last_exception = e
                    meta["retry_count"] = attempt + 1
                    
                    if attempt < max_retries:
                        delay = initial_delay * (backoff_factor ** attempt)
                        logger.warning(
                            f"retry_attempt={attempt + 1} function={func.__name__} "
                            f"error={type(e).__name__} delay={delay:.2f}s"
                        )
                        time.sleep(delay)
                    else:
                        # Max retries exceeded
                        meta["error_class"] = ErrorClass.NETWORK_ERROR
                        logger.error(
                            f"retry_exhausted=true function={func.__name__} "
                            f"attempts={max_retries + 1}"
                        )
                        # Return degraded result instead of crashing
                        return _get_degraded_result(func.__name__, e), meta
                        
                except Exception as e:
                    # Non-retryable error - degrade gracefully
                    logger.error(
                        f"non_retryable_error=true function={func.__name__} "
                        f"error={type(e).__name__} message={str(e)}"
                    )
                    meta["error_class"] = type(e).__name__
                    return _get_degraded_result(func.__name__, e), meta
            
            # Should not reach here, but handle gracefully
            return _get_degraded_result(func.__name__, last_exception), meta
            
        return wrapper
    return decorator


def _get_degraded_result(function_name: str, error: Exception) -> Any:
    """
    Get a safe degraded result when function fails.
    
    Args:
        function_name: Name of the failed function
        error: The exception that occurred
        
    Returns:
        Safe default result based on function type
    """
    logger.info(f"degraded_mode=true function={function_name}")
    
    # Return appropriate degraded results based on function context
    if "search" in function_name.lower() or "retrieve" in function_name.lower():
        return []  # Empty results
    elif "answer" in function_name.lower():
        return {
            "answer": "I apologize, but I'm unable to provide an answer at this moment due to a temporary service issue. Please try again.",
            "citations": [],
            "used_chunks": 0
        }
    elif "predict" in function_name.lower():
        return {
            "prediction": None,
            "probabilities": [],
            "error": str(error)
        }
    else:
        return None


def measure_latency(stage_name: str):
    """
    Decorator to measure and log execution latency for a specific stage.
    
    Args:
        stage_name: Name of the execution stage (e.g., 'retrieval', 'llm', 'tool')
        
    Returns:
        Decorated function with latency measurement
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Tuple[Any, float]:
            """
            Execute function and measure latency.
            
            Returns:
                Tuple of (result, latency_ms)
            """
            start_time = time.time()
            result = func(*args, **kwargs)
            latency_ms = int((time.time() - start_time) * 1000)
            
            logger.debug(
                f"latency_measured=true stage={stage_name} "
                f"latency_ms={latency_ms}"
            )
            
            return result, latency_ms
            
        return wrapper
    return decorator
