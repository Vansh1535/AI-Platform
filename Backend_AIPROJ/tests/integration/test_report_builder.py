"""
Tests for Report Builder — Phase 3

Tests Markdown report generation for various insight types.
"""

import pytest
from datetime import datetime
from app.export.report_builder import (
    build_report,
    build_rag_answer_report,
    build_summary_report,
    build_csv_insights_report,
    build_aggregation_report,
    build_generic_report
)


class TestRAGAnswerReport:
    """Test RAG answer report generation."""
    
    def test_basic_rag_report(self):
        """Test basic RAG answer report."""
        payload = {
            "query": "What is machine learning?",
            "answer": "Machine learning is a subset of AI...",
            "citations": [
                {
                    "document_id": "doc1",
                    "relevance_score": 0.95,
                    "content": "Machine learning enables computers..."
                }
            ],
            "meta": {
                "latency_ms_total": 250,
                "confidence_score": 0.92,
                "routing_decision": "vector_search",
                "degradation_level": "none"
            }
        }
        
        report = build_rag_answer_report(payload)
        
        assert "# RAG Answer Report" in report
        assert "What is machine learning?" in report
        assert "Machine learning is a subset of AI" in report
        assert "## Evidence & Citations" in report
        assert "doc1" in report
        assert "0.95" in report
    
    def test_rag_report_with_degradation(self):
        """Test RAG report with degradation."""
        payload = {
            "query": "Test query",
            "answer": "Fallback answer",
            "citations": [],
            "meta": {
                "latency_ms_total": 100,
                "confidence_score": 0.65,
                "routing_decision": "keyword_fallback",
                "degradation_level": "fallback",
                "graceful_message": "Embedding service unavailable"
            }
        }
        
        report = build_rag_answer_report(payload)
        
        assert "fallback" in report.lower()
        assert "Embedding service unavailable" in report
    
    def test_rag_report_multiple_citations(self):
        """Test RAG report with multiple citations."""
        payload = {
            "query": "Test",
            "answer": "Answer",
            "citations": [
                {"document_id": "doc1", "relevance_score": 0.95, "content": "Content 1"},
                {"document_id": "doc2", "relevance_score": 0.88, "content": "Content 2"},
                {"document_id": "doc3", "relevance_score": 0.75, "content": "Content 3"}
            ],
            "meta": {"latency_ms_total": 200}
        }
        
        report = build_rag_answer_report(payload)
        
        assert "doc1" in report
        assert "doc2" in report
        assert "doc3" in report
        assert "0.95" in report
        assert "0.88" in report
    
    def test_rag_report_truncates_long_content(self):
        """Test that long citation content is truncated."""
        long_content = "A" * 500  # Very long content
        
        payload = {
            "query": "Test",
            "answer": "Answer",
            "citations": [
                {"document_id": "doc1", "relevance_score": 0.95, "content": long_content}
            ],
            "meta": {"latency_ms_total": 100}
        }
        
        report = build_rag_answer_report(payload)
        
        # Should be truncated with ellipsis
        assert "..." in report
        # Full content should not be present
        assert long_content not in report


class TestSummaryReport:
    """Test summary report generation."""
    
    def test_basic_summary_report(self):
        """Test basic summary report."""
        payload = {
            "document_id": "doc123",
            "summary": "This document discusses machine learning concepts...",
            "mode": "hybrid",
            "meta": {
                "chunks_used": 5,
                "latency_ms_total": 500,
                "confidence_score": 0.88,
                "degradation_level": "none"
            }
        }
        
        report = build_summary_report(payload)
        
        assert "# Document Summary Report" in report
        assert "doc123" in report
        assert "hybrid" in report
        assert "This document discusses" in report
        assert "5" in report  # chunks_used
    
    def test_summary_report_extractive_mode(self):
        """Test summary with extractive mode."""
        payload = {
            "document_id": "doc456",
            "summary": "Extractive summary...",
            "mode": "extractive",
            "meta": {
                "chunks_used": 3,
                "latency_ms_total": 100,
                "degradation_level": "fallback",
                "graceful_message": "LLM unavailable, used extractive fallback"
            }
        }
        
        report = build_summary_report(payload)
        
        assert "extractive" in report
        assert "LLM unavailable" in report
    
    def test_summary_report_with_confidence(self):
        """Test summary report includes confidence score."""
        payload = {
            "document_id": "doc789",
            "summary": "Summary text",
            "mode": "abstraction",
            "meta": {
                "confidence_score": 0.95,
                "latency_ms_total": 600
            }
        }
        
        report = build_summary_report(payload)
        
        assert "0.95" in report


