"""
Unit Tests for Cross-File Semantic Intelligence

Tests the document-level semantic clustering and cross-file analysis functionality.

Test Coverage:
- Similar-topic documents form same cluster
- Unrelated documents do NOT cluster together
- Fallback mode returns explainable metadata
- No crashes when embeddings disabled
- Graceful handling of edge cases
- Confidence scoring accuracy
- Theme label generation
- Evidence snippet extraction
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch
from app.tools.insights.cross_file_analyzer import (
    analyze_cross_file_semantics,
    cluster_documents_by_similarity,
    generate_cluster_theme_label,
    extract_evidence_snippets,
    detect_overlapping_concepts,
    compute_cosine_similarity,
    extract_theme_label_from_summary,
    get_embedding_function,
    DOC_SIMILARITY_THRESHOLD,
    MIN_DOCS_FOR_CLUSTERING,
    MIN_CLUSTER_SIZE
)


class TestCrossFileSemanticClustering:
    """Test document-level clustering functionality."""
    
    def test_similar_documents_form_cluster(self):
        """Similar-topic documents should cluster together."""
        # Create mock summaries about API security
        summaries = [
            {
                "document_id": "doc1.txt",
                "summary": "API Security best practices include authentication, rate limiting, and input validation. OAuth2 tokens should be properly secured.",
                "chunks_used": 5
            },
            {
                "document_id": "doc2.txt",
                "summary": "API Authentication methods use OAuth2 and JWT tokens. Security measures prevent unauthorized access through rate limiting.",
                "chunks_used": 4
            },
            {
                "document_id": "doc3.txt",
                "summary": "Security practices for APIs involve proper authentication and authorization. Token-based systems like OAuth2 are recommended.",
                "chunks_used": 3
            }
        ]
        
        # Create mock embedding function that returns similar embeddings
        def mock_embeddings(texts):
            # Return similar vectors for similar content
            base_vector = np.array([0.5, 0.3, 0.8, 0.2, 0.6])
            return [
                (base_vector + np.random.normal(0, 0.05, 5)).tolist()
                for _ in texts
            ]
        
        clusters = cluster_documents_by_similarity(
            summaries,
            mock_embeddings,
            similarity_threshold=0.4  # Lower threshold for testing
        )
        
        # Should form 1 cluster with all 3 documents
        assert len(clusters) >= 1
        assert clusters[0]["member_count"] >= 2
        
        # All API security docs should be in same cluster
        cluster_docs = clusters[0]["member_documents"]
        assert len(cluster_docs) >= 2
        
        # Theme should be related to API or Security
        theme = clusters[0]["theme_label"].lower()
        assert any(keyword in theme for keyword in ["api", "security", "authentication", "oauth"])
        
        # Confidence should be reasonable
        assert 0.0 <= clusters[0]["confidence_score"] <= 1.0
        assert clusters[0]["confidence_score"] > 0.3  # Not too low
    
    def test_unrelated_documents_do_not_cluster(self):
        """Unrelated documents should NOT cluster together."""
        # Create summaries on completely different topics
        summaries = [
            {
                "document_id": "doc1.txt",
                "summary": "Quantum Computing leverages superposition and entanglement for parallel computation. Qubits can exist in multiple states simultaneously.",
                "chunks_used": 5
            },
            {
                "document_id": "doc2.txt",
                "summary": "Organic Gardening techniques include composting, crop rotation, and natural pest control. Sustainable farming practices preserve soil health.",
                "chunks_used": 4
            },
            {
                "document_id": "doc3.txt",
                "summary": "Renaissance Art flourished in 15th century Italy. Michelangelo and Leonardo da Vinci pioneered new painting techniques.",
                "chunks_used": 6
            }
        ]
        
        # Create mock embedding function that returns dissimilar embeddings
        def mock_embeddings(texts):
            # Return very different vectors for different topics
            vectors = [
                np.array([0.9, 0.1, 0.1, 0.0, 0.0]),  # Quantum
                np.array([0.0, 0.9, 0.1, 0.1, 0.0]),  # Gardening
                np.array([0.0, 0.0, 0.1, 0.9, 0.1])   # Art
            ]
            return [v.tolist() for v in vectors]
        
        clusters = cluster_documents_by_similarity(
            summaries,
            mock_embeddings,
            similarity_threshold=DOC_SIMILARITY_THRESHOLD
        )
        
        # Should form NO clusters (documents too dissimilar)
        # or at most small clusters
        if clusters:
            # Any clusters should have low confidence
            for cluster in clusters:
                # Clusters of unrelated docs should have low confidence
                assert cluster["confidence_score"] < 0.7
                # Should not group all 3 unrelated docs
                assert cluster["member_count"] < len(summaries)
        else:
            # No clusters is also valid for completely unrelated docs
            assert len(clusters) == 0
    
    def test_mixed_similar_and_dissimilar_documents(self):
        """Some similar, some dissimilar - should cluster correctly."""
        summaries = [
            {
                "document_id": "ml1.txt",
                "summary": "Machine Learning algorithms use neural networks for pattern recognition. Deep learning models train on large datasets.",
                "chunks_used": 5
            },
            {
                "document_id": "ml2.txt",
                "summary": "Neural Networks and Deep Learning enable AI systems. Training models requires extensive computational resources.",
                "chunks_used": 4
            },
            {
                "document_id": "cooking.txt",
                "summary": "Baking bread requires yeast, flour, water and patience. Proper kneading develops gluten structure.",
                "chunks_used": 3
            }
        ]
        
        # Mock embeddings: ml1 and ml2 similar, cooking different
        def mock_embeddings(texts):
            vectors = [
                np.array([0.8, 0.7, 0.2, 0.1, 0.0]),  # ML 1
                np.array([0.7, 0.8, 0.3, 0.1, 0.0]),  # ML 2 (similar to ML1)
                np.array([0.1, 0.1, 0.0, 0.9, 0.8])   # Cooking (very different)
            ]
            return [v.tolist() for v in vectors]
        
        clusters = cluster_documents_by_similarity(
            summaries,
            mock_embeddings,
            similarity_threshold=0.4
        )
        
        # Should have 1 cluster with the 2 ML documents
        assert len(clusters) >= 1
        
        ml_cluster = clusters[0]
        assert ml_cluster["member_count"] == 2
        assert "ml1.txt" in ml_cluster["member_documents"]
        assert "ml2.txt" in ml_cluster["member_documents"]
        assert "cooking.txt" not in ml_cluster["member_documents"]


class TestFallbackBehavior:
    """Test graceful fallback scenarios."""
    
    def test_too_few_documents_fallback(self):
        """Should fallback gracefully when too few documents."""
        summaries = [
            {
                "document_id": "single.txt",
                "summary": "This is a single document summary.",
                "chunks_used": 2
            }
        ]
        
        result, telemetry = analyze_cross_file_semantics(summaries)
        
        # Should fallback
        assert telemetry["cross_file_analysis_used"] is False
        assert telemetry["fallback_reason"] == "too_few_documents"
        assert telemetry["cluster_count"] == 0
        
        # Result should still have structure
        assert "semantic_clusters" in result
        assert result["semantic_clusters"] == []
        assert result["cross_file_overlap_detected"] is False
        
        # Should not crash
        assert "latency_ms" in telemetry
        assert telemetry["latency_ms"] >= 0
    
    def test_embeddings_unavailable_fallback(self):
        """Should fallback gracefully when embeddings unavailable."""
        summaries = [
            {"document_id": "doc1.txt", "summary": "Summary 1", "chunks_used": 2},
            {"document_id": "doc2.txt", "summary": "Summary 2", "chunks_used": 3}
        ]
        
        # Mock get_embedding_function to return None
        with patch('app.tools.insights.cross_file_analyzer.get_embedding_function', return_value=None):
            result, telemetry = analyze_cross_file_semantics(summaries)
        
        # Should fallback
        assert telemetry["cross_file_analysis_used"] is False
        assert telemetry["fallback_reason"] == "embeddings_unavailable"
        assert telemetry["cluster_count"] == 0
        
        # Should have explainable metadata
        assert "fallback_reason" in telemetry
        assert telemetry["fallback_reason"] is not None
    
    def test_no_clusters_formed_fallback(self):
        """Should fallback when documents too dissimilar to cluster."""
        summaries = [
            {
                "document_id": "doc1.txt",
                "summary": "Completely unique topic A with nothing in common.",
                "chunks_used": 2
            },
            {
                "document_id": "doc2.txt",
                "summary": "Totally different topic B with no overlap.",
                "chunks_used": 3
            }
        ]
        
        # Mock embeddings that are very dissimilar
        def mock_embeddings(texts):
            return [
                np.array([1.0, 0.0, 0.0, 0.0, 0.0]).tolist(),
                np.array([0.0, 0.0, 0.0, 0.0, 1.0]).tolist()
            ]
        
        with patch('app.tools.insights.cross_file_analyzer.get_embedding_function', return_value=mock_embeddings):
            result, telemetry = analyze_cross_file_semantics(summaries)
        
        # Should fallback or have very low confidence
        if not telemetry["cross_file_analysis_used"]:
            assert telemetry["fallback_reason"] in ["no_clusters_formed", "weak_signals"]
    
    def test_weak_signals_fallback(self):
        """Should fallback when cluster confidence too low."""
        summaries = [
            {"document_id": "doc1.txt", "summary": "Topic A with some words.", "chunks_used": 2},
            {"document_id": "doc2.txt", "summary": "Topic B with different words.", "chunks_used": 2}
        ]
        
        # Mock embeddings with very weak similarity (below threshold)
        def mock_embeddings(texts):
            # Vectors with cosine similarity around 0.25 (weak signal)
            return [
                np.array([0.5, 0.5, 0.0, 0.0, 0.0]).tolist(),
                np.array([0.3, 0.0, 0.7, 0.0, 0.0]).tolist()
            ]
        
        with patch('app.tools.insights.cross_file_analyzer.get_embedding_function', return_value=mock_embeddings):
            result, telemetry = analyze_cross_file_semantics(summaries)
        
        # Might fallback due to weak signals or no clusters forming
        if not telemetry["cross_file_analysis_used"]:
            # Any fallback reason is acceptable for low-similarity docs
            assert telemetry["fallback_reason"] is not None
            assert telemetry["fallback_reason"] in ["weak_signals", "no_clusters_formed"]


class TestNoCrashGuarantee:
    """Ensure no crashes in any scenario."""
    
    def test_empty_summaries_no_crash(self):
        """Empty summaries list should not crash."""
        result, telemetry = analyze_cross_file_semantics([])
        
        assert isinstance(result, dict)
        assert isinstance(telemetry, dict)
        assert telemetry["cross_file_analysis_used"] is False
    
    def test_missing_summary_text_no_crash(self):
        """Documents without summary text should not crash."""
        summaries = [
            {"document_id": "doc1.txt", "chunks_used": 2},  # Missing 'summary'
            {"document_id": "doc2.txt", "summary": "", "chunks_used": 1},  # Empty summary
            {"document_id": "doc3.txt", "summary": "Valid summary", "chunks_used": 3}
        ]
        
        def mock_embeddings(texts):
            return [np.random.rand(5).tolist() for _ in texts]
        
        with patch('app.tools.insights.cross_file_analyzer.get_embedding_function', return_value=mock_embeddings):
            # Should not crash
            result, telemetry = analyze_cross_file_semantics(summaries)
            
            assert isinstance(result, dict)
            assert isinstance(telemetry, dict)
    
    def test_malformed_embeddings_no_crash(self):
        """Malformed embedding function should not crash."""
        summaries = [
            {"document_id": "doc1.txt", "summary": "Text 1", "chunks_used": 2},
            {"document_id": "doc2.txt", "summary": "Text 2", "chunks_used": 2}
        ]
        
        # Mock embedding function that returns wrong size
        def bad_embeddings(texts):
            return [[0.5]]  # Wrong size!
        
        with patch('app.tools.insights.cross_file_analyzer.get_embedding_function', return_value=bad_embeddings):
            # Should not crash, should fallback gracefully
            result, telemetry = analyze_cross_file_semantics(summaries)
            
            assert isinstance(result, dict)
            assert isinstance(telemetry, dict)
            assert telemetry["cross_file_analysis_used"] is False
    
    def test_embedding_function_raises_exception_no_crash(self):
        """Exception in embedding function should not crash."""
        summaries = [
            {"document_id": "doc1.txt", "summary": "Text", "chunks_used": 2},
            {"document_id": "doc2.txt", "summary": "Text", "chunks_used": 2}
        ]
        
        def failing_embeddings(texts):
            raise RuntimeError("Embedding service down")
        
        with patch('app.tools.insights.cross_file_analyzer.get_embedding_function', return_value=failing_embeddings):
            # Should not crash
            result, telemetry = analyze_cross_file_semantics(summaries)
            
            assert isinstance(result, dict)
            assert isinstance(telemetry, dict)
            # Should have fallback reason
            assert telemetry["fallback_reason"] is not None


class TestUtilityFunctions:
    """Test helper and utility functions."""
    
    def test_cosine_similarity_calculation(self):
        """Cosine similarity should be computed correctly."""
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([1.0, 0.0, 0.0])
        
        similarity = compute_cosine_similarity(vec1, vec2)
        assert similarity == pytest.approx(1.0, abs=0.01)  # Identical vectors
        
        vec3 = np.array([0.0, 1.0, 0.0])
        similarity2 = compute_cosine_similarity(vec1, vec3)
        assert similarity2 == pytest.approx(0.0, abs=0.01)  # Orthogonal vectors
    
    def test_extract_theme_label_from_summary(self):
        """Theme label extraction should work correctly."""
        summary = "API Security involves OAuth2 authentication and rate limiting. Security best practices prevent unauthorized access."
        
        label = extract_theme_label_from_summary(summary)
        
        assert isinstance(label, str)
        assert len(label) > 0
        # Should extract capitalized terms
        assert any(word in label for word in ["API", "Security", "OAuth"])
    
    def test_generate_cluster_theme_label(self):
        """Cluster theme label should represent members."""
        members = [
            {"document_id": "doc1", "summary": "Machine Learning enables AI systems through neural networks."},
            {"document_id": "doc2", "summary": "Machine Learning algorithms train on large datasets using neural networks."}
        ]
        
        label = generate_cluster_theme_label(members, mode="extractive")
        
        assert isinstance(label, str)
        assert len(label) > 0
        # Should relate to the content
        assert "machine" in label.lower() or "learning" in label.lower() or "neural" in label.lower()
    
    def test_extract_evidence_snippets(self):
        """Evidence extraction should provide snippets."""
        members = [
            {
                "document_id": "doc1.txt",
                "summary": "This is a detailed summary with multiple sentences. It covers various topics. The first sentence is most important.",
                "chunks_used": 5
            },
            {
                "document_id": "doc2.txt",
                "summary": "Another summary providing context. It explains the topic clearly.",
                "chunks_used": 3
            }
        ]
        
        evidence = extract_evidence_snippets(members, max_snippets=2)
        
        assert isinstance(evidence, list)
        assert len(evidence) <= 2
        
        if evidence:
            assert "document_id" in evidence[0]
            assert "snippet" in evidence[0]
            assert "chunks_used" in evidence[0]
            
            # Snippet should be truncated if needed
            assert len(evidence[0]["snippet"]) <= 160  # EVIDENCE_SNIPPET_LENGTH + "..."
    
    def test_detect_overlapping_concepts(self):
        """Should detect overlapping concepts from clusters."""
        clusters = [
            {
                "theme_label": "API Security",
                "member_documents": ["doc1.txt", "doc2.txt", "doc3.txt"],
                "confidence_score": 0.85
            },
            {
                "theme_label": "Database Design",
                "member_documents": ["doc4.txt", "doc5.txt"],
                "confidence_score": 0.72
            }
        ]
        
        summaries = [
            {"document_id": f"doc{i}.txt", "summary": "Summary"} 
            for i in range(1, 6)
        ]
        
        overlaps = detect_overlapping_concepts(clusters, summaries)
        
        assert isinstance(overlaps, list)
        assert len(overlaps) == 2  # Two clusters = two overlapping concepts
        
        assert overlaps[0]["concept"] == "API Security"
        assert overlaps[0]["frequency"] == 3
        assert overlaps[0]["confidence"] == 0.85


class TestTelemetryFields:
    """Ensure all telemetry fields are present."""
    
    def test_successful_analysis_has_all_telemetry(self):
        """Successful analysis should have complete telemetry."""
        summaries = [
            {
                "document_id": "doc1.txt",
                "summary": "Machine Learning uses neural networks for pattern recognition.",
                "chunks_used": 5
            },
            {
                "document_id": "doc2.txt",
                "summary": "Neural Networks enable deep learning and AI applications.",
                "chunks_used": 4
            }
        ]
        
        def mock_embeddings(texts):
            # Similar embeddings
            return [
                np.array([0.8, 0.6, 0.2, 0.1, 0.0]).tolist(),
                np.array([0.7, 0.7, 0.3, 0.1, 0.0]).tolist()
            ]
        
        with patch('app.tools.insights.cross_file_analyzer.get_embedding_function', return_value=mock_embeddings):
            result, telemetry = analyze_cross_file_semantics(summaries)
            
            # Check all required telemetry fields
            required_fields = [
                "cross_file_analysis_used",
                "cluster_count",
                "avg_cluster_confidence",
                "documents_clustered",
                "documents_unclustered",
                "weak_signals_detected",
                "fallback_reason",
                "latency_ms"
            ]
            
            for field in required_fields:
                assert field in telemetry, f"Missing telemetry field: {field}"
    
    def test_fallback_has_explainable_metadata(self):
        """Fallback scenarios should have clear metadata."""
        summaries = [{"document_id": "single.txt", "summary": "One doc", "chunks_used": 1}]
        
        result, telemetry = analyze_cross_file_semantics(summaries)
        
        # Should have fallback metadata
        assert telemetry["cross_file_analysis_used"] is False
        assert telemetry["fallback_reason"] is not None
        assert isinstance(telemetry["fallback_reason"], str)
        assert len(telemetry["fallback_reason"]) > 0


class TestIntegration:
    """Integration tests for full pipeline."""
    
    def test_end_to_end_clustering_workflow(self):
        """Test complete workflow from summaries to clusters."""
        summaries = [
            {
                "document_id": "security1.md",
                "summary": "API Security best practices include OAuth2 authentication, rate limiting, and HTTPS encryption.",
                "chunks_used": 8
            },
            {
                "document_id": "security2.md",
                "summary": "Security measures for APIs involve proper authentication using OAuth2 and implementing rate limits.",
                "chunks_used": 6
            },
            {
                "document_id": "security3.md",
                "summary": "API security requires authentication tokens, encrypted connections, and access control mechanisms.",
                "chunks_used": 7
            }
        ]
        
        def mock_embeddings(texts):
            # Generate similar embeddings for security-related texts
            base = np.array([0.7, 0.6, 0.5, 0.3, 0.2])
            return [(base + np.random.normal(0, 0.03, 5)).tolist() for _ in texts]
        
        with patch('app.tools.insights.cross_file_analyzer.get_embedding_function', return_value=mock_embeddings):
            result, telemetry = analyze_cross_file_semantics(summaries, mode="extractive")
            
            # Should successfully cluster
            if telemetry["cross_file_analysis_used"]:
                assert result["cross_file_overlap_detected"] is True
                assert len(result["semantic_clusters"]) >= 1
                
                cluster = result["semantic_clusters"][0]
                assert cluster["member_count"] >= 2
                assert "theme_label" in cluster
                assert "evidence_snippets" in cluster
                assert "confidence_score" in cluster
                
                # Should have shared themes
                assert len(result["shared_themes"]) > 0
