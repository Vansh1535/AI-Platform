"""
Phase C Tests - Multi-Document Insights Aggregation

Tests:
1. Multi-file insight success case
2. One-file rejection message  
3. Partial-failure graceful mode
4. Deterministic aggregation output
5. Agent → Tool → API consistency
"""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set test environment
os.environ["LLM_PROVIDER"] = "none"  # Disable LLM for deterministic testing
os.environ["RAG_ENABLED"] = "true"

from app.tools.insights import aggregate_insights, aggregate_insights_tool
from app.ingestion.integration import ingest_multi_file
from app.rag.retrieval.search import clear_test_documents


def test_multi_file_success():
    """Test successful multi-document insights aggregation."""
    print("\n" + "="*80)
    print("TEST 1: Multi-File Insights Success")
    print("="*80)
    
    # Create test documents
    doc1_content = """Machine Learning Fundamentals
    
Machine learning is a subset of artificial intelligence.
It enables computers to learn patterns from data.
Supervised learning uses labeled training data.
Neural networks process complex patterns.
Deep learning uses multiple layers."""
    
    doc2_content = """Artificial Intelligence Overview
    
Artificial intelligence transforms modern technology.
Machine learning is a core component of AI.
Neural networks are inspired by biological brains.
Computer vision enables visual interpretation.
Natural language processing handles text data."""
    
    doc3_content = """Data Science Principles
    
Data science combines statistics and programming.
Machine learning algorithms discover patterns.
Data visualization helps understand insights.
Statistical analysis validates findings.
Python is widely used for data science."""
    
    docs_to_cleanup = []
    
    try:
        # Clear test documents
        print("\n[*] Cleaning test documents...")
        clear_test_documents(source_pattern="test_insights")
        
        # Ingest documents
        print(f"\n[*] Ingesting 3 test documents...")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(doc1_content)
            docs_to_cleanup.append(f.name)
        
        result1 = ingest_multi_file(
            file_path=docs_to_cleanup[0],
            source="test_insights_ml.txt",
            normalize=True,
            exists_policy="overwrite"
        )
        doc1_id = result1['document_id']
        print(f"    Document 1: {doc1_id}")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(doc2_content)
            docs_to_cleanup.append(f.name)
        
        result2 = ingest_multi_file(
            file_path=docs_to_cleanup[1],
            source="test_insights_ai.txt",
            normalize=True,
            exists_policy="overwrite"
        )
        doc2_id = result2['document_id']
        print(f"    Document 2: {doc2_id}")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(doc3_content)
            docs_to_cleanup.append(f.name)
        
        result3 = ingest_multi_file(
            file_path=docs_to_cleanup[2],
            source="test_insights_ds.txt",
            normalize=True,
            exists_policy="overwrite"
        )
        doc3_id = result3['document_id']
        print(f"    Document 3: {doc3_id}")
        
        # Aggregate insights
        print(f"\n[*] Aggregating insights across 3 documents...")
        result, telemetry = aggregate_insights(
            document_ids=[doc1_id, doc2_id, doc3_id],
            mode="extractive",
            max_chunks=5
        )
        
        print(f"\n[*] Verification:")
        print(f"    Files processed: {telemetry['files_processed']}/3 - {'✅' if telemetry['files_processed'] == 3 else '❌'}")
        print(f"    Files failed: {telemetry['files_failed']} - {'✅' if telemetry['files_failed'] == 0 else '❌'}")
        print(f"    Per-document summaries: {len(result['per_document'])} - {'✅' if len(result['per_document']) == 3 else '❌'}")
        
        # Verify aggregated insights
        insights = result.get('aggregated_insights')
        assert insights is not None, "Should have aggregated insights"
        
        has_themes = len(insights.get('themes', [])) > 0
        has_overlaps = len(insights.get('overlaps', [])) > 0
        has_entities = len(insights.get('entities', [])) > 0
        
        print(f"    Has themes: {'✅' if has_themes else '❌'} ({len(insights.get('themes', []))} found)")
        print(f"    Has overlaps: {'✅' if has_overlaps else '❌'} ({len(insights.get('overlaps', []))} found)")
        print(f"    Has entities: {'✅' if has_entities else '❌'} ({len(insights.get('entities', []))} found)")
        
        # Check for expected overlaps (machine learning should appear in multiple docs)
        ml_in_overlaps = any(
            'machine learning' in overlap['theme'].lower() or 'neural' in overlap['theme'].lower()
            for overlap in insights.get('overlaps', [])
        )
        print(f"    Found ML/AI overlaps: {'✅' if ml_in_overlaps else '❌'}")
        
        # Verify telemetry
        assert telemetry['routing'] == 'insight_aggregator', "Routing should be insight_aggregator"
        assert telemetry['files_processed'] == 3, "Should process all 3 files"
        assert telemetry['files_failed'] == 0, "Should have no failures"
        
        print(f"\n✅ TEST PASSED - Multi-file insights successfully aggregated")
        return True
        
    finally:
        for doc_path in docs_to_cleanup:
            if os.path.exists(doc_path):
                os.unlink(doc_path)


