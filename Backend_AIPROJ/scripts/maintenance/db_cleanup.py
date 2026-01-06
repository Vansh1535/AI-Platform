"""
Database Maintenance Script
Clean up old documents and optimize database
"""
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.core.db import get_session, init_engine
from app.core.db.models import Document, CSVInsightsCache
from app.core.logging import logger
from sqlalchemy import select, delete, func


async def cleanup_old_documents(days: int = 30):
    """Remove documents older than specified days."""
    init_engine()
    
    try:
        async with get_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Count documents to delete
            count_query = select(func.count(Document.id)).where(
                Document.created_at < cutoff_date
            )
            result = await session.execute(count_query)
            count = result.scalar()
            
            if count == 0:
                logger.info(f"No documents older than {days} days found")
                return
            
            logger.info(f"Found {count} documents to delete (older than {days} days)")
            
            # Delete old documents
            async with session.begin():
                delete_query = delete(Document).where(
                    Document.created_at < cutoff_date
                )
                await session.execute(delete_query)
            
            logger.info(f"✅ Deleted {count} old documents")
            
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")
        raise


async def cleanup_expired_cache():
    """Remove expired cache entries."""
    init_engine()
    
    try:
        async with get_session() as session:
            now = datetime.utcnow()
            
            # Count expired entries
            count_query = select(func.count(CSVInsightsCache.id)).where(
                CSVInsightsCache.expires_at < now
            )
            result = await session.execute(count_query)
            count = result.scalar()
            
            if count == 0:
                logger.info("No expired cache entries found")
                return
            
            logger.info(f"Found {count} expired cache entries")
            
            # Delete expired cache
            async with session.begin():
                delete_query = delete(CSVInsightsCache).where(
                    CSVInsightsCache.expires_at < now
                )
                await session.execute(delete_query)
            
            logger.info(f"✅ Deleted {count} expired cache entries")
            
    except Exception as e:
        logger.error(f"❌ Cache cleanup failed: {e}")
        raise


async def optimize_database():
    """Run database optimization."""
    init_engine()
    
    try:
        async with get_session() as session:
            # Run VACUUM ANALYZE (PostgreSQL)
            logger.info("Running VACUUM ANALYZE...")
            await session.execute("VACUUM ANALYZE")
            
            logger.info("✅ Database optimization complete")
            
    except Exception as e:
        logger.error(f"❌ Optimization failed: {e}")
        raise


async def get_database_stats():
    """Get database statistics."""
    init_engine()
    
    try:
        async with get_session() as session:
            # Document count
            doc_query = select(func.count(Document.id))
            doc_result = await session.execute(doc_query)
            doc_count = doc_result.scalar()
            
            # Cache count
            cache_query = select(func.count(CSVInsightsCache.id))
            cache_result = await session.execute(cache_query)
            cache_count = cache_result.scalar()
            
            # Expired cache count
            expired_query = select(func.count(CSVInsightsCache.id)).where(
                CSVInsightsCache.expires_at < datetime.utcnow()
            )
            expired_result = await session.execute(expired_query)
            expired_count = expired_result.scalar()
            
            logger.info("📊 Database Statistics:")
            logger.info(f"  Total Documents: {doc_count}")
            logger.info(f"  Cache Entries: {cache_count}")
            logger.info(f"  Expired Cache: {expired_count}")
            
            return {
                "documents": doc_count,
                "cache_entries": cache_count,
                "expired_cache": expired_count
            }
            
    except Exception as e:
        logger.error(f"❌ Stats retrieval failed: {e}")
        raise


async def main():
    """Run maintenance tasks."""
    logger.info("🔧 Starting database maintenance...")
    
    try:
        # Show current stats
        await get_database_stats()
        
        # Clean up expired cache
        await cleanup_expired_cache()
        
        # Clean up old documents (optional - uncomment if needed)
        # await cleanup_old_documents(days=30)
        
        # Optimize database
        await optimize_database()
        
        # Show updated stats
        logger.info("\n📊 Updated Statistics:")
        await get_database_stats()
        
        logger.info("\n✅ Maintenance complete!")
        
    except Exception as e:
        logger.error(f"\n❌ Maintenance failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
