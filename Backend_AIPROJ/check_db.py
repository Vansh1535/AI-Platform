"""
Quick script to check if documents exist in PostgreSQL database.
"""
import asyncio
from app.core.db import init_engine
from app.core.db.repository import DocumentRepository

async def check():
    # Initialize database (not async)
    init_engine()
    
    # Get all documents
    docs = await DocumentRepository.list_documents(limit=100, offset=0)
    
    print(f'\n📊 PostgreSQL Database Status')
    print(f'=' * 60)
    print(f'Total documents: {len(docs)}')
    
    if docs:
        print(f'\n📄 Documents:')
        for doc in docs[:10]:  # Show first 10
            print(f'  - {doc.filename} ({doc.ingestion_status}) - {doc.chunk_count} chunks')
    else:
        print('\n⚠️  No documents found in PostgreSQL!')
        print('   This explains why the homepage shows 0/0/0')
        print('   Documents may be:')
        print('   1. Only in uploads folder (not ingested to DB)')
        print('   2. In old SQLite database')
        print('   3. Need to be re-uploaded after migration')
    
    return len(docs)

if __name__ == "__main__":
    count = asyncio.run(check())
    print(f'\nResult: {count} documents found in PostgreSQL')
