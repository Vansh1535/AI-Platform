"""
PostgreSQL Database Configuration — Local Development

Async PostgreSQL connection using SQLAlchemy + asyncpg.
Replaces SQLite registry with production-grade Postgres.

Environment Variables:
- DB_HOST: Database host (default: localhost)
- DB_PORT: Database port (default: 5432)
- DB_USER: Database user (default: postgres)
- DB_PASS: Database password (default: postgres)
- DB_NAME: Database name (default: rag_platform)

Design:
- Async engine for non-blocking I/O
- Connection pooling enabled
- Graceful degradation if DB unavailable
- Development-only (local Postgres)
"""

import os
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from contextlib import asynccontextmanager

from app.core.logging import setup_logger

logger = setup_logger("INFO")

# SQLAlchemy Base for models
Base = declarative_base()

# Global engine and session factory
_engine = None
_async_session_factory = None


def get_database_url() -> str:
    """
    Build PostgreSQL connection URL from environment variables.
    
    Returns:
        Connection URL for asyncpg
        
    Format: postgresql+asyncpg://user:pass@host:port/dbname
    """
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_user = os.getenv("DB_USER", "postgres")
    db_pass = os.getenv("DB_PASS", "postgres")
    db_name = os.getenv("DB_NAME", "rag_platform")
    
    url = f"postgresql+asyncpg://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    
    # Log connection attempt (without password)
    safe_url = f"postgresql+asyncpg://{db_user}:***@{db_host}:{db_port}/{db_name}"
    logger.info(f"Database URL: {safe_url}")
    
    return url


def init_engine():
    """
    Initialize async SQLAlchemy engine with connection pooling.
    
    Only called once at startup.
    """
    global _engine, _async_session_factory
    
    if _engine is not None:
        logger.info("Database engine already initialized")
        return
    
    try:
        database_url = get_database_url()
        
        _engine = create_async_engine(
            database_url,
            echo=False,  # Set to True for SQL query logging
            pool_size=10,  # Connection pool size
            max_overflow=20,  # Max connections beyond pool_size
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=3600,  # Recycle connections after 1 hour
        )
        
        _async_session_factory = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Keep objects usable after commit
        )
        
        logger.info("✅ Database engine initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize database engine: {str(e)}")
        _engine = None
        _async_session_factory = None
        raise


async def create_tables():
    """
    Create all tables defined in Base metadata.
    
    Only for DEV mode. Does not drop existing tables.
    Safe to call multiple times (idempotent).
    """
    global _engine
    
    if _engine is None:
        raise RuntimeError("Database engine not initialized. Call init_engine() first.")
    
    try:
        async with _engine.begin() as conn:
            # Create tables if they don't exist
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ Database tables created/verified")
        
    except Exception as e:
        logger.error(f"❌ Failed to create tables: {str(e)}")
        raise


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get async database session with automatic cleanup.
    
    Usage:
        async with get_session() as session:
            result = await session.execute(...)
            await session.commit()
    
    Yields:
        AsyncSession for database operations
        
    Raises:
        RuntimeError: If engine not initialized
    """
    if _async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_engine() first.")
    
    session = _async_session_factory()
    try:
        yield session
    except Exception as e:
        await session.rollback()
        logger.error(f"Session error, rolled back: {str(e)}")
        raise
    finally:
        await session.close()


async def check_database_connection() -> tuple[bool, Optional[str]]:
    """
    Check if database is available and responsive.
    
    Returns:
        Tuple of (is_available, error_message)
        
    Example:
        available, error = await check_database_connection()
        if not available:
            logger.warning(f"DB unavailable: {error}")
    """
    try:
        if _engine is None:
            return False, "Database engine not initialized"
        
        async with _engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            row = result.scalar()
            
            if row == 1:
                logger.debug("Database connection check: OK")
                return True, None
            else:
                return False, "Unexpected query result"
                
    except Exception as e:
        error_msg = f"Database connection failed: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


async def get_database_stats() -> dict:
    """
    Get database statistics and health info.
    
    Returns:
        Dictionary with connection pool stats and table counts
    """
    try:
        stats = {
            "engine_initialized": _engine is not None,
            "database_url": get_database_url().replace(os.getenv("DB_PASS", ""), "***"),
            "pool_size": _engine.pool.size() if _engine else 0,
            "connections_in_use": _engine.pool.checkedin() if _engine else 0,
        }
        
        # Check connection
        is_available, error = await check_database_connection()
        stats["connection_available"] = is_available
        stats["connection_error"] = error
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get database stats: {str(e)}")
        return {
            "engine_initialized": False,
            "error": str(e)
        }


async def close_engine():
    """
    Close database engine and cleanup connections.
    
    Should be called on application shutdown.
    """
    global _engine, _async_session_factory
    
    if _engine is None:
        logger.info("Database engine not initialized, nothing to close")
        return
    
    try:
        await _engine.dispose()
        _engine = None
        _async_session_factory = None
        logger.info("✅ Database engine closed successfully")
        
    except Exception as e:
        logger.error(f"❌ Error closing database engine: {str(e)}")


def is_database_initialized() -> bool:
    """
    Check if database engine is initialized.
    
    Returns:
        True if engine ready, False otherwise
    """
    return _engine is not None


# Startup helper
async def initialize_database():
    """
    Complete database initialization sequence.
    
    Call this on application startup:
    1. Initialize engine
    2. Create tables (if not exist)
    3. Verify connection
    
    Raises exception if database unavailable.
    """
    logger.info("Initializing PostgreSQL database...")
    
    # Step 1: Initialize engine
    init_engine()
    
    # Step 2: Create tables
    await create_tables()
    
    # Step 3: Verify connection
    is_available, error = await check_database_connection()
    
    if not is_available:
        raise RuntimeError(f"Database connection failed: {error}")
    
    logger.info("✅ Database initialization complete")
    
    # Log stats
    stats = await get_database_stats()
    logger.info(f"Database stats: {stats}")
