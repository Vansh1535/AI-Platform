"""
Export Package — Phase 3

Provides report generation and export capabilities in multiple formats.
"""

from app.export.report_builder import (
    build_report,
    build_rag_answer_report,
    build_summary_report,
    build_csv_insights_report,
    build_aggregation_report
)

from app.export.pdf_adapter import (
    markdown_to_pdf,
    is_pdf_available,
    get_pdf_capabilities,
    cleanup_temp_pdf
)

__all__ = [
    "build_report",
    "build_rag_answer_report",
    "build_summary_report",
    "build_csv_insights_report",
    "build_aggregation_report",
    "markdown_to_pdf",
    "is_pdf_available",
    "get_pdf_capabilities",
    "cleanup_temp_pdf"
]
