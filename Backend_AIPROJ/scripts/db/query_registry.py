"""
Database Verification CLI — Query Registry

Advanced queries for database verification and debugging.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Load environment variables from .env file
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from app.core.db import initialize_database, get_session
from app.core.db.models import Document, IngestionEvent, Chunk, CSVInsightsCache
from sqlalchemy import select, func, and_, or_


async def query_recent_documents(hours=24):
    """Query documents ingested in last N hours."""
    print(f"\n📄 Documents ingested in last {hours} hours:")
    print("-" * 80)
    
    try:
        await initialize_database()
        
        async with get_session() as session:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            query = select(Document).where(
                Document.created_at >= cutoff
            ).order_by(Document.created_at.desc())
            
            result = await session.execute(query)
            documents = result.scalars().all()
            
            if not documents:
                print(f"No documents found in last {hours} hours")
                return
            
            for doc in documents:
                print(f"  • {doc.filename} ({doc.ingestion_status}) - {doc.created_at}")
            
            print(f"\nTotal: {len(documents)} documents")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")


async def query_failed_ingestions():
    """Query failed ingestion events."""
    print("\n❌ Failed Ingestion Events:")
    print("-" * 80)
    
    try:
        await initialize_database()
        
        async with get_session() as session:
            query = select(IngestionEvent).where(
                IngestionEvent.event_status == "failure"
            ).order_by(IngestionEvent.event_timestamp.desc()).limit(10)
            
            result = await session.execute(query)
            events = result.scalars().all()
            
            if not events:
                print("No failed ingestions found ✅")
                return
            
            for event in events:
                print(f"  • Document: {event.document_id}")
                print(f"    Time: {event.event_timestamp}")
                print(f"    Error: {event.error_message}")
                print()
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")


async def query_by_hash(file_hash):
    """Query document by file hash (duplicate detection)."""
    print(f"\n🔍 Searching for document with hash: {file_hash}")
    print("-" * 80)
    
    try:
        await initialize_database()
        
        async with get_session() as session:
            query = select(Document).where(Document.file_hash == file_hash)
            result = await session.execute(query)
            doc = result.scalar_one_or_none()
            
            if not doc:
                print("❌ No document found with that hash")
                return
            
            print("✅ Document found:")
            print(f"  ID: {doc.id}")
            print(f"  Filename: {doc.filename}")
            print(f"  Status: {doc.ingestion_status}")
            print(f"  Created: {doc.created_at}")
            print(f"  Chunks: {doc.chunk_count}")
            
            # Check if there are ingestion events
            event_query = select(func.count()).select_from(IngestionEvent).where(
                IngestionEvent.document_id == doc.id
            )
            result = await session.execute(event_query)
            event_count = result.scalar()
            print(f"  Ingestion Events: {event_count}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")


async def query_chunks(document_id):
    """Query chunks for a document."""
    print(f"\n📦 Chunks for document: {document_id}")
    print("-" * 80)
    
    try:
        await initialize_database()
        
        async with get_session() as session:
            query = select(Chunk).where(
                Chunk.document_id == document_id
            ).order_by(Chunk.chunk_index)
            
            result = await session.execute(query)
            chunks = result.scalars().all()
            
            if not chunks:
                print("No chunks found for this document")
                return
            
            print(f"Total chunks: {len(chunks)}\n")
            
            for chunk in chunks[:10]:  # Show first 10
                print(f"  [{chunk.chunk_index}] ID: {chunk.id}")
                print(f"      Size: {chunk.chunk_size} chars" if chunk.chunk_size else "      Size: N/A")
                print(f"      Vector ID: {chunk.vector_id}" if chunk.vector_id else "      Vector ID: N/A")
                print()
            
            if len(chunks) > 10:
                print(f"  ... and {len(chunks) - 10} more chunks")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")


async def query_cache_stats():
    """Query CSV insights cache statistics."""
    print("\n💾 CSV Insights Cache Statistics:")
    print("-" * 80)
    
    try:
        await initialize_database()
        
        async with get_session() as session:
            # Total cache entries
            count_query = select(func.count()).select_from(CSVInsightsCache)
            result = await session.execute(count_query)
            total = result.scalar()
            
            print(f"Total cache entries: {total}")
            
            if total == 0:
                print("Cache is empty")
                return
            
            # Recent cache entries
            recent_query = select(CSVInsightsCache).order_by(
                CSVInsightsCache.created_at.desc()
            ).limit(5)
            
            result = await session.execute(recent_query)
            recent = result.scalars().all()
            
            print("\nRecent cache entries:")
            for entry in recent:
                print(f"  • {entry.dataset_name or 'Unnamed'} ({entry.analysis_mode})")
                print(f"    Hash: {entry.file_hash[:16]}...")
                print(f"    LLM: {entry.enable_llm_insights}")
                print(f"    Accessed: {entry.access_count} times")
                print()
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")


async def main():
    """Main CLI interface."""
    print("=" * 80)
    print("DATABASE QUERY CLI")
    print("=" * 80)
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python query_registry.py recent [hours]     # Recent documents")
        print("  python query_registry.py failed             # Failed ingestions")
        print("  python query_registry.py hash <hash>        # Find by hash")
        print("  python query_registry.py chunks <doc_id>    # List chunks")
        print("  python query_registry.py cache              # Cache stats")
        print()
        return
    
    command = sys.argv[1]
    
    if command == "recent":
        hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
        await query_recent_documents(hours)
    
    elif command == "failed":
        await query_failed_ingestions()
    
    elif command == "hash":
        if len(sys.argv) < 3:
            print("❌ Error: Please provide file hash")
            return
        await query_by_hash(sys.argv[2])
    
    elif command == "chunks":
        if len(sys.argv) < 3:
            print("❌ Error: Please provide document ID")
            return
        await query_chunks(sys.argv[2])
    
    elif command == "cache":
        await query_cache_stats()
    
    else:
        print(f"❌ Unknown command: {command}")
    
    print()


if __name__ == "__main__":
    asyncio.run(main())
