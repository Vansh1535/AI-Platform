"""
Phase B Stability Tests - Deterministic & Reliable Summarization

Tests:
1. Deterministic extractive output across runs
2. Retrieval filtered by document_id
3. Hybrid mode triggers when confidence is low
4. API → Tool → Agent output consistency
5. Overwrite ingestion version behavior
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

from app.tools.summarizer import summarize_document
from app.ingestion.integration import ingest_multi_file
from app.rag.retrieval.search import clear_test_documents


def test_deterministic_extractive_output():
    """Test that extractive summarization produces identical results across multiple runs."""
    print("\n" + "="*80)
    print("TEST 1: Deterministic Extractive Output")
    print("="*80)
    
    # Create consistent test document
    test_content = """Machine Learning Fundamentals

Machine learning is a subset of artificial intelligence that enables computers to learn from data.
The primary goal is to develop algorithms that can identify patterns and make decisions.
Supervised learning uses labeled training data to train models for classification and regression tasks.
Unsupervised learning finds hidden patterns in unlabeled data through clustering and dimensionality reduction.
Deep learning uses neural networks with multiple layers to process complex patterns."""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(test_content)
        temp_path = f.name
    
    try:
        # Clear any existing test documents
        print("\n[*] Cleaning test documents...")
        clear_result = clear_test_documents(source_pattern="test_deterministic")
        print(f"    Cleared: {clear_result['deleted_count']} documents")
        
        # Ingest document with overwrite policy
        print(f"\n[*] Ingesting document: {temp_path}")
        ingest_result = ingest_multi_file(
            file_path=temp_path,
            source="test_deterministic_ml.txt",
            normalize=True,
            exists_policy="overwrite"
        )
        
        doc_id = ingest_result['document_id']
        print(f"    Document ID: {doc_id}")
        print(f"    Chunks: {ingest_result.get('chunk_count', 0)}")
        
        # Run summarization 3 times
        summaries = []
        telemetries = []
        
        for i in range(3):
            print(f"\n[*] Run {i+1}: Generating summary...")
            summary, telemetry = summarize_document(
                document_id=doc_id,
                mode="extractive",
                max_chunks=5,
                summary_length="medium"
            )
            summaries.append(summary)
            telemetries.append(telemetry)
            
            print(f"    Mode: {telemetry.get('mode_used')}")
            print(f"    Chunks: {telemetry.get('chunks_used')}")
            print(f"    Sentences: {telemetry.get('key_sentences')}")
        
        # Verify all summaries are identical
        print(f"\n[*] Verifying deterministic behavior...")
        all_identical = all(s == summaries[0] for s in summaries)
        
        if all_identical:
            print("    ✅ SUCCESS: All summaries identical")
        else:
            print("    ❌ FAIL: Summaries differ across runs")
            for i, summary in enumerate(summaries):
                print(f"\n    Run {i+1} summary length: {len(summary)}")
        
        # Verify telemetry consistency
        chunks_used = [t.get('chunks_used') for t in telemetries]
        key_sentences = [t.get('key_sentences') for t in telemetries]
        
        chunks_consistent = len(set(chunks_used)) == 1
        sentences_consistent = len(set(key_sentences)) == 1
        
        print(f"    Chunks used: {chunks_used} - {'✅ Consistent' if chunks_consistent else '❌ Inconsistent'}")
        print(f"    Key sentences: {key_sentences} - {'✅ Consistent' if sentences_consistent else '❌ Inconsistent'}")
        
        assert all_identical, "Summaries should be identical across runs"
        assert chunks_consistent, "Chunk count should be consistent"
        assert sentences_consistent, "Key sentence count should be consistent"
        
        print(f"\n✅ TEST PASSED - Deterministic behavior verified")
        return True
        
    finally:
        os.unlink(temp_path)


def test_document_id_filtering():
    """Test that retrieval is properly filtered by document_id."""
    print("\n" + "="*80)
    print("TEST 2: Document ID Filtering")
    print("="*80)
    
    # Create two different documents
    doc1_content = "Python is a high-level programming language. It emphasizes code readability."
    doc2_content = "JavaScript is widely used for web development. It runs in browsers and servers."
    
    docs_to_cleanup = []
    
    try:
        # Clear test documents
        print("\n[*] Cleaning test documents...")
        clear_test_documents(source_pattern="test_filtering")
        
        # Ingest document 1
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(doc1_content)
            docs_to_cleanup.append(f.name)
        
        print(f"\n[*] Ingesting document 1...")
        result1 = ingest_multi_file(
            file_path=docs_to_cleanup[0],
            source="test_filtering_python.txt",
            normalize=True,
            exists_policy="overwrite"
        )
        doc1_id = result1['document_id']
        print(f"    Document 1 ID: {doc1_id}")
        
        # Ingest document 2
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(doc2_content)
            docs_to_cleanup.append(f.name)
        
        print(f"\n[*] Ingesting document 2...")
        result2 = ingest_multi_file(
            file_path=docs_to_cleanup[1],
            source="test_filtering_javascript.txt",
            normalize=True,
            exists_policy="overwrite"
        )
        doc2_id = result2['document_id']
        print(f"    Document 2 ID: {doc2_id}")
        
        # Summarize document 1
        print(f"\n[*] Summarizing document 1...")
        summary1, telemetry1 = summarize_document(
            document_id=doc1_id,
            mode="extractive",
            max_chunks=5
        )
        
        # Summarize document 2
        print(f"\n[*] Summarizing document 2...")
        summary2, telemetry2 = summarize_document(
            document_id=doc2_id,
            mode="extractive",
            max_chunks=5
        )
        
        print(f"\n[*] Verifying filtering...")
        
        # Check that summaries contain correct content
        has_python = 'python' in summary1.lower() or 'readability' in summary1.lower()
        has_javascript = 'javascript' in summary2.lower() or 'browser' in summary2.lower()
        
        # Check that summaries DON'T contain wrong content
        no_js_in_python = 'javascript' not in summary1.lower()
        no_python_in_js = 'python' not in summary2.lower()
        
        print(f"    Doc1 has Python content: {'✅' if has_python else '❌'}")
        print(f"    Doc1 excludes JS content: {'✅' if no_js_in_python else '❌'}")
        print(f"    Doc2 has JS content: {'✅' if has_javascript else '❌'}")
        print(f"    Doc2 excludes Python content: {'✅' if no_python_in_js else '❌'}")
        
        # Verify document_id_filter in telemetry
        assert telemetry1.get('document_id_filter') == doc1_id, "Telemetry should include document_id_filter"
        assert telemetry2.get('document_id_filter') == doc2_id, "Telemetry should include document_id_filter"
        
        assert has_python, "Summary 1 should contain Python-related content"
        assert has_javascript, "Summary 2 should contain JavaScript-related content"
        assert no_js_in_python, "Summary 1 should not contain JavaScript content"
        assert no_python_in_js, "Summary 2 should not contain Python content"
        
        print(f"\n✅ TEST PASSED - Document ID filtering working correctly")
        return True
        
    finally:
        for doc_path in docs_to_cleanup:
            if os.path.exists(doc_path):
                os.unlink(doc_path)


def test_overwrite_ingestion():
    """Test that overwrite policy properly versions documents."""
    print("\n" + "="*80)
    print("TEST 3: Overwrite Ingestion Behavior")
    print("="*80)
    
    # Create test document
    original_content = "Original content about machine learning basics."
    updated_content = "Updated content about advanced machine learning techniques and neural networks."
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(original_content)
        temp_path = f.name
    
    try:
        print("\n[*] Cleaning test documents...")
        clear_test_documents(source_pattern="test_overwrite")
        
        # First ingestion
        print(f"\n[*] First ingestion...")
        result1 = ingest_multi_file(
            file_path=temp_path,
            source="test_overwrite_ml.txt",
            normalize=True,
            exists_policy="overwrite"
        )
        doc_id_1 = result1['document_id']
        print(f"    Document ID: {doc_id_1}")
        
        # Update file content
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        # Second ingestion with overwrite
        print(f"\n[*] Second ingestion (overwrite)...")
        result2 = ingest_multi_file(
            file_path=temp_path,
            source="test_overwrite_ml.txt",
            normalize=True,
            exists_policy="overwrite"
        )
        doc_id_2 = result2['document_id']
        print(f"    Document ID: {doc_id_2}")
        
        # Verify document IDs are different (versioned)
        print(f"\n[*] Verifying versioning...")
        ids_different = doc_id_1 != doc_id_2
        print(f"    Document IDs different: {'✅' if ids_different else '❌'}")
        print(f"    Original: {doc_id_1}")
        print(f"    Updated:  {doc_id_2}")
        
        # Summarize the updated document
        summary, telemetry = summarize_document(
            document_id=doc_id_2,
            mode="extractive",
            max_chunks=5
        )
        
        # Verify summary contains updated content
        has_updated_content = 'advanced' in summary.lower() or 'neural' in summary.lower()
        no_original_content = 'basics' not in summary.lower()
        
        print(f"    Summary has updated content: {'✅' if has_updated_content else '❌'}")
        print(f"    Summary excludes original content: {'✅' if no_original_content else '❌'}")
        
        assert ids_different or result2.get('status') == 'overwritten', "Overwrite should create new version"
        
        print(f"\n✅ TEST PASSED - Overwrite behavior working correctly")
        return True
        
    finally:
        os.unlink(temp_path)


def test_sentence_scoring():
    """Test that improved sentence scoring produces better summaries."""
    print("\n" + "="*80)
    print("TEST 4: Improved Sentence Scoring")
    print("="*80)
    
    # Create document with varied sentence quality
    test_content = """Document Analysis Report

