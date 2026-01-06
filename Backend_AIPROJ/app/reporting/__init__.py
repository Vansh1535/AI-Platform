"""
Reporting Module — Unified narrative format and export builders.

Consolidates narrative report generation and export formatting across:
- RAG Answers
- Document Summaries
- CSV Insights
- Cross-File Aggregation

Key exports:
- NarrativeReport: Standardized report dataclass
- build_narrative_report(): Create unified reports
- merge_narrative_reports(): Combine multiple reports
- extract_narrative_report_from_payload(): Bridge existing payloads
- validate_narrative_report(): Validate report structure
"""

from .narrative_builder import (
    NarrativeReport,
    build_narrative_report,
    merge_narrative_reports,
    extract_narrative_report_from_payload,
    validate_narrative_report
)

__all__ = [
    "NarrativeReport",
    "build_narrative_report",
    "merge_narrative_reports",
    "extract_narrative_report_from_payload",
    "validate_narrative_report"
]