class TestCSVInsightsReport:
    """Test CSV insights report generation."""
    
    def test_basic_csv_insights_report(self):
        """Test basic CSV insights without LLM."""
        payload = {
            "dataset_name": "sales_data.csv",
            "insights": {
                "row_count": 1000,
                "column_count": 10,
                "numeric_columns": 6,
                "categorical_columns": 4,
                "column_profiles": {
                    "revenue": {
                        "type": "numeric",
                        "mean": 5000.50,
                        "median": 4800.00,
                        "std": 1200.00,
                        "min": 1000.00,
                        "max": 15000.00
                    },
                    "category": {
                        "type": "categorical",
                        "unique_values": 5,
                        "top_values": {"Electronics": 300, "Clothing": 250}
                    }
                },
                "data_quality": {
                    "null_ratio": 0.02,
                    "duplicate_ratio": 0.01,
                    "quality_flags": ["minor_nulls", "no_duplicates"]
                }
            },
            "meta": {
                "latency_ms_total": 150,
                "degradation_level": "none"
            }
        }
        
        report = build_csv_insights_report(payload)
        
        assert "# CSV Insights Report" in report
        assert "sales_data.csv" in report
        assert "1000" in report  # row_count (formatted as 1,000)
        assert "10" in report  # column_count
        assert "revenue" in report
        assert "5000.5" in report  # mean (Python removes trailing zero)
        assert "## Data Quality Assessment" in report
    
    def test_csv_insights_with_llm_insights(self):
        """Test CSV insights with LLM-generated narrative."""
        payload = {
            "dataset_name": "customer_data.csv",
            "insights": {
                "row_count": 500,
                "column_count": 8,
                "llm_insights": {
                    "dataset_explanation": "This dataset contains customer information...",
                    "key_patterns": ["High correlation between age and spending", "Seasonal trends visible"],
                    "relationships": ["Age vs Revenue shows positive correlation"],
                    "outliers_and_risks": ["3 outliers detected in revenue column"],
                    "data_quality_commentary": "Generally clean data with minor nulls"
                },
                "column_profiles": {},
                "data_quality": {
                    "null_ratio": 0.01,
                    "duplicate_ratio": 0.0,
                    "quality_flags": []
                }
            },
            "meta": {
                "latency_ms_total": 800,
                "latency_ms_llm": 600,
                "degradation_level": "none"
            }
        }
        
        report = build_csv_insights_report(payload)
        
        assert "## AI-Powered Insights" in report
        assert "This dataset contains customer information" in report
        assert "High correlation between age and spending" in report
        assert "Seasonal trends visible" in report
        assert "⚠️" in report  # Outliers section
    
    def test_csv_insights_without_llm(self):
        """Test CSV insights falls back gracefully without LLM."""
        payload = {
            "dataset_name": "test.csv",
            "insights": {
                "row_count": 100,
                "column_count": 5,
                "column_profiles": {},
                "data_quality": {
                    "null_ratio": 0.0,
                    "duplicate_ratio": 0.0,
                    "quality_flags": []
                }
            },
            "meta": {
                "latency_ms_total": 50,
                "degradation_level": "none"
            }
        }
        
        report = build_csv_insights_report(payload)
        
        # Should not have AI section if no LLM insights
        assert "## Statistical Analysis" in report
        assert "100" in report
    
    def test_csv_insights_with_quality_issues(self):
        """Test CSV insights with data quality issues."""
        payload = {
            "dataset_name": "dirty_data.csv",
            "insights": {
                "row_count": 200,
                "column_count": 6,
                "column_profiles": {},
                "data_quality": {
                    "null_ratio": 0.15,
                    "duplicate_ratio": 0.08,
                    "quality_flags": ["high_nulls", "duplicates_detected"]
                }
            },
            "meta": {
                "latency_ms_total": 100,
                "degradation_level": "mild",
                "graceful_message": "Data quality issues detected"
            }
        }
        
        report = build_csv_insights_report(payload)
        
        assert "15.0%" in report  # null_ratio formatted as percentage
        assert "8.0%" in report  # duplicate_ratio formatted as percentage
        assert "high_nulls" in report
        assert "Data quality issues detected" in report