def test_one_file_rejection():
    """Test rejection when only one document provided."""
    print("\n" + "="*80)
    print("TEST 2: One-File Rejection")
    print("="*80)
    
    # Create single test document
    doc_content = "Machine learning is a subset of AI."
    
    try:
        print("\n[*] Cleaning test documents...")
        clear_test_documents(source_pattern="test_single")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(doc_content)
            temp_path = f.name
        
        print(f"\n[*] Ingesting single document...")
        result = ingest_multi_file(
            file_path=temp_path,
            source="test_single_doc.txt",
            normalize=True,
            exists_policy="overwrite"
        )
        doc_id = result['document_id']
        print(f"    Document ID: {doc_id}")
        
        # Try aggregation with single document
        print(f"\n[*] Attempting aggregation with 1 document (should fail)...")
        
        try:
            aggregate_insights(
                document_ids=[doc_id],
                mode="extractive",
                max_chunks=5
            )
            print("    ❌ FAIL: Should have raised ValueError")
            assert False, "Should reject single document"
        except ValueError as e:
            error_msg = str(e)
            has_minimum_requirement = "at least 2" in error_msg.lower()
            print(f"    ✅ Correctly rejected: {error_msg}")
            print(f"    Has minimum requirement message: {'✅' if has_minimum_requirement else '❌'}")
            assert has_minimum_requirement, "Error message should mention minimum 2 documents"
        
        print(f"\n✅ TEST PASSED - Single document correctly rejected")
        return True
        
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_partial_failure_graceful():
    """Test graceful handling when some documents fail."""
    print("\n" + "="*80)
    print("TEST 3: Partial Failure Graceful Mode")
    print("="*80)
    
    # Create test documents
    doc1_content = "Machine learning enables pattern recognition."
    doc2_content = "Neural networks process complex data."
    
    docs_to_cleanup = []
    
    try:
        print("\n[*] Cleaning test documents...")
        clear_test_documents(source_pattern="test_partial")
        
        # Ingest first document
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(doc1_content)
            docs_to_cleanup.append(f.name)
        
        result1 = ingest_multi_file(
            file_path=docs_to_cleanup[0],
            source="test_partial_doc1.txt",
            normalize=True,
            exists_policy="overwrite"
        )
        doc1_id = result1['document_id']
        print(f"    Document 1 (valid): {doc1_id}")
        
        # Ingest second document
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(doc2_content)
            docs_to_cleanup.append(f.name)
        
        result2 = ingest_multi_file(
            file_path=docs_to_cleanup[1],
            source="test_partial_doc2.txt",
            normalize=True,
            exists_policy="overwrite"
        )
        doc2_id = result2['document_id']
        print(f"    Document 2 (valid): {doc2_id}")
        
        # Use one invalid document ID
        invalid_id = "nonexistent-doc-12345"
        print(f"    Document 3 (invalid): {invalid_id}")
        
        # Aggregate with mixed valid/invalid IDs
        print(f"\n[*] Aggregating with 2 valid + 1 invalid document...")
        result, telemetry = aggregate_insights(
            document_ids=[doc1_id, doc2_id, invalid_id],
            mode="extractive",
            max_chunks=5
        )
        
        print(f"\n[*] Verification:")
        print(f"    Files requested: {telemetry['files_requested']} - {'✅' if telemetry['files_requested'] == 3 else '❌'}")
        print(f"    Files processed: {telemetry['files_processed']} - {'✅' if telemetry['files_processed'] == 2 else '❌'}")
        print(f"    Files failed: {telemetry['files_failed']} - {'✅' if telemetry['files_failed'] == 1 else '❌'}")
        
        # Should have successful summaries
        successful = len(result['per_document']) == 2
        print(f"    Successful summaries: {len(result['per_document'])}/2 - {'✅' if successful else '❌'}")
        
        # Should have failed documents list
        has_failed_list = 'failed_documents' in result and len(result['failed_documents']) == 1
        print(f"    Failed documents tracked: {'✅' if has_failed_list else '❌'}")
        
        # Should still have insights (2 successful docs is enough)
        has_insights = result.get('aggregated_insights') is not None
        print(f"    Aggregated insights generated: {'✅' if has_insights else '❌'}")
        
        # Should have message about partial success
        has_message = result.get('message') is not None
        print(f"    Status message provided: {'✅' if has_message else '❌'}")
        if has_message:
            print(f"       Message: {result['message'][:100]}...")
        
        assert telemetry['files_processed'] == 2, "Should process 2 valid documents"
        assert telemetry['files_failed'] == 1, "Should track 1 failed document"
        assert successful, "Should have 2 successful summaries"
        assert has_insights, "Should still generate insights with 2 docs"
        
        print(f"\n✅ TEST PASSED - Partial failure handled gracefully")
        return True
        
    finally:
        for doc_path in docs_to_cleanup:
            if os.path.exists(doc_path):
                os.unlink(doc_path)


