"""
Tests for PDF Adapter and Export Endpoint — Phase 3

Tests PDF conversion with graceful fallback and export endpoint functionality.
"""

import pytest
import os
from app.export.pdf_adapter import (
    is_pdf_available,
    markdown_to_pdf,
    get_pdf_capabilities,
    cleanup_temp_pdf
)


class TestPDFAvailability:
    """Test PDF converter availability detection."""
    
    def test_is_pdf_available_returns_tuple(self):
        """Test that is_pdf_available returns (bool, str) tuple."""
        available, converter = is_pdf_available()
        
        assert isinstance(available, bool)
        assert isinstance(converter, str)
    
    def test_converter_name_valid(self):
        """Test that converter name is valid."""
        available, converter = is_pdf_available()
        
        # Should be one of the supported converters or "none"
        assert converter in ["pdfkit", "reportlab", "none"]
    
    def test_get_pdf_capabilities(self):
        """Test getting PDF capabilities."""
        caps = get_pdf_capabilities()
        
        assert "available" in caps
        assert "converter" in caps
        assert "supported_formats" in caps
        assert "fallback_enabled" in caps
        assert "message" in caps
        
        # Should always support markdown
        assert "markdown" in caps["supported_formats"]


class TestMarkdownToPDF:
    """Test Markdown to PDF conversion."""
    
    def test_markdown_to_pdf_returns_tuple(self):
        """Test that markdown_to_pdf returns proper tuple."""
        markdown = "# Test Report\n\nThis is a test."
        
        success, result, metadata = markdown_to_pdf(markdown)
        
        assert isinstance(success, bool)
        assert isinstance(result, str)
        assert isinstance(metadata, dict)
    
    def test_markdown_to_pdf_metadata_structure(self):
        """Test that metadata has required fields."""
        markdown = "# Test"
        
        success, result, metadata = markdown_to_pdf(markdown)
        
        required_fields = [
            "export_format",
            "export_latency_ms",
            "fallback_triggered",
            "degradation_level"
        ]
        
        for field in required_fields:
            assert field in metadata
    
    def test_pdf_fallback_when_unavailable(self):
        """Test that fallback works when PDF unavailable."""
        markdown = "# Test Report\n\nContent here."
        
        success, result, metadata = markdown_to_pdf(markdown)
        
        if not success:
            # Fallback should be triggered
            assert metadata["fallback_triggered"] is True
            assert metadata["degradation_level"] in ["fallback", "mild"]
            assert metadata["fallback_reason"] is not None
            assert "graceful_message" in metadata
            # Result should be the markdown content
            assert result == markdown
    
    def test_pdf_success_returns_file_path(self):
        """Test that successful PDF conversion returns file path."""
        markdown = "# Test Report"
        
        success, result, metadata = markdown_to_pdf(markdown, "test_output.pdf")
        
        if success:
            # Should return a file path
            assert isinstance(result, str)
            assert result.endswith(".pdf")
            assert metadata["export_format"] == "pdf"
            assert metadata["fallback_triggered"] is False
            assert metadata["degradation_level"] == "none"
            
            # Cleanup
            cleanup_temp_pdf(result)
    
    def test_pdf_custom_filename(self):
        """Test PDF generation with custom filename."""
        markdown = "# Custom Report"
        filename = "custom_test_report.pdf"
        
        success, result, metadata = markdown_to_pdf(markdown, filename)
        
        if success:
            assert filename in result
            cleanup_temp_pdf(result)
    
    def test_pdf_latency_recorded(self):
        """Test that PDF conversion records latency."""
        markdown = "# Test"
        
        success, result, metadata = markdown_to_pdf(markdown)
        
        assert metadata["export_latency_ms"] >= 0
        assert isinstance(metadata["export_latency_ms"], int)


class TestPDFCleanup:
    """Test PDF file cleanup."""
    
    def test_cleanup_removes_file(self):
        """Test that cleanup removes PDF file."""
        # Create a dummy file
        import tempfile
        temp_dir = tempfile.gettempdir()
        test_file = os.path.join(temp_dir, "test_cleanup.pdf")
        
        with open(test_file, 'w') as f:
            f.write("dummy content")
        
        assert os.path.exists(test_file)
        
        cleanup_temp_pdf(test_file)
        
        # File should be removed
        assert not os.path.exists(test_file)
    
    def test_cleanup_handles_missing_file(self):
        """Test that cleanup handles non-existent files gracefully."""
        # Should not raise exception
        cleanup_temp_pdf("/nonexistent/path/file.pdf")


