"""
PostgreSQL Migration Verification Tests

Run this to verify the PostgreSQL migration is working correctly.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.core.db import (
    initialize_database, 
    check_database_connection,
    DocumentRepository,
    IngestionEventRepository,
    ChunkRepository,
    CSVCacheRepository
)


async def test_database_connection():
    """Test 1: Database connection"""
    print("\n🧪 Test 1: Database Connection")
    print("-" * 60)
    
    try:
        # Initialize first
        await initialize_database()
        
        # Then check connection
        is_available, error = await check_database_connection()
        
        if is_available:
            print("✅ PASS: Database connection successful")
            return True
        else:
            print(f"❌ FAIL: Database connection failed - {error}")
            return False
    except Exception as e:
        print(f"❌ FAIL: Database initialization error - {str(e)}")
        return False


async def test_table_creation():
    """Test 2: Tables exist"""
    print("\n🧪 Test 2: Table Creation")
    print("-" * 60)
    
    try:
        await initialize_database()
        
        # Check if we can query each table
        docs = await DocumentRepository.list_documents(limit=1)
        print(f"✅ PASS: Documents table accessible ({len(docs)} found)")
        
        return True
    except Exception as e:
        print(f"❌ FAIL: Table access error - {str(e)}")
        return False


async def test_document_crud():
    """Test 3: Document CRUD operations"""
    print("\n🧪 Test 3: Document CRUD Operations")
    print("-" * 60)
    
    try:
        # Create
        test_doc = await DocumentRepository.create_document(
            document_id="test_migration_verify",
            filename="test.txt",
            file_hash="test_hash_12345",
            file_size=100,
            ingestion_status="completed",
            ingestion_version="1"
        )
        print("✅ CREATE: Document created successfully")
        
        # Read
        doc = await DocumentRepository.get_document_by_id("test_migration_verify")
        if doc and doc.filename == "test.txt":
            print("✅ READ: Document retrieved successfully")
        else:
            print("❌ FAIL: Document not found or incorrect data")
            return False
        
        # Update
        updated = await DocumentRepository.update_document(
            "test_migration_verify",
            chunk_count=5
        )
        if updated and updated.chunk_count == 5:
            print("✅ UPDATE: Document updated successfully")
        else:
            print("❌ FAIL: Document update failed")
            return False
        
        # Delete
        deleted = await DocumentRepository.delete_document("test_migration_verify")
        if deleted:
            print("✅ DELETE: Document deleted successfully")
        else:
            print("❌ FAIL: Document deletion failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: CRUD operations error - {str(e)}")
        return False


async def test_duplicate_detection():
    """Test 4: Duplicate detection by hash"""
    print("\n🧪 Test 4: Duplicate Detection")
    print("-" * 60)
    
    try:
        # Create first document
        await DocumentRepository.create_document(
            document_id="dup_test_1",
            filename="duplicate.txt",
            file_hash="duplicate_hash_123",
            file_size=100,
            ingestion_version="1"
        )
        
        # Check duplicate by hash
        existing = await DocumentRepository.get_document_by_hash("duplicate_hash_123")
        
        if existing and existing.id == "dup_test_1":
            print("✅ PASS: Duplicate detection working")
            
            # Cleanup
            await DocumentRepository.delete_document("dup_test_1")
            return True
        else:
            print("❌ FAIL: Duplicate not detected")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Duplicate detection error - {str(e)}")
        return False


async def test_ingestion_events():
    """Test 5: Ingestion event tracking"""
    print("\n🧪 Test 5: Ingestion Event Tracking")
    print("-" * 60)
    
    try:
        # Create document
        await DocumentRepository.create_document(
            document_id="event_test_1",
            filename="event_test.txt",
            file_hash="event_hash_123",
            file_size=100,
            ingestion_version="1"
        )
        
        # Create event
        event = await IngestionEventRepository.create_event(
            document_id="event_test_1",
            event_type="ingestion_started",
            event_status="success",
            processing_time_ms=100
        )
        
        # Get events
        events = await IngestionEventRepository.get_events_for_document("event_test_1")
        
        if len(events) > 0:
            print(f"✅ PASS: Event tracking working ({len(events)} events)")
            
            # Cleanup
            await DocumentRepository.delete_document("event_test_1")
            return True
        else:
            print("❌ FAIL: No events found")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Event tracking error - {str(e)}")
        return False


async def main():
    """Run all tests"""
    print("=" * 60)
    print("PostgreSQL Migration Verification Tests")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(await test_database_connection())
    results.append(await test_table_creation())
    results.append(await test_document_crud())
    results.append(await test_duplicate_detection())
    results.append(await test_ingestion_events())
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED - Migration verified successfully!")
        return 0
    else:
        print(f"\n⚠️ {total - passed} TEST(S) FAILED - Review errors above")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