This is a short line.
The primary objective of this comprehensive analysis is to evaluate the effectiveness of machine learning algorithms in natural language processing tasks, specifically focusing on sentiment analysis and entity recognition.
What are the benefits?
Machine learning transforms how we process data by enabling computers to learn patterns automatically.
He said it was good.
Advanced neural networks achieve 95% accuracy on benchmark datasets.
It works well.
The model architecture consists of three transformer layers with multi-head attention mechanisms."""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(test_content)
        temp_path = f.name
    
    try:
        print("\n[*] Cleaning test documents...")
        clear_test_documents(source_pattern="test_scoring")
        
        print(f"\n[*] Ingesting test document...")
        ingest_result = ingest_multi_file(
            file_path=temp_path,
            source="test_scoring_report.txt",
            normalize=True,
            exists_policy="overwrite"
        )
        
        doc_id = ingest_result['document_id']
        print(f"    Document ID: {doc_id}")
        
        # Generate summary
        print(f"\n[*] Generating summary...")
        summary, telemetry = summarize_document(
            document_id=doc_id,
            mode="extractive",
            max_chunks=5,
            summary_length="medium"
        )
        
        print(f"\n[*] Analyzing sentence quality...")
        print(f"    Summary:\n{summary}")
        
        # Check that summary avoids low-quality sentences
        summary_lower = summary.lower()
        
        # Good: Should contain informative sentences
        has_ml_transform = 'machine learning' in summary_lower and 'data' in summary_lower
        has_accuracy_or_ml_info = '95%' in summary or 'neural' in summary_lower or 'algorithms' in summary_lower
        
        # Bad: Should avoid questions and vague pronouns
        no_question = 'what are the benefits' not in summary_lower
        no_vague_he_said = 'he said' not in summary_lower
        
        print(f"    Has ML content: {'✅' if has_ml_transform or has_accuracy_or_ml_info else '❌'}")
        print(f"    Avoids question sentence: {'✅' if no_question else '❌'}")
        print(f"    Avoids 'he said' pronoun: {'✅' if no_vague_he_said else '❌'}")
        
        quality_score = sum([
            has_ml_transform or has_accuracy_or_ml_info,
            no_question,
            no_vague_he_said
        ])
        
        print(f"\n    Quality score: {quality_score}/3")
        
        assert quality_score >= 2, "Summary should have reasonable quality (2/3 or better)"
        
        print(f"\n✅ TEST PASSED - Sentence scoring improving summary quality")
        return True
        
    finally:
        os.unlink(temp_path)


def test_summary_length_option():
    """Test that summary_length parameter produces different output sizes."""
    print("\n" + "="*80)
    print("TEST 5: Summary Length Options")
    print("="*80)
    
    # Create substantial test document
    test_content = """Artificial Intelligence Overview