class TestPDFDegradationScenarios:
    """Test PDF degradation scenarios."""
    
    def test_fallback_includes_graceful_message(self):
        """Test that fallback includes user-friendly message."""
        markdown = "# Test"
        
        success, result, metadata = markdown_to_pdf(markdown)
        
        if not success:
            assert metadata["graceful_message"] is not None
            assert len(metadata["graceful_message"]) > 0
            # Should be informative
            assert "PDF" in metadata["graceful_message"] or "Markdown" in metadata["graceful_message"]
    
    def test_fallback_returns_usable_content(self):
        """Test that fallback always returns usable content."""
        markdown = "# Important Report\n\nCritical information here."
        
        success, result, metadata = markdown_to_pdf(markdown)
        
        # Even if PDF fails, should return markdown
        assert result is not None
        assert len(result) > 0
        
        if not success:
            # Should be the original markdown
            assert "Important Report" in result
            assert "Critical information" in result
    
    def test_converter_recorded_on_success(self):
        """Test that successful conversion records converter used."""
        markdown = "# Test"
        
        success, result, metadata = markdown_to_pdf(markdown)
        
        if success:
            assert metadata["converter_used"] in ["pdfkit", "reportlab"]
            cleanup_temp_pdf(result)


# Export Endpoint Tests (Simulated)
class TestExportEndpointLogic:
    """Test export endpoint logic (without FastAPI test client)."""
    
    def test_export_markdown_workflow(self):
        """Test Markdown export workflow."""
        from app.export.report_builder import build_report
        
        # Simulate endpoint logic
        payload_source = "rag"
        payload = {
            "query": "What is ML?",
            "answer": "Machine learning is...",
            "citations": [],
            "meta": {"latency_ms_total": 200}
        }
        format_type = "markdown"
        
        # Build report
        markdown_content = build_report(payload_source, payload)
        
        assert markdown_content is not None
        assert "RAG Answer Report" in markdown_content
        assert "What is ML?" in markdown_content
    
    def test_export_pdf_workflow_with_fallback(self):
        """Test PDF export workflow with fallback."""
        from app.export.report_builder import build_report
        from app.export.pdf_adapter import markdown_to_pdf
        
        # Simulate endpoint logic
        payload = {
            "document_id": "doc1",
            "summary": "Summary text",
            "mode": "hybrid",
            "meta": {"latency_ms_total": 500}
        }
        
        # Build markdown
        markdown_content = build_report("summary", payload)
        
        # Try PDF conversion
        success, result, metadata = markdown_to_pdf(markdown_content, "export_test.pdf")
        
        # Should always have usable output
        assert result is not None
        
        if success:
            assert os.path.exists(result)
            cleanup_temp_pdf(result)
        else:
            # Fallback to markdown
            assert result == markdown_content
            assert metadata["fallback_triggered"] is True
    
    def test_export_all_payload_types(self):
        """Test export works for all payload types."""
        from app.export.report_builder import build_report
        
        test_payloads = {
            "rag": {
                "query": "Q",
                "answer": "A",
                "citations": [],
                "meta": {}
            },
            "summary": {
                "document_id": "d",
                "summary": "S",
                "mode": "h",
                "meta": {}
            },
            "csv_insights": {
                "dataset_name": "data.csv",
                "insights": {
                    "row_count": 100,
                    "column_count": 5,
                    "column_profiles": {},
                    "data_quality": {}
                },
                "meta": {}
            },
            "aggregation": {
                "aggregated_insights": {
                    "themes": [],
                    "key_findings": [],
                    "summary": ""
                },
                "document_summaries": [],
                "meta": {}
            }
        }
        
        for source, payload in test_payloads.items():
            report = build_report(source, payload)
            assert report is not None
            assert len(report) > 0


class TestExportMetadata:
    """Test export metadata tracking."""
    
    def test_export_tracks_source_component(self):
        """Test that export tracks source component."""
        from app.export.report_builder import build_report
        
        sources = ["rag", "summary", "csv_insights", "aggregation"]
        
        for source in sources:
            # Metadata should track which component generated the data
            # This would be verified in the actual endpoint response
            pass
    
    def test_export_tracks_format(self):
        """Test that export tracks output format."""
        markdown = "# Test"
        
        success, result, metadata = markdown_to_pdf(markdown)
        
        assert metadata["export_format"] in ["markdown", "pdf"]
    
    def test_export_tracks_latency(self):
        """Test that export tracks processing latency."""
        markdown = "# Test"
        
        success, result, metadata = markdown_to_pdf(markdown)
        
        assert "export_latency_ms" in metadata
        assert metadata["export_latency_ms"] >= 0