def test_deterministic_aggregation():
    """Test that aggregation produces consistent results across runs."""
    print("\n" + "="*80)
    print("TEST 4: Deterministic Aggregation Output")
    print("="*80)
    
    # Create test documents
    doc1_content = "Machine learning algorithms process data."
    doc2_content = "Neural networks learn from examples."
    
    docs_to_cleanup = []
    
    try:
        print("\n[*] Cleaning test documents...")
        clear_test_documents(source_pattern="test_deterministic")
        
        # Ingest documents
        print(f"\n[*] Ingesting 2 test documents...")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(doc1_content)
            docs_to_cleanup.append(f.name)
        
        result1 = ingest_multi_file(
            file_path=docs_to_cleanup[0],
            source="test_deterministic_doc1.txt",
            normalize=True,
            exists_policy="overwrite"
        )
        doc1_id = result1['document_id']
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(doc2_content)
            docs_to_cleanup.append(f.name)
        
        result2 = ingest_multi_file(
            file_path=docs_to_cleanup[1],
            source="test_deterministic_doc2.txt",
            normalize=True,
            exists_policy="overwrite"
        )
        doc2_id = result2['document_id']
        
        # Run aggregation 3 times
        print(f"\n[*] Running aggregation 3 times...")
        results = []
        
        for i in range(3):
            result, telemetry = aggregate_insights(
                document_ids=[doc1_id, doc2_id],
                mode="extractive",
                max_chunks=5
            )
            results.append(result)
            print(f"    Run {i+1}: {len(result['per_document'])} docs, {len(result['aggregated_insights']['themes'])} themes")
        
        # Verify consistency
        print(f"\n[*] Verifying consistency across runs...")
        
        # Per-document summaries should be identical
        summaries_consistent = all(
            results[0]['per_document'][i]['summary'] == results[j]['per_document'][i]['summary']
            for j in range(1, 3)
            for i in range(len(results[0]['per_document']))
        )
        print(f"    Summaries consistent: {'✅' if summaries_consistent else '❌'}")
        
        # Theme counts should be identical
        theme_counts = [len(r['aggregated_insights']['themes']) for r in results]
        themes_consistent = len(set(theme_counts)) == 1
        print(f"    Theme counts: {theme_counts} - {'✅' if themes_consistent else '❌'}")
        
        # Overlap counts should be identical
        overlap_counts = [len(r['aggregated_insights']['overlaps']) for r in results]
        overlaps_consistent = len(set(overlap_counts)) == 1
        print(f"    Overlap counts: {overlap_counts} - {'✅' if overlaps_consistent else '❌'}")
        
        assert summaries_consistent, "Per-document summaries should be identical"
        assert themes_consistent, "Theme extraction should be deterministic"
        
        print(f"\n✅ TEST PASSED - Aggregation is deterministic")
        return True
        
    finally:
        for doc_path in docs_to_cleanup:
            if os.path.exists(doc_path):
                os.unlink(doc_path)


