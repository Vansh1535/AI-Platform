"""
Polish Integration Tests — Verify final polish consistency.

Tests for:
1. Unified narrative format across exports
2. Export format toggle (md/pdf from same payload)
3. Enriched agent tool metadata
4. No breaking changes to existing behavior
"""

import pytest
from typing import Dict, Any
import pandas as pd
from app.reporting import (
    NarrativeReport,
    build_narrative_report,
    extract_narrative_report_from_payload,
    validate_narrative_report
)
from app.agents.tools import (
    doc_summarizer_tool,
    rag_answer_tool,
    csv_insights_tool,
    cross_file_insight_tool,
    AGENT_TOOLS
)
from app.api.export_routes import ExportRequest, ExportResponse


class TestUnifiedNarrativeFormat:
    """Test unified narrative format across exports."""
    
    def test_build_narrative_report_rag_type(self):
        """Test narrative report building for RAG answers."""
        telemetry = {
            "confidence_score": 0.85,
            "routing_decision": "rag",
            "fallback_triggered": False,
            "degradation_level": "none"
        }
        
        report = build_narrative_report(
            report_type="rag_answer",
            title="ML Question",
            summaries=["Machine learning is a subset of AI"],
            insights=[{
                "heading": "Definition",
                "content": "ML involves systems learning from data",
                "confidence": 0.9,
                "source": "doc_1"
            }],
            telemetry=telemetry
        )
        
        assert report.report_type == "rag_answer"
        assert report.title == "ML Question"
        assert len(report.insight_sections) == 1
        assert report.confidence_context["overall_confidence"] == 0.85
        assert report.confidence_context["routing_decision"] == "rag"
    
    def test_build_narrative_report_csv_type(self):
        """Test narrative report building for CSV insights."""
        telemetry = {
            "confidence_score": 0.75,
            "routing_decision": "csv_insights",
            "fallback_triggered": False,
            "degradation_level": "none"
        }
        
        report = build_narrative_report(
            report_type="csv_insights",
            title="Sales Analysis",
            summaries=["Data shows 15% growth quarter-over-quarter"],
            insights=[{
                "heading": "Key Finding",
                "content": "Regional sales peaked in Q3",
                "confidence": 0.8,
                "source": "sales_data.csv"
            }],
            telemetry=telemetry,
            graceful_message=None
        )
        
        assert report.report_type == "csv_insights"
        assert report.graceful_notes is None
        assert report.confidence_context["source_count"] == 1
        assert report.confidence_context["fallback_triggered"] is False
    
    def test_extract_narrative_from_rag_payload(self):
        """Test extracting narrative from RAG payload."""
        payload = {
            "query": "What is AI?",
            "answer": "AI is artificial intelligence",
            "citations": [
                {"text": "Citation 1", "source": "doc_1"},
                {"text": "Citation 2", "source": "doc_2"}
            ],
            "telemetry": {"confidence_score": 0.9}
        }
        
        report = extract_narrative_report_from_payload(
            payload,
            payload_type="rag"
        )
        
        assert report is not None
        assert report.report_type == "rag_answer"
        assert report.title == "What is AI?"
        # Should extract answer and citations as insights
        assert len(report.insight_sections) >= 1
    
    def test_extract_narrative_from_csv_payload(self):
        """Test extracting narrative from CSV insights payload."""
        payload = {
            "title": "Data Summary",
            "summary": "Dataset has 1000 rows",
            "insights": [
                {"heading": "Distribution", "content": "Normally distributed"},
                {"heading": "Outliers", "content": "5 outliers detected"}
            ],
            "telemetry": {"confidence_score": 0.8}
        }
        
        report = extract_narrative_report_from_payload(
            payload,
            payload_type="csv_insights"
        )
        
        assert report is not None
        assert report.report_type == "csv_insights"
        assert len(report.insight_sections) == 2
    
    def test_validate_narrative_report(self):
        """Test narrative report validation."""
        # Valid report
        report = build_narrative_report(
            report_type="rag_answer",
            title="Test",
            summaries=["Summary"],
            insights=[{"heading": "Finding", "content": "Content"}],
            telemetry={}
        )
        
        is_valid, error = validate_narrative_report(report)
        assert is_valid is True
        assert error is None
        
        # Invalid report (no summary)
        invalid_report = NarrativeReport(
            report_type="test",
            title="Test",
            summary_block="",  # Empty!
            insight_sections=[],
            confidence_context={}
        )
        
        is_valid, error = validate_narrative_report(invalid_report)
        assert is_valid is False
        assert "summary" in error.lower()
    
    def test_narrative_report_to_dict(self):
        """Test converting narrative report to dict."""
        report = build_narrative_report(
            report_type="rag_answer",
            title="Test",
            summaries=["Summary"],
            insights=[{"heading": "Finding", "content": "Content"}],
            telemetry={"test": "value"}
        )
        
        report_dict = report.to_dict()
        
        assert report_dict["report_type"] == "rag_answer"
        assert report_dict["title"] == "Test"
        assert report_dict["telemetry"]["test"] == "value"
        assert isinstance(report_dict["insight_sections"], list)


