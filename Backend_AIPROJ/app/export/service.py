"""
Document Export Service — Markdown/PDF Export with Graceful Fallback

Supports exporting:
- CSV insights (statistical profiles)
- RAG insights (question-answer pairs)
- Cross-file insights (aggregated patterns)

Formats:
- Markdown (default)
- PDF (with graceful markdown fallback if PDF generation fails)

Graceful degradation: Returns markdown if PDF unavailable.
Never calls LLM unless enable_llm_insights=True.
"""

import time
from typing import Dict, Any, List, Optional
from enum import Enum
from app.core.logging import setup_logger

logger = setup_logger("INFO")


class ExportType(str, Enum):
    """Export content types."""
    CSV = "csv"
    RAG = "rag"
    INSIGHTS = "insights"


class ExportFormat(str, Enum):
    """Export output formats."""
    MARKDOWN = "markdown"
    PDF = "pdf"


def format_csv_insights_markdown(
    document_id: str,
    insights: Dict[str, Any],
    telemetry: Optional[Dict[str, Any]] = None
) -> str:
    """
    Format CSV insights as Markdown.
    
    Args:
        document_id: Document identifier
        insights: CSV insights dictionary with column_profiles, data_quality, etc.
        telemetry: Optional telemetry dictionary
        
    Returns:
        Formatted Markdown string
    """
    lines = []
    
    # Header
    lines.append(f"# CSV Insights Report\n")
    lines.append(f"**Document ID:** `{document_id}`")
    lines.append(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Summary
    if "summary" in insights:
        summary = insights["summary"]
        lines.append("## Dataset Summary\n")
        lines.append(f"- **Rows:** {summary.get('rows', 'N/A')}")
        lines.append(f"- **Columns:** {summary.get('columns', 'N/A')}")
        lines.append(f"- **Numeric Columns:** {summary.get('numeric_columns', 0)}")
        lines.append(f"- **Categorical Columns:** {summary.get('categorical_columns', 0)}\n")
    
    # Insight Notes
    if "insight_notes" in insights:
        lines.append("## Analytical Insights\n")
        lines.append(insights["insight_notes"])
        lines.append("")
    
    # Column Profiles
    if "column_profiles" in insights:
        profiles = insights["column_profiles"]
        if profiles:
            lines.append("## Column Analysis\n")
            
            for col_name, profile in profiles.items():
                col_type = profile.get("type", "unknown")
                lines.append(f"### {col_name}")
                lines.append(f"**Type:** `{col_type}`\n")
                
                if col_type in ["numeric", "categorical_numeric"]:
                    lines.append("**Statistics:**")
                    lines.append(f"- Count: {profile.get('count', 'N/A')}")
                    lines.append(f"- Mean: {profile.get('mean', 'N/A')}")
                    lines.append(f"- Median: {profile.get('median', 'N/A')}")
                    lines.append(f"- Std Dev: {profile.get('std', 'N/A')}")
                    lines.append(f"- Min: {profile.get('min', 'N/A')}")
                    lines.append(f"- Max: {profile.get('max', 'N/A')}")
                    
                    if "nulls" in profile:
                        lines.append(f"- Null Count: {profile['nulls']}")
                    lines.append("")
                    
                elif col_type in ["categorical", "text"]:
                    lines.append("**Distribution:**")
                    if "top_categories" in profile:
                        for cat, count in profile["top_categories"].items():
                            lines.append(f"- `{cat}`: {count}")
                    lines.append("")
    
    # Data Quality
    if "data_quality" in insights:
        quality = insights["data_quality"]
        lines.append("## Data Quality Assessment\n")
        
        if "null_count" in quality:
            lines.append(f"- **Total Nulls:** {quality['null_count']}")
        if "duplicate_rows" in quality:
            lines.append(f"- **Duplicate Rows:** {quality['duplicate_rows']}")
        if "completeness_ratio" in quality:
            lines.append(f"- **Completeness:** {quality['completeness_ratio']:.1%}")
        
        if "flags" in quality and quality["flags"]:
            lines.append("- **Quality Flags:**")
            for flag in quality["flags"]:
                lines.append(f"  - {flag}")
        
        lines.append("")
    
    # Telemetry (if provided)
    if telemetry:
        lines.append("## Export Telemetry\n")
        lines.append(f"- **Latency:** {telemetry.get('latency_ms_total', 'N/A')}ms")
        lines.append(f"- **Cache Hit:** {telemetry.get('cache_hit', False)}")
        lines.append(f"- **Fallback Triggered:** {telemetry.get('fallback_triggered', False)}")
        lines.append(f"- **Degradation Level:** {telemetry.get('degradation_level', 'none')}")
        if telemetry.get("graceful_message"):
            lines.append(f"- **Note:** {telemetry['graceful_message']}")
        lines.append("")
    
    return "\n".join(lines)


def format_rag_insights_markdown(
    document_ids: List[str],
    rag_results: Dict[str, Any],
    telemetry: Optional[Dict[str, Any]] = None
) -> str:
    """
    Format RAG insights as Markdown.
    
    Args:
        document_ids: List of source document IDs
        rag_results: RAG result dictionary with questions, answers, sources
        telemetry: Optional telemetry dictionary
        
    Returns:
        Formatted Markdown string
    """
    lines = []
    
    # Header
    lines.append(f"# RAG Insights Report\n")
    lines.append(f"**Source Documents:** {', '.join(f'`{doc_id}`' for doc_id in document_ids)}")
    lines.append(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Q&A Pairs
    if "qa_pairs" in rag_results:
        lines.append("## Key Insights from Documents\n")
        
        for i, qa in enumerate(rag_results["qa_pairs"], 1):
            lines.append(f"### Question {i}: {qa.get('question', 'N/A')}\n")
            lines.append(f"**Answer:** {qa.get('answer', 'N/A')}\n")
            
            if "confidence" in qa:
                lines.append(f"**Confidence:** {qa['confidence']:.1%}\n")
            
            if "sources" in qa and qa["sources"]:
                lines.append("**Source Documents:**")
                for source in qa["sources"]:
                    lines.append(f"- {source}")
                lines.append("")
    
    # Summary Narrative
    if "summary" in rag_results:
        lines.append("## Document Summary\n")
        lines.append(rag_results["summary"])
        lines.append("")
    
    # Telemetry
    if telemetry:
        lines.append("## Export Telemetry\n")
        lines.append(f"- **Latency:** {telemetry.get('latency_ms_total', 'N/A')}ms")
        lines.append(f"- **Fallback Triggered:** {telemetry.get('fallback_triggered', False)}")
        lines.append(f"- **Degradation Level:** {telemetry.get('degradation_level', 'none')}")
        lines.append("")
    
    return "\n".join(lines)


def format_aggregated_insights_markdown(
    insights_data: List[Dict[str, Any]],
    aggregation_type: str = "patterns",
    telemetry: Optional[Dict[str, Any]] = None
) -> str:
    """
    Format aggregated cross-file insights as Markdown.
    
    Args:
        insights_data: List of insight dictionaries
        aggregation_type: Type of aggregation (patterns, trends, anomalies)
        telemetry: Optional telemetry dictionary
        
    Returns:
        Formatted Markdown string
    """
    lines = []
    
    # Header
    lines.append(f"# Cross-File Insights Report ({aggregation_type.title()})\n")
    lines.append(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    if aggregation_type == "patterns":
        lines.append("## Identified Patterns\n")
        for i, insight in enumerate(insights_data, 1):
            lines.append(f"### Pattern {i}\n")
            lines.append(f"**Description:** {insight.get('description', 'N/A')}\n")
            lines.append(f"**Confidence:** {insight.get('confidence', 0):.1%}\n")
            if "affected_documents" in insight:
                lines.append(f"**Affected Documents:** {', '.join(insight['affected_documents'])}\n")
            lines.append("")
    
    elif aggregation_type == "trends":
        lines.append("## Observed Trends\n")
        for i, trend in enumerate(insights_data, 1):
            lines.append(f"### Trend {i}: {trend.get('name', 'N/A')}\n")
            lines.append(f"**Direction:** {trend.get('direction', 'N/A')}")
            lines.append(f"**Magnitude:** {trend.get('magnitude', 'N/A')}\n")
            if "evidence" in trend:
                lines.append("**Evidence:**")
                for evidence in trend["evidence"]:
                    lines.append(f"- {evidence}")
                lines.append("")
    
    elif aggregation_type == "anomalies":
        lines.append("## Detected Anomalies\n")
        for i, anomaly in enumerate(insights_data, 1):
            lines.append(f"### Anomaly {i}\n")
            lines.append(f"**Type:** {anomaly.get('type', 'N/A')}\n")
            lines.append(f"**Severity:** {anomaly.get('severity', 'low')}\n")
            lines.append(f"**Description:** {anomaly.get('description', 'N/A')}\n")
            lines.append("")
    
    # Telemetry
    if telemetry:
        lines.append("## Export Telemetry\n")
        lines.append(f"- **Latency:** {telemetry.get('latency_ms_total', 'N/A')}ms")
        lines.append(f"- **Degradation Level:** {telemetry.get('degradation_level', 'none')}")
        lines.append("")
    
    return "\n".join(lines)


async def export_document(
    document_id: str,
    export_type: ExportType,
    export_format: ExportFormat = ExportFormat.MARKDOWN,
    insights_data: Optional[Dict[str, Any]] = None,
    enable_llm_insights: bool = False,
    telemetry: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Export document insights in specified format.
    
    Args:
        document_id: Document identifier
        export_type: Type of content to export (csv, rag, insights)
        export_format: Output format (markdown or pdf)
        insights_data: Pre-computed insights data
        enable_llm_insights: Whether LLM insights are enabled
        telemetry: Optional telemetry dictionary
        
    Returns:
        Dictionary with content and metadata
    """
    start_time = time.time()
    response_telemetry = telemetry or {
        "latency_ms_total": 0,
        "format": export_format.value,
        "type": export_type.value,
        "fallback_triggered": False,
        "degradation_level": "none"
    }
    
    try:
        # Generate Markdown version
        markdown_content = None
        
        if export_type == ExportType.CSV:
            if insights_data:
                markdown_content = format_csv_insights_markdown(document_id, insights_data, telemetry)
            else:
                markdown_content = f"# CSV Insights\n\nNo insights data available for document `{document_id}`"
        
        elif export_type == ExportType.RAG:
            if insights_data:
                doc_ids = insights_data.get("source_documents", [document_id])
                markdown_content = format_rag_insights_markdown(doc_ids, insights_data, telemetry)
            else:
                markdown_content = f"# RAG Insights\n\nNo RAG data available for document `{document_id}`"
        
        elif export_type == ExportType.INSIGHTS:
            if insights_data:
                markdown_content = format_aggregated_insights_markdown(
                    insights_data.get("patterns", []),
                    insights_data.get("aggregation_type", "patterns"),
                    telemetry
                )
            else:
                markdown_content = f"# Cross-File Insights\n\nNo insights data available"
        
        # If Markdown requested, return it
        if export_format == ExportFormat.MARKDOWN:
            latency_ms = int((time.time() - start_time) * 1000)
            response_telemetry["latency_ms_total"] = latency_ms
            
            return {
                "status": "success",
                "format": "markdown",
                "content": markdown_content,
                "document_id": document_id,
                "export_type": export_type.value,
                "telemetry": response_telemetry
            }
        
        # If PDF requested, try to convert
        elif export_format == ExportFormat.PDF:
            try:
                import markdown_pdf
                pdf_content = markdown_pdf.convert(markdown_content)
                latency_ms = int((time.time() - start_time) * 1000)
                response_telemetry["latency_ms_total"] = latency_ms
                
                return {
                    "status": "success",
                    "format": "pdf",
                    "content": pdf_content,
                    "document_id": document_id,
                    "export_type": export_type.value,
                    "telemetry": response_telemetry
                }
            
            except ImportError:
                # Gracefully fallback to Markdown if PDF library unavailable
                logger.warning("⚠️ PDF library not available - falling back to Markdown")
                latency_ms = int((time.time() - start_time) * 1000)
                response_telemetry.update({
                    "latency_ms_total": latency_ms,
                    "fallback_triggered": True,
                    "degradation_level": "degraded",
                    "graceful_message": "PDF generation unavailable - returning Markdown instead"
                })
                
                return {
                    "status": "success_degraded",
                    "format": "markdown",
                    "content": markdown_content,
                    "document_id": document_id,
                    "export_type": export_type.value,
                    "telemetry": response_telemetry
                }
            
            except Exception as e:
                # Graceful fallback on PDF conversion error
                logger.warning(f"⚠️ PDF conversion failed: {str(e)} - falling back to Markdown")
                latency_ms = int((time.time() - start_time) * 1000)
                response_telemetry.update({
                    "latency_ms_total": latency_ms,
                    "fallback_triggered": True,
                    "degradation_level": "degraded",
                    "graceful_message": f"PDF conversion error: {str(e)} - returning Markdown instead"
                })
                
                return {
                    "status": "success_degraded",
                    "format": "markdown",
                    "content": markdown_content,
                    "document_id": document_id,
                    "export_type": export_type.value,
                    "telemetry": response_telemetry
                }
    
    except Exception as e:
        logger.error(f"Export failed for document {document_id}: {str(e)}")
        latency_ms = int((time.time() - start_time) * 1000)
        response_telemetry["latency_ms_total"] = latency_ms
        
        return {
            "status": "failed",
            "error": str(e),
            "document_id": document_id,
            "export_type": export_type.value,
            "telemetry": response_telemetry
        }
