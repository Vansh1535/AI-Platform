"""
Narrative Report Builder — Unified narrative format across platform.

Consolidation point for report generation from:
- RAG Answers with citations
- Document Summaries
- CSV Insights (deterministic + optional LLM)
- Cross-File Aggregated Insights

Design:
- Single source of truth for narrative report structure
- Reuses existing narrative content (never invents text)
- Ensures consistent field naming across all exports
- Non-breaking: Returns standardized structure, all existing content preserved
"""

from typing import Dict, Any, List, Optional, Literal
from dataclasses import dataclass, asdict
from app.core.logging import setup_logger

logger = setup_logger("INFO")


@dataclass
class NarrativeReport:
    """
    Unified narrative report structure for all exports.
    
    Used by:
    - RAG Answer export
    - Document Summary export
    - CSV Insights export
    - Cross-File Aggregation export
    """
    report_type: str  # "rag_answer", "summary", "csv_insights", "aggregation"
    title: str  # Report/query title
    summary_block: str  # 1-2 sentence executive summary
    insight_sections: List[Dict[str, Any]]  # Detailed insights/findings
    confidence_context: Dict[str, Any]  # Confidence metrics and context
    graceful_notes: Optional[str] = None  # Any degradation/fallback messages
    telemetry: Optional[Dict[str, Any]] = None  # Telemetry context
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "report_type": self.report_type,
            "title": self.title,
            "summary_block": self.summary_block,
            "insight_sections": self.insight_sections,
            "confidence_context": self.confidence_context,
            "graceful_notes": self.graceful_notes,
            "telemetry": self.telemetry
        }


def build_narrative_report(
    report_type: Literal["rag_answer", "summary", "csv_insights", "aggregation"],
    title: str,
    summaries: List[str],
    insights: List[Dict[str, Any]],
    telemetry: Dict[str, Any],
    graceful_message: Optional[str] = None
) -> NarrativeReport:
    """
    Build a unified narrative report from component data.
    
    Args:
        report_type: Type of report being generated
        title: Report title (e.g., query, document name)
        summaries: List of summary sentences (will be combined)
        insights: List of insight dictionaries with 'heading' and 'content'
        telemetry: Telemetry context (passed through)
        graceful_message: Optional degradation message
    
    Returns:
        NarrativeReport with consistent structure
        
    Design:
    - Does NOT invent narrative content
    - Reuses all existing text from summaries and insights
    - Simply reshapes into consistent structure
    - All original data preserved
    """
    
    # Combine summaries into single block
    summary_block = " ".join(summaries) if summaries else "No summary available."
    
    # Build insight sections
    insight_sections = []
    for insight in insights:
        if isinstance(insight, dict):
            insight_sections.append({
                "heading": insight.get("heading", "Finding"),
                "content": insight.get("content", ""),
                "confidence": insight.get("confidence", 0.5),
                "source": insight.get("source", "")
            })
    
    # Build confidence context
    confidence_context = {
        "overall_confidence": telemetry.get("confidence_score", 0.5),
        "retrieval_quality": telemetry.get("retrieval_quality", "unknown"),
        "has_sources": len(insight_sections) > 0,
        "source_count": len(insight_sections),
        "routing_decision": telemetry.get("routing_decision", "fallback"),
        "fallback_triggered": telemetry.get("fallback_triggered", False),
        "degradation_level": telemetry.get("degradation_level", "none")
    }
    
    return NarrativeReport(
        report_type=report_type,
        title=title,
        summary_block=summary_block,
        insight_sections=insight_sections,
        confidence_context=confidence_context,
        graceful_notes=graceful_message,
        telemetry=telemetry
    )


