"""
Database Verification CLI — List Documents

Query and display all documents from PostgreSQL registry.
Used to verify database contents and compare with pgAdmin.
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Load environment variables from .env file
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from app.core.db import initialize_database, get_session
from app.core.db.models import Document
from sqlalchemy import select, func


async def list_documents():
    """List all documents from database."""
    print("=" * 80)
    print("DATABASE VERIFICATION: List All Documents")
    print("=" * 80)
    print()
    
    try:
        # Initialize database
        print("Initializing database connection...")
        await initialize_database()
        print("✅ Database connected\n")
        
        async with get_session() as session:
            # Count total documents
            count_query = select(func.count()).select_from(Document)
            result = await session.execute(count_query)
            total_count = result.scalar()
            
            print(f"Total Documents: {total_count}")
            print("-" * 80)
            print()
            
            if total_count == 0:
                print("No documents found in database.")
                return
            
            # Get all documents
            query = select(Document).order_by(Document.created_at.desc())
            result = await session.execute(query)
            documents = result.scalars().all()
            
            # Display documents
            for i, doc in enumerate(documents, 1):
                print(f"[{i}] Document ID: {doc.id}")
                print(f"    Filename: {doc.filename}")
                print(f"    File Hash: {doc.file_hash}")
                print(f"    Status: {doc.ingestion_status}")
                print(f"    Chunk Count: {doc.chunk_count}")
                print(f"    File Size: {doc.file_size} bytes" if doc.file_size else "    File Size: N/A")
                print(f"    Created: {doc.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"    Processing Time: {doc.processing_time_ms}ms" if doc.processing_time_ms else "    Processing Time: N/A")
                
                if doc.graceful_message:
                    print(f"    ⚠️  Graceful Message: {doc.graceful_message}")
                
                if doc.degradation_level and doc.degradation_level != "none":
                    print(f"    ⚠️  Degradation Level: {doc.degradation_level}")
                
                print()
        
        print("=" * 80)
        print("✅ Verification complete")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def document_stats():
    """Show document statistics."""
    print("=" * 80)
    print("DOCUMENT STATISTICS")
    print("=" * 80)
    print()
    
    try:
        await initialize_database()
        
        async with get_session() as session:
            # Total documents
            count_query = select(func.count()).select_from(Document)
            result = await session.execute(count_query)
            total = result.scalar()
            
            # By status
            status_query = select(Document.ingestion_status, func.count()).group_by(Document.ingestion_status)
            result = await session.execute(status_query)
            status_counts = result.all()
            
            # Total chunks
            chunks_query = select(func.sum(Document.chunk_count)).select_from(Document)
            result = await session.execute(chunks_query)
            total_chunks = result.scalar() or 0
            
            print(f"Total Documents: {total}")
            print(f"Total Chunks: {total_chunks}")
            print()
            print("Documents by Status:")
            for status, count in status_counts:
                print(f"  - {status}: {count}")
            print()
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    print("\n")
    
    if len(sys.argv) > 1 and sys.argv[1] == "stats":
        asyncio.run(document_stats())
    else:
        asyncio.run(list_documents())
    
    print("\n")
