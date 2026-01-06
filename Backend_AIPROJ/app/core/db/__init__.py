"""
Database module initialization.
"""

from .postgres import (
    Base,
    init_engine,
    create_tables,
    get_session,
    check_database_connection,
    get_database_stats,
    close_engine,
    is_database_initialized,
    initialize_database,
    get_database_url
)

from .repository import (
    DocumentRepository,
    IngestionEventRepository,
    ChunkRepository,
    CSVCacheRepository,
)

__all__ = [
    "Base",
    "init_engine",
    "create_tables",
    "get_session",
    "check_database_connection",
    "get_database_stats",
    "close_engine",
    "is_database_initialized",
    "initialize_database",
    "get_database_url",
    "DocumentRepository",
    "IngestionEventRepository",
    "ChunkRepository",
    "CSVCacheRepository",
]
