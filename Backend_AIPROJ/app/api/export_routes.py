"""
Export Routes — Phase 3 (Polished)

REST endpoints for exporting insights and reports in various formats.
Supports Markdown and optional PDF export with graceful degradation.

Uses unified narrative builder for consistent report structure across all sources.
Consolidates md/pdf generation from single narrative payload.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse, Response
from pydantic import BaseModel, Field
from typing import Dict, Any, Literal, Optional
import os
import time

from app.core.logging import setup_logger
from app.export.report_builder import build_report
from app.export.pdf_adapter import markdown_to_pdf, cleanup_temp_pdf, get_pdf_capabilities
from app.reporting import (
    NarrativeReport,
    build_narrative_report,
    extract_narrative_report_from_payload,
    validate_narrative_report
)

logger = setup_logger("INFO")

router = APIRouter(prefix="/export", tags=["Export"])


class ExportRequest(BaseModel):
    """Request model for report export."""
    payload_source: Literal["rag", "summary", "csv_insights", "aggregation"] = Field(
        ...,
        description="Type of insight to export"
    )
    payload: Dict[str, Any] = Field(
        ...,
        description="The insight/report data to export"
    )
    format: Literal["md", "pdf"] = Field(
        default="md",
        description="Export format (md for markdown, pdf for PDF)"
    )
    filename: str = Field(
        default="report",
        description="Base filename for export (without extension)"
    )


class ExportResponse(BaseModel):
    """Response model for export."""
    success: bool
    format: str
    content: str
    metadata: Dict[str, Any]
    narrative_report: Optional[Dict[str, Any]] = None  # Unified narrative structure


@router.post("/report", response_model=ExportResponse)
async def export_report(request: ExportRequest):
    """
    Export insights/reports in Markdown or PDF format.
    
    Design:
    - Builds ONE narrative payload using unified narrative_builder
    - Converts to markdown, then to PDF when requested
    - Both formats contain same narrative content
    - Gracefully falls back to markdown if PDF generation fails
    
    Supports:
    - RAG answers with citations
    - Document summaries
    - CSV insights (with optional LLM insights)
    - Cross-file aggregated insights
    
    Returns:
    - For md: Returns content as string in response
    - For pdf: Attempts PDF generation, falls back to md if unavailable
    
    Graceful degradation:
    - If PDF converter unavailable → returns Markdown with degradation flag
    - If PDF conversion fails → returns Markdown with degradation flag
    - Always returns usable output
    
    Example:
        POST /export/report
        {
            "payload_source": "rag",
            "payload": {
                "query": "What is machine learning?",
                "answer": "Machine learning is...",
                "citations": [...],
                "meta": {...}
            },
            "format": "md",
            "filename": "ml_answer"
        }
    """
    start_time = time.time()
    
    try:
        # Validate payload
        if not request.payload:
            raise HTTPException(
                status_code=400,
                detail="Empty payload provided"
            )
        
        # Normalize format param (accept both "md"/"markdown" and "pdf")
        normalized_format = "md" if request.format in ["md", "markdown"] else "pdf"
        
        logger.info(f"Exporting {request.payload_source} in {normalized_format} format")
        
        # Step 1: Build Markdown report (this is the shared base)
        try:
            markdown_content = build_report(
                request.payload_source,
                request.payload
            )
        except Exception as e:
            logger.error(f"Report building failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to build report: {str(e)}"
            )
        
        # Step 2: Extract or build unified narrative report
        narrative_report = extract_narrative_report_from_payload(
            request.payload,
            payload_type=request.payload_source
        )
        
        if not narrative_report:
            # Fallback: Build from markdown content and telemetry
            narrative_report = build_narrative_report(
                report_type=request.payload_source,
                title=request.payload.get("query", request.payload.get("title", "Report")),
                summaries=[markdown_content[:200]],  # First 200 chars as summary
                insights=[],
                telemetry=request.payload.get("telemetry", {})
            )
        
        # Validate narrative report
        is_valid, error_msg = validate_narrative_report(narrative_report)
        if not is_valid:
            logger.warning(f"Narrative report validation failed: {error_msg}")
        
        # Step 3: Create standardized export metadata
        from app.export.export_schema import create_export_metadata
        export_meta = create_export_metadata(source=request.payload_source)
        
        # Step 4: Handle format-specific conversion and fallback
        export_latency = int((time.time() - start_time) * 1000)
        actual_format = normalized_format
        actual_content = markdown_content
        graceful_message = None
        degradation_level = "none"
        fallback_triggered = False
        
        if normalized_format == "pdf":
            # Attempt PDF conversion (PDF generation from markdown)
            pdf_filename = f"{request.filename}.pdf"
            
            try:
                success, result, pdf_metadata = markdown_to_pdf(
                    markdown_content,
                    output_filename=pdf_filename
                )
                
                if success:
                    # PDF generated successfully
                    logger.info(f"PDF generated: {result}")
                    
                    try:
                        with open(result, 'rb') as f:
                            pdf_bytes = f.read()
                        
                        # Clean up temp file
                        cleanup_temp_pdf(result)
                        
                        actual_format = "pdf"
                        actual_content = f"PDF generated successfully ({len(pdf_bytes)} bytes)"
                        export_meta.update(pdf_metadata)
                        
                    except Exception as e:
                        logger.error(f"Failed to read PDF file: {str(e)}")
                        # Fall back to Markdown
                        actual_format = "md"
                        actual_content = markdown_content
                        graceful_message = "PDF file could not be read. Returned Markdown instead."
                        degradation_level = "fallback"
                        fallback_triggered = True
                else:
                    # PDF conversion failed, gracefully fall back to Markdown
                    logger.info("PDF conversion failed, returning Markdown fallback")
                    actual_format = "md"
                    actual_content = markdown_content
                    graceful_message = "PDF generation unavailable. Returned Markdown instead."
                    degradation_level = "fallback"
                    fallback_triggered = True
                    export_meta.update(pdf_metadata)
                    
            except Exception as e:
                logger.error(f"PDF generation exception: {str(e)}")
                actual_format = "md"
                actual_content = markdown_content
                graceful_message = f"PDF generation failed: {str(e)}. Returned Markdown instead."
                degradation_level = "fallback"
                fallback_triggered = True
        
        # Step 5: Combine metadata
        metadata = {
            **export_meta,
            "export_format": actual_format,
            "requested_format": normalized_format,
            "export_latency_ms": export_latency,
            "degradation_level": degradation_level,
            "fallback_triggered": fallback_triggered,
            "content_size_chars": len(actual_content) if isinstance(actual_content, str) else 0
        }
        
        # Add source payload telemetry if available
        if "telemetry" in request.payload:
            metadata["source_telemetry"] = request.payload["telemetry"]
        
        # Add graceful message if present
        if graceful_message:
            metadata["graceful_message"] = graceful_message
        
        return ExportResponse(
            success=True,
            format=actual_format,
            content=actual_content,
            metadata=metadata,
            narrative_report=narrative_report.to_dict()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Export failed: {str(e)}"
        )


@router.get("/capabilities")
async def get_export_capabilities():
    """
    Get information about export capabilities.
    
    Returns:
        Dictionary with supported formats and PDF availability
        
    Features:
    - Unified narrative report structure across all sources
    - Single narrative payload converted to md or pdf
    - Graceful fallback to markdown if PDF unavailable
    - Consistent metadata structure with telemetry
        
    Example response:
        {
            "supported_sources": ["rag", "summary", "csv_insights", "aggregation"],
            "supported_formats": ["md", "pdf"],
            "narrative_format": {
                "available": true,
                "unified": true,
                "fields": ["report_type", "title", "summary_block", "insight_sections", "confidence_context", "graceful_notes", "telemetry"]
            },
            "pdf": {
                "available": true,
                "converter": "pdfkit",
                "fallback_enabled": true
            }
        }
    """
    pdf_caps = get_pdf_capabilities()
    
    return {
        "supported_sources": ["rag", "summary", "csv_insights", "aggregation"],
        "supported_formats": ["md", "pdf"],
        "narrative_format": {
            "available": True,
            "unified": True,
            "description": "All exports use unified NarrativeReport structure",
            "fields": [
                "report_type",
                "title",
                "summary_block",
                "insight_sections",
                "confidence_context",
                "graceful_notes",
                "telemetry"
            ]
        },
        "pdf": pdf_caps,
        "markdown": {
            "available": True,
            "message": "Markdown export always available"
        },
        "polish_features": {
            "unified_narrative_builder": True,
            "format_consolidation": True,
            "single_payload_multiple_formats": True
        }
    }
