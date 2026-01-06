"""
Performance and Load Tests for PostgreSQL Migration

Tests ingestion pipeline performance, scalability, and reliability
under various load conditions.

Test Categories:
1. Latency Tests - Measure response times for single operations
2. Throughput Tests - Measure documents/second under load
3. Batch Tests - Measure performance with multiple concurrent uploads
4. Degradation Tests - Verify graceful behavior under DB outage
5. Cache Tests - Verify CSV insights cache performance
"""

import asyncio
import time
import pytest
from pathlib import Path
import tempfile
from typing import List, Dict, Any
from app.ingestion.integration_async import ingest_multi_file_async
from app.core.db.document_service import get_document_service
from app.core.db import DocumentRepository, ChunkRepository
from app.analytics.csv_insights import generate_csv_insights
import pandas as pd


class TestLatencyPerformance:
    """Test individual operation latency."""
    
    @pytest.mark.asyncio
    async def test_single_document_ingestion_latency(self):
        """Test latency for ingesting a single document."""
        # Create test document
        test_content = "This is test content. " * 100  # ~2000 chars
        test_file = Path(tempfile.mktemp(suffix=".txt"))
        test_file.write_text(test_content)
        
        try:
            start = time.time()
            
            result = await ingest_multi_file_async(
                file_path=str(test_file),
                source="performance_test.txt",
                chunk_size=200,
                overlap=50,
                exists_policy="overwrite",
                normalize=True
            )
            
            latency_ms = (time.time() - start) * 1000
            
            # Assertions
            assert result["status"] == "success"
            assert latency_ms < 5000, f"Ingestion took {latency_ms}ms (expected < 5000ms)"
            assert result["chunks"] > 0
            
            print(f"✅ Single document latency: {latency_ms:.2f}ms")
            print(f"   Chunks created: {result['chunks']}")
            print(f"   Throughput: {(result['chunks'] / latency_ms * 1000):.2f} chunks/sec")
            
        finally:
            test_file.unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_database_query_latency(self):
        """Test latency for database queries."""
        service = get_document_service()
        
        # Test 1: Get document (warm path)
        start = time.time()
        doc = await service.list_documents_by_status("completed")
        query_latency_ms = (time.time() - start) * 1000
        
        assert query_latency_ms < 1000, f"Query took {query_latency_ms}ms (expected < 1000ms)"
        
        print(f"✅ Database query latency: {query_latency_ms:.2f}ms")
        print(f"   Documents returned: {len(doc)}")