class TestExportFormatToggle:
    """Test export format toggle (md/pdf from same payload)."""
    
    def test_export_request_accepts_md_format(self):
        """Test ExportRequest accepts md format."""
        payload = {
            "query": "Test",
            "answer": "Test answer",
            "telemetry": {}
        }
        
        request = ExportRequest(
            payload_source="rag",
            payload=payload,
            format="md",
            filename="test"
        )
        
        assert request.format == "md"
        assert request.filename == "test"
    
    def test_export_request_accepts_pdf_format(self):
        """Test ExportRequest accepts pdf format."""
        payload = {
            "query": "Test",
            "answer": "Test answer",
            "telemetry": {}
        }
        
        request = ExportRequest(
            payload_source="rag",
            payload=payload,
            format="pdf",
            filename="test"
        )
        
        assert request.format == "pdf"
    
    def test_export_request_default_format_is_md(self):
        """Test ExportRequest defaults to md."""
        payload = {
            "query": "Test",
            "answer": "Test answer"
        }
        
        request = ExportRequest(
            payload_source="rag",
            payload=payload
        )
        
        assert request.format == "md"
    
    def test_export_response_includes_narrative_report(self):
        """Test ExportResponse includes narrative_report field."""
        response = ExportResponse(
            success=True,
            format="md",
            content="# Test\n\nContent",
            metadata={
                "export_version": "2.0.0",
                "generated_at": "2026-01-04T00:00:00Z"
            },
            narrative_report={
                "report_type": "rag_answer",
                "title": "Test",
                "summary_block": "Test summary",
                "insight_sections": [],
                "confidence_context": {}
            }
        )
        
        assert response.narrative_report is not None
        assert response.narrative_report["report_type"] == "rag_answer"


class TestEnrichedToolMetadata:
    """Test enriched agent tool metadata."""
    
    def test_csv_insights_tool_metadata(self):
        """Test CSV insights tool metadata includes export support."""
        metadata = csv_insights_tool.metadata
        
        assert metadata.name == "csv_insights"
        assert metadata.category == "data_analysis"
        assert metadata.supports_export is True
        assert metadata.requires_document is False
        assert metadata.supports_batch is False
        assert "narrative_insight" in str(metadata.output_schema)
    
    def test_rag_answer_tool_metadata(self):
        """Test RAG answer tool metadata is enriched."""
        metadata = rag_answer_tool.metadata
        
        assert metadata.name == "rag_answer"
        assert metadata.category == "question_answering"
        assert metadata.supports_export is True
        assert metadata.requires_document is False
        assert metadata.uses_llm is True
        assert len(metadata.examples) >= 2  # Multiple examples
    
    def test_doc_summarizer_tool_metadata(self):
        """Test document summarizer metadata is enriched."""
        metadata = doc_summarizer_tool.metadata
        
        assert metadata.name == "doc_summarizer"
        assert metadata.category == "document_processing"
        assert metadata.supports_export is True
        assert metadata.requires_document is True
        assert metadata.supports_batch is False
        assert len(metadata.examples) >= 3  # Multiple examples with modes
    
    def test_cross_file_tool_metadata(self):
        """Test cross-file tool metadata is enriched."""
        metadata = cross_file_insight_tool.metadata
        
        assert metadata.name == "cross_file_insight"
        assert metadata.category == "multi_document_analysis"
        assert metadata.supports_export is True
        assert metadata.requires_document is True
        assert metadata.supports_batch is True  # Batch of documents
        assert len(metadata.examples) >= 3
    
    def test_all_tools_have_required_metadata(self):
        """Test all tools have required metadata fields."""
        required_fields = [
            "name", "description", "inputs", "output_schema",
            "uses_llm", "category", "supports_export"
        ]
        
        for tool_name, tool in AGENT_TOOLS.items():
            metadata = tool.metadata
            for field in required_fields:
                assert hasattr(metadata, field), f"{tool_name} missing {field}"
                assert getattr(metadata, field) is not None, \
                    f"{tool_name}.{field} is None"
    
    def test_metadata_to_dict_includes_enriched_fields(self):
        """Test metadata.to_dict() includes enriched fields."""
        metadata = csv_insights_tool.metadata
        metadata_dict = metadata.to_dict()
        
        assert "supports_export" in metadata_dict
        assert "requires_document" in metadata_dict
        assert "supports_batch" in metadata_dict
        assert metadata_dict["supports_export"] is True
    
    def test_tool_discovery_can_filter_by_export(self):
        """Test tools can be filtered by export capability."""
        exportable_tools = [
            name for name, tool in AGENT_TOOLS.items()
            if tool.metadata.supports_export
        ]
        
        # All 4 tools should support export
        assert len(exportable_tools) == 4
        assert "csv_insights" in exportable_tools
        assert "rag_answer" in exportable_tools
        assert "doc_summarizer" in exportable_tools
        assert "cross_file_insight" in exportable_tools
    
    def test_tool_discovery_can_filter_by_document_requirement(self):
        """Test tools can be filtered by document requirement."""
        doc_required = [
            name for name, tool in AGENT_TOOLS.items()
            if tool.metadata.requires_document
        ]
        
        doc_not_required = [
            name for name, tool in AGENT_TOOLS.items()
            if not tool.metadata.requires_document
        ]
        
        # doc_summarizer and cross_file require documents
        assert "doc_summarizer" in doc_required
        assert "cross_file_insight" in doc_required
        
        # csv_insights and rag_answer don't require pre-existing documents
        assert "csv_insights" in doc_not_required
        assert "rag_answer" in doc_not_required


