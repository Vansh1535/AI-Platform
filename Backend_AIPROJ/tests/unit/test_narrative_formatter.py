"""
Tests for Narrative Formatter — Unified narrative insight format.

Validates:
- Narrative insight creation and formatting
- Merging multiple insights
- Validation logic
- Legacy format conversion
"""

import pytest
from app.core.insights.narrative_formatter import (
    format_narrative_insight,
    merge_narrative_insights,
    validate_narrative_insight,
    convert_to_narrative_insight,
    NarrativeInsight
)


class TestNarrativeInsightCreation:
    """Test creating narrative insights."""
    
    def test_format_narrative_insight_minimal(self):
        """Create narrative insight with minimal required fields."""
        insight = format_narrative_insight(
            theme="Performance Improvement",
            evidence=["Latency reduced by 40%"],
            source_documents=["doc_123"]
        )
        
        assert insight["theme"] == "Performance Improvement"
        assert len(insight["evidence"]) == 1
        assert len(insight["source_documents"]) == 1
        assert insight["mode"] == "deterministic"
        assert 0.0 <= insight["confidence"] <= 1.0
        assert "narrative_text" in insight
    
    def test_format_narrative_insight_with_all_fields(self):
        """Create narrative insight with all fields."""
        insight = format_narrative_insight(
            theme="Data Quality Issues",
            evidence=["Missing values in 30% of rows", "Duplicate records detected"],
            source_documents=["dataset_456"],
            confidence=0.85,
            narrative_text="Dataset quality analysis reveals significant issues",
            mode="llm_hybrid",
            related_themes=["Data Cleaning", "ETL Pipeline"],
            metadata={"analyst": "agent_1"}
        )
        
        assert insight["theme"] == "Data Quality Issues"
        assert len(insight["evidence"]) == 2
        assert insight["confidence"] == 0.85
        assert insight["mode"] == "llm_hybrid"
        assert insight["related_themes"] == ["Data Cleaning", "ETL Pipeline"]
        assert insight["metadata"]["analyst"] == "agent_1"
    
    def test_auto_generated_narrative_text(self):
        """Narrative text auto-generated if not provided."""
        insight = format_narrative_insight(
            theme="Test Theme",
            evidence=["Evidence 1", "Evidence 2"],
            source_documents=["doc_1", "doc_2"]
        )
        
        # Should auto-generate narrative
        assert "narrative_text" in insight
        assert len(insight["narrative_text"]) > 0
        assert "Test Theme" in insight["narrative_text"]
    
    def test_confidence_clamped_to_range(self):
        """Confidence should be clamped to [0, 1]."""
        insight1 = format_narrative_insight(
            theme="Test",
            evidence=["E1"],
            source_documents=["D1"],
            confidence=1.5  # > 1
        )
        assert insight1["confidence"] == 1.0
        
        insight2 = format_narrative_insight(
            theme="Test",
            evidence=["E1"],
            source_documents=["D1"],
            confidence=-0.5  # < 0
        )
        assert insight2["confidence"] == 0.0


class TestNarrativeInsightMerging:
    """Test merging multiple narrative insights."""
    
    def test_merge_empty_list(self):
        """Merging empty list returns default insight."""
        merged = merge_narrative_insights([])
        
        assert merged["theme"] == "No insights"
        assert len(merged["evidence"]) == 0
        assert merged["mode"] == "deterministic"
    
    def test_merge_single_insight(self):
        """Merging single insight returns it unchanged."""
        insight = format_narrative_insight(
            theme="Single Theme",
            evidence=["E1"],
            source_documents=["D1"]
        )
        
        merged = merge_narrative_insights([insight])
        assert merged["theme"] == "Single Theme"
    
    def test_merge_union_strategy(self):
        """Union strategy combines all evidence."""
        insight1 = format_narrative_insight(
            theme="Theme 1",
            evidence=["E1", "E2"],
            source_documents=["D1"],
            confidence=0.8
        )
        insight2 = format_narrative_insight(
            theme="Theme 2",
            evidence=["E3"],
            source_documents=["D2"],
            confidence=0.6
        )
        
        merged = merge_narrative_insights([insight1, insight2], merge_strategy="union")
        
        # Should combine evidence (deduplicated)
        assert len(merged["evidence"]) == 3
        assert len(merged["source_documents"]) == 2
        
        # Confidence should be averaged
        assert merged["confidence"] == pytest.approx(0.7, abs=0.01)
    
    def test_merge_highest_confidence_strategy(self):
        """Highest confidence strategy returns best insight."""
        insight1 = format_narrative_insight(
            theme="Low Confidence",
            evidence=["E1"],
            source_documents=["D1"],
            confidence=0.3
        )
        insight2 = format_narrative_insight(
            theme="High Confidence",
            evidence=["E2"],
            source_documents=["D2"],
            confidence=0.9
        )
        
        merged = merge_narrative_insights(
            [insight1, insight2],
            merge_strategy="highest_confidence"
        )
        
        assert merged["theme"] == "High Confidence"
        assert merged["confidence"] == 0.9
    
    def test_merge_mode_propagation(self):
        """LLM hybrid mode propagates if any insight used LLM."""
        insight1 = format_narrative_insight(
            theme="T1",
            evidence=["E1"],
            source_documents=["D1"],
            mode="deterministic"
        )
        insight2 = format_narrative_insight(
            theme="T2",
            evidence=["E2"],
            source_documents=["D2"],
            mode="llm_hybrid"
        )
        
        merged = merge_narrative_insights([insight1, insight2])
        
        # Should be llm_hybrid if any insight used LLM
        assert merged["mode"] == "llm_hybrid"