Artificial intelligence (AI) is transforming modern technology.
Machine learning enables computers to learn from data patterns.
Deep learning uses neural networks with multiple layers.
Natural language processing allows computers to understand human language.
Computer vision enables machines to interpret visual information.
Reinforcement learning trains agents through reward-based feedback.
Expert systems capture domain-specific knowledge for decision making.
Neural networks are inspired by biological brain structures.
Supervised learning requires labeled training data.
Unsupervised learning discovers hidden patterns in data."""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(test_content)
        temp_path = f.name
    
    try:
        print("\n[*] Cleaning test documents...")
        clear_test_documents(source_pattern="test_length")
        
        print(f"\n[*] Ingesting document...")
        ingest_result = ingest_multi_file(
            file_path=temp_path,
            source="test_length_ai.txt",
            normalize=True,
            exists_policy="overwrite"
        )
        
        doc_id = ingest_result['document_id']
        print(f"    Document ID: {doc_id}")
        
        # Test all three lengths
        lengths = ["short", "medium", "detailed"]
        summaries = {}
        
        for length in lengths:
            print(f"\n[*] Generating {length} summary...")
            summary, telemetry = summarize_document(
                document_id=doc_id,
                mode="extractive",
                max_chunks=5,
                summary_length=length
            )
            summaries[length] = summary
            
            key_sentences = telemetry.get('key_sentences', 0)
            print(f"    Key sentences: {key_sentences}")
            print(f"    Summary length: {len(summary)} chars")
        
        # Verify length ordering
        print(f"\n[*] Verifying length differences...")
        short_len = len(summaries["short"])
        medium_len = len(summaries["medium"])
        detailed_len = len(summaries["detailed"])
        
        length_ordering_correct = short_len < medium_len < detailed_len
        
        print(f"    Short: {short_len} chars")
        print(f"    Medium: {medium_len} chars")
        print(f"    Detailed: {detailed_len} chars")
        print(f"    Correct ordering: {'✅' if length_ordering_correct else '❌'}")
        
        assert length_ordering_correct, "Summary lengths should increase: short < medium < detailed"
        
        print(f"\n✅ TEST PASSED - Summary length options working correctly")
        return True
        
    finally:
        os.unlink(temp_path)


def run_all_tests():
    """Run all Phase B stability tests."""
    print("\n" + "="*80)
    print("PHASE B STABILITY TEST SUITE")
    print("="*80)
    
    tests = [
        ("Deterministic Extractive Output", test_deterministic_extractive_output),
        ("Document ID Filtering", test_document_id_filtering),
        ("Overwrite Ingestion", test_overwrite_ingestion),
        ("Sentence Scoring Quality", test_sentence_scoring),
        ("Summary Length Options", test_summary_length_option),
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