class TestNonBreakingChanges:
    """Test that polish changes don't break existing behavior."""
    
    def test_narrative_report_response_field_optional(self):
        """Test narrative_report field in ExportResponse is optional."""
        # Should work without narrative_report
        response = ExportResponse(
            success=True,
            format="md",
            content="# Test",
            metadata={"test": "value"}
        )
        
        assert response.narrative_report is None
        assert response.content == "# Test"
    
    def test_tool_metadata_backward_compatible(self):
        """Test enriched metadata doesn't break existing code."""
        metadata = csv_insights_tool.metadata
        
        # Old code should still work
        old_fields = {
            "name": metadata.name,
            "description": metadata.description,
            "inputs": metadata.inputs,
            "output_schema": metadata.output_schema,
            "uses_llm": metadata.uses_llm,
            "category": metadata.category
        }
        
        # All old fields present
        for field, value in old_fields.items():
            assert value is not None
    
    def test_export_request_supports_md_and_pdf_formats(self):
        """Test export request works with 'md' and 'pdf' formats."""
        payload = {"query": "Test", "answer": "Test"}
        
        # Both 'md' and 'pdf' should work
        request_md = ExportRequest(
            payload_source="rag",
            payload=payload,
            format="md"
        )
        assert request_md.format == "md"
        
        request_pdf = ExportRequest(
            payload_source="rag",
            payload=payload,
            format="pdf"
        )
        assert request_pdf.format == "pdf"


class TestPolishFeatureIntegration:
    """Test integration of polish features."""
    
    def test_narrative_builder_reuses_existing_content(self):
        """Test that narrative builder reuses content, doesn't invent."""
        original_summary = "The quick brown fox"
        original_insight = "Jumps over the lazy dog"
        
        report = build_narrative_report(
            report_type="rag_answer",
            title="Test",
            summaries=[original_summary],
            insights=[{
                "heading": "Finding",
                "content": original_insight
            }],
            telemetry={}
        )
        
        # Verify exact content reuse
        assert original_summary in report.summary_block
        assert original_insight in report.insight_sections[0]["content"]
    
    def test_export_routes_use_narrative_builder(self):
        """Test that export routes can use narrative builder."""
        from app.reporting import extract_narrative_report_from_payload
        
        payload = {
            "query": "Test?",
            "answer": "Test answer here",
            "citations": [],
            "telemetry": {"confidence_score": 0.8}
        }
        
        # This is how export_routes will use it
        report = extract_narrative_report_from_payload(
            payload,
            payload_type="rag"
        )
        
        assert report is not None
        assert report.report_type == "rag_answer"
    
    def test_tool_metadata_supports_ui_discovery(self):
        """Test metadata structure supports UI discovery features."""
        from app.agents.tools import AGENT_TOOLS
        
        # Should be able to build a tool picker UI
        tool_picker = []
        for name, tool in AGENT_TOOLS.items():
            meta = tool.metadata
            tool_picker.append({
                "id": meta.name,
                "label": meta.name.replace("_", " ").title(),
                "category": meta.category,
                "description": meta.description[:100],  # Truncate for UI
                "supports_export": meta.supports_export,
                "requires_document": meta.requires_document,
                "example_count": len(meta.examples or [])
            })
        
        # Should have 4 tools
        assert len(tool_picker) == 4
        
        # Each should have required UI fields
        for tool in tool_picker:
            assert "id" in tool
            assert "label" in tool
            assert "category" in tool
            assert tool["example_count"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