class TestNarrativeInsightValidation:
    """Test validation of narrative insights."""
    
    def test_validate_complete_insight(self):
        """Valid insight passes validation."""
        insight = format_narrative_insight(
            theme="Valid Theme",
            evidence=["E1"],
            source_documents=["D1"]
        )
        
        assert validate_narrative_insight(insight) is True
    
    def test_validate_missing_required_field(self):
        """Missing required field fails validation."""
        incomplete = {
            "theme": "Test",
            "evidence": ["E1"]
            # Missing source_documents, confidence, narrative_text, mode
        }
        
        assert validate_narrative_insight(incomplete) is False
    
    def test_validate_invalid_confidence(self):
        """Invalid confidence range fails validation."""
        invalid = format_narrative_insight(
            theme="Test",
            evidence=["E1"],
            source_documents=["D1"]
        )
        invalid["confidence"] = 1.5  # Out of range
        
        assert validate_narrative_insight(invalid) is False
    
    def test_validate_invalid_mode(self):
        """Invalid mode value fails validation."""
        invalid = format_narrative_insight(
            theme="Test",
            evidence=["E1"],
            source_documents=["D1"]
        )
        invalid["mode"] = "invalid_mode"
        
        assert validate_narrative_insight(invalid) is False


class TestLegacyFormatConversion:
    """Test conversion from legacy insight formats."""
    
    def test_convert_csv_insight(self):
        """Convert CSV insight to narrative format."""
        csv_insight = {
            "key_pattern": "High Correlation",
            "patterns": ["X and Y correlated at 0.85"],
            "dataset": "sales_data.csv",
            "explanation": "Strong positive correlation detected"
        }
        
        narrative = convert_to_narrative_insight(csv_insight, source_type="csv")
        
        assert narrative["theme"] == "High Correlation"
        assert len(narrative["evidence"]) >= 1
        assert "sales_data.csv" in narrative["source_documents"]
        assert narrative["mode"] == "deterministic"
        assert validate_narrative_insight(narrative)
    
    def test_convert_rag_insight(self):
        """Convert RAG answer to narrative format."""
        rag_insight = {
            "answer": "Machine learning is a subset of AI that enables systems to learn from data",
            "citations": [
                {"document_id": "doc_1", "content": "ML learns from data"},
                {"document_id": "doc_2", "content": "AI subset"}
            ],
            "confidence": 0.9,
            "used_llm": True
        }
        
        narrative = convert_to_narrative_insight(rag_insight, source_type="rag")
        
        assert "Machine learning" in narrative["theme"]
        assert len(narrative["evidence"]) == 2
        assert len(narrative["source_documents"]) == 2
        assert narrative["confidence"] == 0.9
        assert narrative["mode"] == "llm_hybrid"  # Because used_llm=True
        assert validate_narrative_insight(narrative)
    
    def test_convert_summary_insight(self):
        """Convert summary to narrative format."""
        summary_insight = {
            "document_id": "doc_123",
            "summary": "This document discusses project architecture and design patterns",
            "confidence": 0.75,
            "mode_used": "hybrid"
        }
        
        narrative = convert_to_narrative_insight(summary_insight, source_type="summary")
        
        assert "doc_123" in narrative["theme"]
        assert len(narrative["evidence"]) >= 1
        assert "doc_123" in narrative["source_documents"]
        assert narrative["confidence"] == 0.75
        assert narrative["mode"] == "llm_hybrid"
        assert validate_narrative_insight(narrative)
    
    def test_convert_aggregation_insight(self):
        """Convert aggregation insight to narrative format."""
        agg_insight = {
            "theme": "Common Security Patterns",
            "evidence": ["OAuth implementation", "JWT tokens"],
            "overlaps": ["Authentication", "Authorization"],
            "documents": ["doc_1", "doc_2", "doc_3"],
            "confidence": 0.82,
            "synthesis_used": False
        }
        
        narrative = convert_to_narrative_insight(agg_insight, source_type="aggregation")
        
        assert narrative["theme"] == "Common Security Patterns"
        assert len(narrative["evidence"]) >= 2
        assert len(narrative["source_documents"]) == 3
        assert narrative["mode"] == "deterministic"  # synthesis_used=False
        assert validate_narrative_insight(narrative)


class TestDataclassInterface:
    """Test NarrativeInsight dataclass interface."""
    
    def test_dataclass_to_dict(self):
        """Dataclass converts to dict correctly."""
        insight = NarrativeInsight(
            theme="Test",
            evidence=["E1"],
            source_documents=["D1"],
            confidence=0.5,
            narrative_text="Test narrative",
            mode="deterministic"
        )
        
        as_dict = insight.to_dict()
        
        assert isinstance(as_dict, dict)
        assert as_dict["theme"] == "Test"
        assert as_dict["mode"] == "deterministic"
    
    def test_dataclass_from_dict(self):
        """Dataclass creates from dict correctly."""
        data = {
            "theme": "Test",
            "evidence": ["E1"],
            "source_documents": ["D1"],
            "confidence": 0.6,
            "narrative_text": "Test",
            "mode": "deterministic",
            "related_themes": ["T1"],
            "metadata": {"key": "value"}
        }
        
        insight = NarrativeInsight.from_dict(data)
        
        assert isinstance(insight, NarrativeInsight)
        assert insight.theme == "Test"
        assert insight.related_themes == ["T1"]
        assert insight.metadata == {"key": "value"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
