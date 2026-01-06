"""
Graceful Degradation Utilities for Database Operations

Provides decorators and utilities for handling database failures gracefully
across the entire application without crashing user-facing features.
"""

from functools import wraps
from typing import Any, Callable, Optional, Dict
import asyncio
from app.core.logging import setup_logger

logger = setup_logger("INFO")


def graceful_db_operation(
    fallback_value: Any = None,
    operation_name: str = "database operation"
):
    """
    Decorator for graceful degradation of database operations.
    
    Wraps async functions that interact with PostgreSQL and provides
    automatic fallback behavior if the database is unavailable.
    
    Args:
        fallback_value: Value to return if operation fails (default: None)
        operation_name: Descriptive name for logging
        
    Returns:
        Decorated function with graceful error handling
        
    Example:
        @graceful_db_operation(fallback_value=[], operation_name="list documents")
        async def list_documents():
            return await DocumentRepository.list_documents()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.warning(
                    f"🔄 Graceful degradation triggered for {operation_name}: {str(e)}"
                )
                
                # Return graceful response
                if isinstance(fallback_value, dict):
                    return {
                        **fallback_value,
                        "degradation_level": "fallback",
                        "fallback_triggered": True,
                        "graceful_message": f"Database temporarily unavailable for {operation_name}",
                        "routing_decision": "db_fallback"
                    }
                else:
                    return fallback_value
                    
        return wrapper
    return decorator


def graceful_db_operation_sync(
    fallback_value: Any = None,
    operation_name: str = "database operation"
):
    """
    Decorator for graceful degradation of synchronous database operations.
    
    Similar to graceful_db_operation but for sync functions.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(
                    f"🔄 Graceful degradation triggered for {operation_name}: {str(e)}"
                )
                
                # Return graceful response
                if isinstance(fallback_value, dict):
                    return {
                        **fallback_value,
                        "degradation_level": "fallback",
                        "fallback_triggered": True,
                        "graceful_message": f"Database temporarily unavailable for {operation_name}",
                        "routing_decision": "db_fallback"
                    }
                else:
                    return fallback_value
                    
        return wrapper
    return decorator


async def safe_db_call(
    operation: Callable,
    fallback_value: Any = None,
    operation_name: str = "database operation",
    *args,
    **kwargs
) -> Any:
    """
    Execute a database operation with graceful degradation.
    
    Utility function for wrapping database calls inline without decorators.
    
    Args:
        operation: Async function to execute
        fallback_value: Value to return on failure
        operation_name: Description for logging
        *args: Positional arguments for operation
        **kwargs: Keyword arguments for operation
        
    Returns:
        Operation result or fallback value
        
    Example:
        doc = await safe_db_call(
            DocumentRepository.get_document_by_id,
            fallback_value=None,
            operation_name="get document",
            document_id="doc123"
        )
    """
    try:
        return await operation(*args, **kwargs)
    except Exception as e:
        logger.warning(
            f"🔄 Graceful degradation triggered for {operation_name}: {str(e)}"
        )
        
        if isinstance(fallback_value, dict):
            return {
                **fallback_value,
                "degradation_level": "fallback",
                "fallback_triggered": True,
                "graceful_message": f"Database temporarily unavailable for {operation_name}",
                "routing_decision": "db_fallback"
            }
        else:
            return fallback_value


def create_degraded_response(
    base_response: Dict[str, Any],
    operation_name: str,
    error: Optional[Exception] = None
) -> Dict[str, Any]:
    """
    Create a standardized degraded response for API endpoints.
    
    Args:
        base_response: Base response data
        operation_name: Operation that failed
        error: Optional exception that triggered degradation
        
    Returns:
        Response with degradation metadata
    """
    response = {
        **base_response,
        "degradation_level": "fallback",
        "fallback_triggered": True,
        "graceful_message": f"Database temporarily unavailable — returning partial results for {operation_name}",
        "routing_decision": "db_fallback"
    }
    
    if error:
        logger.warning(f"Degraded response for {operation_name}: {str(error)}")
    
    return response


class GracefulDatabaseContext:
    """
    Context manager for database operations with graceful degradation.
    
    Usage:
        async with GracefulDatabaseContext("save document") as ctx:
            await DocumentRepository.create_document(...)
            
        if ctx.failed:
            return {"status": "degraded", "message": ctx.error_message}
    """
    
    def __init__(self, operation_name: str = "database operation"):
        self.operation_name = operation_name
        self.failed = False
        self.error_message = None
        self.exception = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.failed = True
            self.exception = exc_val
            self.error_message = str(exc_val)
            
            logger.warning(
                f"🔄 Graceful degradation in context for {self.operation_name}: {self.error_message}"
            )
            
            # Suppress exception - let caller handle gracefully
            return True
        return False