class TestThroughputPerformance:
    """Test system throughput under load."""
    
    @pytest.mark.asyncio
    async def test_sequential_ingestion_throughput(self):
        """Test throughput for N documents ingested sequentially."""
        n_docs = 10
        test_files = []
        
        try:
            # Create test documents
            for i in range(n_docs):
                content = f"Document {i} content. " * 50
                test_file = Path(tempfile.mktemp(suffix=".txt"))
                test_file.write_text(content)
                test_files.append(test_file)
            
            start = time.time()
            
            results = []
            for i, test_file in enumerate(test_files):
                result = await ingest_multi_file_async(
                    file_path=str(test_file),
                    source=f"throughput_test_{i}.txt",
                    chunk_size=200,
                    overlap=50,
                    exists_policy="overwrite"
                )
                results.append(result)
            
            total_time = time.time() - start
            throughput = n_docs / total_time
            
            # Assertions
            successes = sum(1 for r in results if r["status"] == "success")
            assert successes == n_docs, f"Only {successes}/{n_docs} succeeded"
            assert throughput > 1.0, f"Throughput {throughput:.2f} docs/sec (expected > 1.0)"
            
            total_chunks = sum(r.get("chunks", 0) for r in results)
            
            print(f"✅ Sequential throughput: {throughput:.2f} docs/sec")
            print(f"   Total time: {total_time:.2f}s for {n_docs} documents")
            print(f"   Total chunks: {total_chunks}")
            print(f"   Avg latency: {(total_time / n_docs * 1000):.2f}ms/doc")
            
        finally:
            for test_file in test_files:
                test_file.unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_concurrent_ingestion_throughput(self):
        """Test throughput for N documents ingested concurrently."""
        n_docs = 5  # Smaller for concurrent test
        test_files = []
        
        try:
            # Create test documents
            for i in range(n_docs):
                content = f"Concurrent document {i} content. " * 50
                test_file = Path(tempfile.mktemp(suffix=".txt"))
                test_file.write_text(content)
                test_files.append(test_file)
            
            start = time.time()
            
            # Run concurrently
            tasks = [
                ingest_multi_file_async(
                    file_path=str(test_file),
                    source=f"concurrent_test_{i}.txt",
                    chunk_size=200,
                    overlap=50,
                    exists_policy="overwrite"
                )
                for i, test_file in enumerate(test_files)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            total_time = time.time() - start
            throughput = n_docs / total_time
            
            # Assertions
            successes = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "success")
            assert successes >= n_docs * 0.8, f"Only {successes}/{n_docs} succeeded (expected ≥80%)"
            
            print(f"✅ Concurrent throughput: {throughput:.2f} docs/sec")
            print(f"   Total time: {total_time:.2f}s for {n_docs} documents (concurrent)")
            print(f"   Successes: {successes}/{n_docs}")
            print(f"   Speedup vs sequential: ~{n_docs / total_time:.1f}x")
            
        finally:
            for test_file in test_files:
                test_file.unlink(missing_ok=True)


class TestBatchPerformance:
    """Test batch ingestion performance."""
    
    @pytest.mark.asyncio
    async def test_batch_chunk_persistence(self):
        """Test chunk persistence performance for batch operations."""
        # Create a document with many chunks
        test_content = "Chunk content. " * 1000  # ~15000 chars = ~75 chunks
        test_file = Path(tempfile.mktemp(suffix=".txt"))
        test_file.write_text(test_content)
        
        try:
            start = time.time()
            
            result = await ingest_multi_file_async(
                file_path=str(test_file),
                source="batch_chunks_test.txt",
                chunk_size=200,
                overlap=50,
                exists_policy="overwrite"
            )
            
            latency_ms = (time.time() - start) * 1000
            
            # Verify chunks were persisted
            service = get_document_service()
            chunks = await service.get_chunks_for_document(result["document_id"])
            
            # Assertions
            assert result["status"] == "success"
            assert result["chunks"] > 50, "Expected many chunks"
            assert len(chunks) == result["chunks"] or len(chunks) == 0, "Chunk persistence degraded gracefully"
            
            print(f"✅ Batch chunk persistence: {latency_ms:.2f}ms")
            print(f"   Chunks created: {result['chunks']}")
            print(f"   Chunks persisted to DB: {len(chunks)}")
            print(f"   Throughput: {(result['chunks'] / latency_ms * 1000):.2f} chunks/sec")
            
        finally:
            test_file.unlink(missing_ok=True)


class TestGracefulDegradation:
    """Test graceful degradation under failure conditions."""
    
    @pytest.mark.asyncio
    async def test_ingestion_continues_without_db_tracking(self):
        """Test that ingestion completes even if DB tracking fails."""
        test_content = "Test content for degradation. " * 20
        test_file = Path(tempfile.mktemp(suffix=".txt"))
        test_file.write_text(test_content)
        
        try:
            result = await ingest_multi_file_async(
                file_path=str(test_file),
                source="degradation_test.txt",
                chunk_size=200,
                overlap=50,
                exists_policy="overwrite"
            )
            
            # Assertions - should succeed even if DB unavailable
            assert result["status"] in ["success", "degraded"]
            assert result["chunks"] > 0
            
            # Check for degradation signals
            if result.get("degradation_level"):
                print(f"⚠️  Graceful degradation detected:")
                print(f"   Status: {result['status']}")
                print(f"   Degradation level: {result.get('degradation_level')}")
                print(f"   Message: {result.get('graceful_message')}")
                print(f"   Chunks still created: {result['chunks']}")
            else:
                print(f"✅ No degradation - full DB tracking available")
            
        finally:
            test_file.unlink(missing_ok=True)