class TestAggregationReport:
    """Test aggregation report generation."""
    
    def test_basic_aggregation_report(self):
        """Test basic aggregation report."""
        payload = {
            "aggregated_insights": {
                "themes": ["Data security", "Machine learning algorithms"],
                "key_findings": ["Finding 1", "Finding 2"],
                "summary": "Overall analysis shows..."
            },
            "document_summaries": [
                {"document_id": "doc1", "summary": "Summary 1"},
                {"document_id": "doc2", "summary": "Summary 2"}
            ],
            "meta": {
                "latency_ms_total": 1500,
                "files_processed": 2,
                "files_failed": 0,
                "degradation_level": "none"
            }
        }
        
        report = build_aggregation_report(payload)
        
        assert "# Cross-File Insights Report" in report
        assert "Data security" in report
        assert "Machine learning algorithms" in report
        assert "Summary 1" in report
        assert "doc1" in report
    
    def test_aggregation_with_failed_documents(self):
        """Test aggregation report with failed documents."""
        payload = {
            "aggregated_insights": {
                "themes": ["Theme 1"],
                "key_findings": ["Finding 1"],
                "summary": "Partial analysis"
            },
            "document_summaries": [
                {"document_id": "doc1", "summary": "Success"}
            ],
            "failed_documents": [
                {"document_id": "doc2", "error": "Parsing failed"},
                {"document_id": "doc3", "error": "Timeout"}
            ],
            "meta": {
                "latency_ms_total": 2000,
                "files_processed": 1,
                "files_failed": 2,
                "degradation_level": "mild"
            }
        }
        
        report = build_aggregation_report(payload)
        
        assert "## Failed Documents" in report
        assert "⚠️" in report
        assert "doc2" in report
        assert "doc3" in report
        assert "Parsing failed" in report
    
    def test_aggregation_all_successful(self):
        """Test aggregation with all documents successful."""
        payload = {
            "aggregated_insights": {
                "themes": ["Theme"],
                "key_findings": ["Finding"],
                "summary": "Complete analysis"
            },
            "document_summaries": [
                {"document_id": "doc1", "summary": "Sum1"},
                {"document_id": "doc2", "summary": "Sum2"},
                {"document_id": "doc3", "summary": "Sum3"}
            ],
            "failed_documents": [],
            "meta": {
                "latency_ms_total": 3000,
                "files_processed": 3,
                "files_failed": 0,
                "degradation_level": "none"
            }
        }
        
        report = build_aggregation_report(payload)
        
        # Should not have failed documents section
        assert report.count("## Failed Documents") == 0 or "No failed documents" in report.lower()
        assert "3" in report  # files_processed


class TestGenericReport:
    """Test generic fallback report generation."""
    
    def test_generic_report_basic(self):
        """Test generic report generation."""
        payload = {
            "data": "Some data",
            "result": "Some result",
            "meta": {"latency_ms_total": 100}
        }
        
        report = build_generic_report(payload, "Custom Report")
        
        assert "# Custom Report" in report
        assert "Some data" in report
        assert "Some result" in report
    
    def test_generic_report_handles_nested_data(self):
        """Test generic report handles nested structures."""
        payload = {
            "nested": {
                "level1": {
                    "level2": "deep value"
                }
            },
            "meta": {}
        }
        
        report = build_generic_report(payload)
        
        assert "Generic Report" in report
        assert "Nested" in report  # Key is capitalized in report