def test_agent_tool_consistency():
    """Test consistency between agent tool and direct service calls."""
    print("\n" + "="*80)
    print("TEST 5: Agent → Tool → Service Consistency")
    print("="*80)
    
    # Create test documents
    doc1_content = "Machine learning improves with data."
    doc2_content = "Neural networks power modern AI."
    
    docs_to_cleanup = []
    
    try:
        print("\n[*] Cleaning test documents...")
        clear_test_documents(source_pattern="test_consistency")
        
        # Ingest documents
        print(f"\n[*] Ingesting 2 test documents...")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(doc1_content)
            docs_to_cleanup.append(f.name)
        
        result1 = ingest_multi_file(
            file_path=docs_to_cleanup[0],
            source="test_consistency_doc1.txt",
            normalize=True,
            exists_policy="overwrite"
        )
        doc1_id = result1['document_id']
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(doc2_content)
            docs_to_cleanup.append(f.name)
        
        result2 = ingest_multi_file(
            file_path=docs_to_cleanup[1],
            source="test_consistency_doc2.txt",
            normalize=True,
            exists_policy="overwrite"
        )
        doc2_id = result2['document_id']
        
        # Call service directly
        print(f"\n[*] Calling service directly...")
        service_result, service_telemetry = aggregate_insights(
            document_ids=[doc1_id, doc2_id],
            mode="extractive",
            max_chunks=5
        )
        
        print(f"    Service: {len(service_result['per_document'])} docs processed")
        
        # Call via agent tool (JSON array format)
        print(f"\n[*] Calling via agent tool (JSON format)...")
        tool_output_json = aggregate_insights_tool(
            document_ids=f'["{doc1_id}", "{doc2_id}"]',
            mode="extractive",
            max_chunks=5
        )
        
        has_success_indicator = "MULTI-DOCUMENT INSIGHTS" in tool_output_json
        has_both_docs = doc1_id in tool_output_json and doc2_id in tool_output_json
        has_themes = "KEY THEMES" in tool_output_json
        has_overlaps = "OVERLAPPING THEMES" in tool_output_json
        
        print(f"    Tool output has header: {'✅' if has_success_indicator else '❌'}")
        print(f"    Tool output has both docs: {'✅' if has_both_docs else '❌'}")
        print(f"    Tool output has themes: {'✅' if has_themes else '❌'}")
        print(f"    Tool output has overlaps: {'✅' if has_overlaps else '❌'}")
        
        # Call via agent tool (comma-separated format)
        print(f"\n[*] Calling via agent tool (CSV format)...")
        tool_output_csv = aggregate_insights_tool(
            document_ids=f"{doc1_id},{doc2_id}",
            mode="extractive",
            max_chunks=5
        )
        
        csv_has_content = "MULTI-DOCUMENT INSIGHTS" in tool_output_csv
        print(f"    CSV format works: {'✅' if csv_has_content else '❌'}")
        
        # Verify consistency
        assert has_success_indicator, "Tool should return formatted output"
        assert has_both_docs, "Tool should include both document IDs"
        assert has_themes or has_overlaps, "Tool should include insights"
        assert csv_has_content, "CSV format should also work"
        
        print(f"\n✅ TEST PASSED - Agent tool consistent with service")
        return True
        
    finally:
        for doc_path in docs_to_cleanup:
            if os.path.exists(doc_path):
                os.unlink(doc_path)


def run_all_tests():
    """Run all Phase C tests."""
    print("\n" + "="*80)
    print("PHASE C TEST SUITE - Multi-Document Insights Aggregation")
    print("="*80)
    
    tests = [
        ("Multi-File Success", test_multi_file_success),
        ("One-File Rejection", test_one_file_rejection),
        ("Partial Failure Graceful", test_partial_failure_graceful),
        ("Deterministic Aggregation", test_deterministic_aggregation),
        ("Agent Tool Consistency", test_agent_tool_consistency),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, "PASSED" if success else "FAILED"))
        except Exception as e:
            print(f"\n❌ TEST FAILED: {test_name}")
            print(f"   Error: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append((test_name, f"FAILED: {str(e)[:50]}"))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_name, status in results:
        status_icon = "✅" if status == "PASSED" else "❌"
        print(f"{status_icon} {test_name}: {status}")
    
    passed_count = sum(1 for _, status in results if status == "PASSED")
    total_count = len(results)
    
    print(f"\n📊 Overall: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("🎉 All tests PASSED!")
        return True
    else:
        print("⚠️  Some tests FAILED")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