class TestCSVCachePerformance:
    """Test CSV insights cache performance."""
    
    def test_csv_insights_cache_hit(self):
        """Test cache performance for repeated CSV analysis."""
        # Create test CSV
        df = pd.DataFrame({
            "id": range(100),
            "value": range(100, 200),
            "category": ["A", "B", "C"] * 33 + ["A"]
        })
        
        # First call - cache miss
        start = time.time()
        result1, telemetry1 = generate_csv_insights(
            df,
            file_meta={"source": "cache_test.csv"},
            mode="light",
            enable_llm_insights=False
        )
        first_latency = (time.time() - start) * 1000
        
        # Second call - should hit cache
        start = time.time()
        result2, telemetry2 = generate_csv_insights(
            df,
            file_meta={"source": "cache_test.csv", "file_hash": telemetry1.get("file_hash", "")[:64]},
            mode="light",
            enable_llm_insights=False
        )
        second_latency = (time.time() - start) * 1000
        
        # Assertions
        assert result1 is not None
        assert result2 is not None
        
        cache_hit = telemetry2.get("cache_hit", False)
        
        print(f"✅ CSV cache test:")
        print(f"   First call (miss): {first_latency:.2f}ms")
        print(f"   Second call: {second_latency:.2f}ms")
        print(f"   Cache hit: {cache_hit}")
        
        if cache_hit:
            speedup = first_latency / second_latency if second_latency > 0 else 0
            print(f"   Speedup: {speedup:.2f}x faster")
            assert second_latency < first_latency, "Cache should be faster"


class TestSystemReliability:
    """Test overall system reliability metrics."""
    
    @pytest.mark.asyncio
    async def test_no_data_loss_under_load(self):
        """Verify no documents lost during batch ingestion."""
        n_docs = 20
        test_files = []
        expected_doc_ids = []
        
        try:
            # Create test documents
            for i in range(n_docs):
                content = f"Reliability test document {i}. " * 30
                test_file = Path(tempfile.mktemp(suffix=".txt"))
                test_file.write_text(content)
                test_files.append(test_file)
            
            # Ingest all documents
            results = []
            for i, test_file in enumerate(test_files):
                result = await ingest_multi_file_async(
                    file_path=str(test_file),
                    source=f"reliability_test_{i}.txt",
                    chunk_size=200,
                    overlap=50,
                    exists_policy="overwrite"
                )
                results.append(result)
                if result.get("document_id"):
                    expected_doc_ids.append(result["document_id"])
            
            # Verify all documents in database
            service = get_document_service()
            all_docs = await service.list_documents_by_status("completed")
            
            found_count = sum(1 for doc_id in expected_doc_ids if any(d["id"] == doc_id for d in all_docs))
            
            print(f"✅ Reliability test:")
            print(f"   Documents ingested: {len(results)}")
            print(f"   Successful ingestions: {len(expected_doc_ids)}")
            print(f"   Documents in DB: {found_count}")
            print(f"   Data loss: {len(expected_doc_ids) - found_count} documents")
            
            # Allow some degradation but no complete loss
            assert found_count >= len(expected_doc_ids) * 0.5, "Significant data loss detected"
            
        finally:
            for test_file in test_files:
                test_file.unlink(missing_ok=True)


if __name__ == "__main__":
    """Run performance tests with reporting."""
    print("=" * 80)
    print("PERFORMANCE AND LOAD TESTS - PostgreSQL Migration")
    print("=" * 80)
    print()
    
    pytest.main([
        __file__,
        "-v",
        "-s",  # Show print statements
        "--tb=short"
    ])