class TestBuildReportRouter:
    """Test the build_report router function."""
    
    def test_router_dispatches_rag(self):
        """Test router dispatches to RAG builder."""
        payload = {
            "query": "Test",
            "answer": "Answer",
            "citations": [],
            "meta": {}
        }
        
        report = build_report("rag", payload)
        
        assert "RAG Answer Report" in report
    
    def test_router_dispatches_summary(self):
        """Test router dispatches to summary builder."""
        payload = {
            "document_id": "doc1",
            "summary": "Summary",
            "mode": "hybrid",
            "meta": {}
        }
        
        report = build_report("summary", payload)
        
        assert "Document Summary Report" in report
    
    def test_router_dispatches_csv_insights(self):
        """Test router dispatches to CSV insights builder."""
        payload = {
            "dataset_name": "data.csv",
            "insights": {
                "row_count": 100,
                "column_count": 5,
                "column_profiles": {},
                "data_quality": {}
            },
            "meta": {}
        }
        
        report = build_report("csv_insights", payload)
        
        assert "CSV Insights Report" in report
    
    def test_router_dispatches_aggregation(self):
        """Test router dispatches to aggregation builder."""
        payload = {
            "aggregated_insights": {
                "themes": [],
                "key_findings": [],
                "summary": ""
            },
            "document_summaries": [],
            "meta": {}
        }
        
        report = build_report("aggregation", payload)
        
        assert "Cross-File Insights Report" in report
    
    def test_router_handles_unknown_source(self):
        """Test router handles unknown source types."""
        payload = {"data": "test", "meta": {}}
        
        report = build_report("unknown_type", payload)
        
        assert "Generic Report" in report


class TestReportFormatting:
    """Test report formatting quality."""
    
    def test_reports_have_proper_markdown_headings(self):
        """Test that reports use proper Markdown headings."""
        payloads = [
            ("rag", {
                "query": "Q", "answer": "A", "citations": [], "meta": {}
            }),
            ("summary", {
                "document_id": "d", "summary": "S", "mode": "h", "meta": {}
            })
        ]
        
        for source, payload in payloads:
            report = build_report(source, payload)
            # Should have # for main heading
            assert report.startswith("#")
            # Should have ## for subsections
            assert "##" in report
    
    def test_reports_include_timestamps(self):
        """Test that reports include generation timestamps."""
        payload = {
            "query": "Test",
            "answer": "Answer",
            "citations": [],
            "meta": {}
        }
        
        report = build_rag_answer_report(payload)
        
        assert "**Generated**:" in report
    
    def test_reports_have_metadata_sections(self):
        """Test that reports include metadata sections."""
        payload = {
            "dataset_name": "test.csv",
            "insights": {
                "row_count": 100,
                "column_count": 5,
                "column_profiles": {},
                "data_quality": {}
            },
            "meta": {
                "latency_ms_total": 150,
                "degradation_level": "none"
            }
        }
        
        report = build_csv_insights_report(payload)
        
        # We renamed "Processing Metadata" to "Observability Snapshot"
        assert "## Observability Snapshot" in report
        assert "150" in report  # latency


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_citations_handled_gracefully(self):
        """Test RAG report with empty citations."""
        payload = {
            "query": "Q",
            "answer": "A",
            "citations": [],
            "meta": {}
        }
        
        report = build_rag_answer_report(payload)
        
        assert "RAG Answer Report" in report
        # Should still have citations section
        assert "Evidence & Citations" in report or "No citations" in report.lower()
    
    def test_missing_metadata_handled_gracefully(self):
        """Test report generation with missing metadata."""
        payload = {
            "query": "Q",
            "answer": "A",
            "citations": []
            # No meta field
        }
        
        # Should not crash
        report = build_rag_answer_report(payload)
        
        assert "RAG Answer Report" in report
    
    def test_none_values_handled_gracefully(self):
        """Test report handles None values."""
        payload = {
            "query": "Q",
            "answer": None,
            "citations": None,
            "meta": {}
        }
        
        # Should not crash
        report = build_rag_answer_report(payload)
        
        assert "RAG Answer Report" in report