def merge_narrative_reports(
    reports: List[NarrativeReport],
    merged_title: str
) -> NarrativeReport:
    """
    Merge multiple narrative reports into a single report.
    
    Used for aggregating insights across multiple documents/queries.
    
    Args:
        reports: List of NarrativeReport objects to merge
        merged_title: Title for merged report
        
    Returns:
        Single merged NarrativeReport
    """
    if not reports:
        return NarrativeReport(
            report_type="aggregation",
            title=merged_title,
            summary_block="No reports to merge.",
            insight_sections=[],
            confidence_context={"overall_confidence": 0.0, "source_count": 0},
            telemetry={}
        )
    
    # Combine all summaries
    combined_summaries = [r.summary_block for r in reports if r.summary_block]
    
    # Combine all insights
    combined_insights = []
    for report in reports:
        for insight in report.insight_sections:
            # Tag insight with source report
            insight_copy = insight.copy()
            insight_copy["source_report"] = report.title
            combined_insights.append(insight_copy)
    
    # Average confidence across reports
    avg_confidence = sum(
        r.confidence_context.get("overall_confidence", 0.5)
        for r in reports
    ) / len(reports) if reports else 0.0
    
    # Merge telemetry (take latest/most complete)
    merged_telemetry = {}
    for report in reports:
        if report.telemetry:
            merged_telemetry.update(report.telemetry)
    
    return NarrativeReport(
        report_type="aggregation",
        title=merged_title,
        summary_block=" ".join(combined_summaries),
        insight_sections=combined_insights,
        confidence_context={
            "overall_confidence": avg_confidence,
            "source_count": len(reports),
            "merged_from_count": len(reports),
            "routing_decision": "aggregation",
            "fallback_triggered": False,
            "degradation_level": "none"
        },
        graceful_notes=None,
        telemetry=merged_telemetry
    )


def extract_narrative_report_from_payload(
    payload: Dict[str, Any],
    payload_type: Literal["rag", "summary", "csv_insights", "aggregation"]
) -> Optional[NarrativeReport]:
    """
    Extract or construct a narrative report from existing payload.
    
    This function bridges existing payloads (which may not have
    NarrativeReport structure) to the unified format.
    
    Args:
        payload: Existing export payload
        payload_type: Type of payload source
        
    Returns:
        NarrativeReport extracted/constructed from payload, or None if not applicable
        
    Design:
    - Does NOT require payloads to use NarrativeReport
    - Works with existing payload structures
    - Gracefully handles missing fields
    """
    
    if not payload:
        return None
    
    # Extract common fields if they exist
    title = payload.get("query", payload.get("title", "Report"))
    telemetry = payload.get("telemetry", {})
    graceful_msg = payload.get("graceful_message")
    
    # Extract summaries
    summaries = []
    if "answer" in payload:
        summaries.append(payload["answer"])
    if "summary" in payload:
        summaries.append(payload["summary"])
    if "main_findings" in payload:
        summaries.extend(
            str(f) for f in payload["main_findings"]
            if isinstance(f, str)
        )
    
    # Extract insights
    insights = []
    if "insights" in payload and isinstance(payload["insights"], list):
        insights = payload["insights"]
    if "findings" in payload and isinstance(payload["findings"], list):
        insights.extend(payload["findings"])
    if "citations" in payload and isinstance(payload["citations"], list):
        # Format citations as insights
        for citation in payload["citations"]:
            if isinstance(citation, dict):
                insights.append({
                    "heading": "Citation",
                    "content": citation.get("text", ""),
                    "source": citation.get("source", "")
                })
    
    if not summaries and not insights:
        return None
    
    # Construct report type mapping
    type_mapping = {
        "rag": "rag_answer",
        "summary": "summary",
        "csv_insights": "csv_insights",
        "aggregation": "aggregation"
    }
    
    return build_narrative_report(
        report_type=type_mapping.get(payload_type, payload_type),
        title=title,
        summaries=summaries,
        insights=insights,
        telemetry=telemetry,
        graceful_message=graceful_msg
    )


def validate_narrative_report(report: NarrativeReport) -> tuple[bool, Optional[str]]:
    """
    Validate a narrative report structure.
    
    Args:
        report: NarrativeReport to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    
    if not report.title:
        return False, "Report must have a title"
    
    if not report.summary_block:
        return False, "Report must have a summary block"
    
    if not isinstance(report.insight_sections, list):
        return False, "Insight sections must be a list"
    
    if not isinstance(report.confidence_context, dict):
        return False, "Confidence context must be a dict"
    
    # Validate each insight section
    for i, section in enumerate(report.insight_sections):
        if not isinstance(section, dict):
            return False, f"Insight section {i} must be a dict"
        if "heading" not in section or "content" not in section:
            return False, f"Insight section {i} missing heading/content"
    
    return True, None