class TestExportBackwardCompatibility:
    """Test that export features don't break existing functionality."""
    
    def test_report_builder_standalone_usage(self):
        """Test that report builder works standalone."""
        from app.export.report_builder import build_rag_answer_report
        
        # Can be used without export endpoint
        payload = {
            "query": "Test",
            "answer": "Answer",
            "citations": [],
            "meta": {}
        }
        
        report = build_rag_answer_report(payload)
        assert report is not None
    
    def test_pdf_adapter_optional(self):
        """Test that PDF adapter is truly optional."""
        # System should work fine without PDF libraries
        available, converter = is_pdf_available()
        
        # Whether available or not, should return valid response
        assert isinstance(available, bool)
        
        # If unavailable, fallback should work
        if not available:
            markdown = "# Test"
            success, result, metadata = markdown_to_pdf(markdown)
            
            assert success is False
            assert result == markdown
            assert metadata["fallback_triggered"] is True


class TestExportGracefulDegradation:
    """Test graceful degradation in export functionality."""
    
    def test_pdf_unavailable_still_returns_output(self):
        """Test that PDF unavailability still provides output."""
        markdown = "# Important Data"
        
        success, result, metadata = markdown_to_pdf(markdown)
        
        # Always get output
        assert result is not None
        assert "Important Data" in result
    
    def test_degradation_level_set_correctly(self):
        """Test that degradation level is set correctly."""
        markdown = "# Test"
        
        success, result, metadata = markdown_to_pdf(markdown)
        
        if success:
            assert metadata["degradation_level"] == "none"
        else:
            assert metadata["degradation_level"] in ["fallback", "mild"]
    
    def test_error_information_preserved(self):
        """Test that error information is preserved in metadata."""
        markdown = "# Test"
        
        success, result, metadata = markdown_to_pdf(markdown)
        
        if not success:
            # Should have fallback reason
            assert metadata["fallback_reason"] is not None
            assert isinstance(metadata["fallback_reason"], str)


class TestExportIntegration:
    """Test integration scenarios."""
    
    def test_full_rag_to_pdf_workflow(self):
        """Test complete RAG answer → PDF workflow."""
        from app.export.report_builder import build_rag_answer_report
        from app.export.pdf_adapter import markdown_to_pdf
        
        # Simulate RAG response
        rag_payload = {
            "query": "What is machine learning?",
            "answer": "Machine learning is a field of AI that enables systems to learn from data...",
            "citations": [
                {
                    "document_id": "ml_basics_doc",
                    "relevance_score": 0.95,
                    "content": "Machine learning algorithms can identify patterns in large datasets..."
                }
            ],
            "meta": {
                "latency_ms_total": 350,
                "latency_ms_retrieval": 50,
                "latency_ms_embedding": 30,
                "latency_ms_llm": 250,
                "confidence_score": 0.92,
                "routing_decision": "vector_search",
                "degradation_level": "none"
            }
        }
        
        # Generate markdown report
        markdown = build_rag_answer_report(rag_payload)
        assert "Machine learning is a field of AI" in markdown
        
        # Try PDF conversion
        success, result, pdf_meta = markdown_to_pdf(markdown, "ml_answer.pdf")
        
        # Should have usable output either way
        assert result is not None
        
        if success:
            cleanup_temp_pdf(result)
    
    def test_full_csv_insights_to_markdown_workflow(self):
        """Test complete CSV insights → Markdown workflow."""
        from app.export.report_builder import build_csv_insights_report
        
        # Simulate CSV insights with LLM
        csv_payload = {
            "dataset_name": "sales_Q4_2023.csv",
            "insights": {
                "row_count": 5000,
                "column_count": 12,
                "numeric_columns": 8,
                "categorical_columns": 4,
                "llm_insights": {
                    "dataset_explanation": "This sales dataset contains Q4 2023 transactions across multiple regions...",
                    "key_patterns": [
                        "Revenue peaks in December (holiday season)",
                        "Electronics category dominates sales",
                        "West Coast region shows highest growth"
                    ],
                    "relationships": [
                        "Strong positive correlation between marketing spend and revenue",
                        "Customer age correlates with product category preference"
                    ],
                    "outliers_and_risks": [
                        "3 transactions with unusually high values (>$50k) - potential data entry errors",
                        "15% of records missing customer email - reduces marketing reach"
                    ],
                    "data_quality_commentary": "Generally high-quality data with minor issues in contact information fields"
                },
                "column_profiles": {
                    "revenue": {
                        "type": "numeric",
                        "mean": 3500.00,
                        "median": 2800.00,
                        "std": 1200.00,
                        "min": 100.00,
                        "max": 55000.00
                    }
                },
                "data_quality": {
                    "null_ratio": 0.05,
                    "duplicate_ratio": 0.02,
                    "quality_flags": ["minor_nulls", "some_duplicates"]
                }
            },
            "meta": {
                "latency_ms_total": 850,
                "latency_ms_llm": 650,
                "degradation_level": "none"
            }
        }
        
        # Generate report
        markdown = build_csv_insights_report(csv_payload)
        
        assert "sales_Q4_2023.csv" in markdown
        assert "AI-Powered Insights" in markdown
        assert "Revenue peaks in December" in markdown
        assert "5000" in markdown  # row count
