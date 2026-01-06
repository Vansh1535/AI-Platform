"""
PDF Adapter — Phase 3

Optional PDF conversion wrapper with graceful fallback.
Tries lightweight PDF conversion, falls back to Markdown if unavailable.

Philosophy:
- PDF export is OPTIONAL
- Platform must work fine without PDF tools
- Always returns usable output (PDF or Markdown)
- Never crashes the system

Supported converters (in order of preference):
1. markdown-pdf (if available)
2. pdfkit (if available)
3. Fallback: return Markdown with degradation flag
"""

import os
import tempfile
from typing import Dict, Any, Tuple
from pathlib import Path
from app.core.logging import setup_logger

logger = setup_logger("INFO")


def is_pdf_available() -> Tuple[bool, str]:
    """
    Check if PDF conversion is available.
    
    Returns:
        Tuple of (available, converter_name)
        
    Example:
        available, converter = is_pdf_available()
        if available:
            print(f"PDF conversion available via {converter}")
    """
    # Try markdown-pdf
    try:
        import markdown  # type: ignore
        # Note: markdown-pdf doesn't exist as a standard package
        # This is a placeholder for any lightweight Markdown→PDF converter
        logger.debug("Checking for markdown converter...")
        return False, "none"
    except ImportError:
        pass
    
    # Try pdfkit (requires wkhtmltopdf binary)
    try:
        import pdfkit  # type: ignore
        # Check if wkhtmltopdf is installed
        try:
            config = pdfkit.configuration()
            logger.info("PDF conversion available via pdfkit")
            return True, "pdfkit"
        except (OSError, IOError, Exception):
            logger.debug("pdfkit installed but wkhtmltopdf not found")
            return False, "none"
    except ImportError:
        logger.debug("pdfkit not installed")
    
    # Try reportlab (pure Python)
    try:
        from reportlab.lib.pagesizes import letter  # type: ignore
        from reportlab.platypus import SimpleDocTemplate  # type: ignore
        logger.info("PDF conversion available via reportlab")
        return True, "reportlab"
    except ImportError:
        logger.debug("reportlab not installed")
    
    logger.info("No PDF converter available - will use Markdown fallback")
    return False, "none"


def convert_markdown_to_pdf_pdfkit(markdown_content: str, output_path: str) -> bool:
    """
    Convert Markdown to PDF using pdfkit.
    
    Args:
        markdown_content: Markdown text
        output_path: Path to output PDF file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        import pdfkit  # type: ignore
        import markdown  # type: ignore
        
        # Convert Markdown to HTML
        html_content = markdown.markdown(
            markdown_content,
            extensions=['tables', 'fenced_code', 'codehilite']
        )
        
        # Add basic styling
        styled_html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    max-width: 800px;
                    margin: 40px auto;
                    padding: 20px;
                }}
                h1 {{
                    color: #333;
                    border-bottom: 2px solid #333;
                    padding-bottom: 10px;
                }}
                h2 {{
                    color: #555;
                    border-bottom: 1px solid #ddd;
                    padding-bottom: 5px;
                }}
                code {{
                    background-color: #f4f4f4;
                    padding: 2px 5px;
                    border-radius: 3px;
                }}
                blockquote {{
                    border-left: 4px solid #ddd;
                    padding-left: 15px;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        # Convert HTML to PDF
        pdfkit.from_string(styled_html, output_path)
        
        logger.info(f"PDF generated successfully: {output_path}")
        return True
        
    except Exception as e:
        logger.warning(f"PDF conversion failed with pdfkit: {str(e)}")
        return False


def convert_markdown_to_pdf_reportlab(markdown_content: str, output_path: str) -> bool:
    """
    Convert Markdown to PDF using reportlab (simple text-based).
    
    Args:
        markdown_content: Markdown text
        output_path: Path to output PDF file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        from reportlab.lib.pagesizes import letter  # type: ignore
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak  # type: ignore
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # type: ignore
        from reportlab.lib.units import inch  # type: ignore
        from reportlab.lib.enums import TA_LEFT, TA_CENTER  # type: ignore
        
        # Create PDF
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Parse markdown (simple parsing)
        lines = markdown_content.split('\n')
        
        for line in lines:
            line = line.strip()
            
            if not line:
                story.append(Spacer(1, 0.2*inch))
                continue
            
            # Headings
            if line.startswith('# '):
                text = line[2:].strip()
                story.append(Paragraph(text, styles['Title']))
                story.append(Spacer(1, 0.3*inch))
            elif line.startswith('## '):
                text = line[3:].strip()
                story.append(Paragraph(text, styles['Heading1']))
                story.append(Spacer(1, 0.2*inch))
            elif line.startswith('### '):
                text = line[4:].strip()
                story.append(Paragraph(text, styles['Heading2']))
                story.append(Spacer(1, 0.1*inch))
            # Lists
            elif line.startswith('- ') or line.startswith('* '):
                text = line[2:].strip()
                story.append(Paragraph(f"• {text}", styles['Normal']))
            # Horizontal rules
            elif line.startswith('---'):
                story.append(Spacer(1, 0.2*inch))
                story.append(Paragraph('_' * 80, styles['Normal']))
                story.append(Spacer(1, 0.2*inch))
            # Normal text
            else:
                # Remove markdown formatting (basic)
                text = line.replace('**', '').replace('*', '').replace('`', '')
                story.append(Paragraph(text, styles['Normal']))
        
        # Build PDF
        doc.build(story)
        
        logger.info(f"PDF generated successfully with reportlab: {output_path}")
        return True
        
    except Exception as e:
        logger.warning(f"PDF conversion failed with reportlab: {str(e)}")
        return False


def markdown_to_pdf(
    markdown_content: str,
    output_filename: str = "report.pdf"
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Convert Markdown to PDF with graceful fallback.
    
    Args:
        markdown_content: Markdown text to convert
        output_filename: Desired output filename
        
    Returns:
        Tuple of (success, file_path_or_content, metadata)
        - If PDF successful: (True, "/path/to/file.pdf", metadata)
        - If fallback: (False, markdown_content, metadata with degradation)
        
    Example:
        success, result, meta = markdown_to_pdf(markdown_text)
        if success:
            print(f"PDF created: {result}")
        else:
            print(f"Fallback Markdown: {result[:100]}...")
            print(f"Reason: {meta['fallback_reason']}")
    """
    metadata = {
        "export_format": "pdf",
        "export_latency_ms": 0,
        "converter_used": None,
        "fallback_triggered": False,
        "fallback_reason": None,
        "degradation_level": "none",
        "graceful_message": None
    }
    
    import time
    start_time = time.time()
    
    # Check if PDF conversion is available
    available, converter = is_pdf_available()
    
    if not available:
        logger.info("PDF conversion unavailable, returning Markdown fallback")
        metadata.update({
            "export_format": "markdown",
            "fallback_triggered": True,
            "fallback_reason": "pdf_converter_unavailable",
            "degradation_level": "fallback",
            "graceful_message": "PDF export unavailable. Returned Markdown instead. Install pdfkit or reportlab for PDF support."
        })
        metadata["export_latency_ms"] = int((time.time() - start_time) * 1000)
        return False, markdown_content, metadata
    
    # Create temporary output path
    temp_dir = tempfile.gettempdir()
    output_path = os.path.join(temp_dir, output_filename)
    
    # Try conversion
    success = False
    
    if converter == "pdfkit":
        success = convert_markdown_to_pdf_pdfkit(markdown_content, output_path)
        metadata["converter_used"] = "pdfkit"
    elif converter == "reportlab":
        success = convert_markdown_to_pdf_reportlab(markdown_content, output_path)
        metadata["converter_used"] = "reportlab"
    
    metadata["export_latency_ms"] = int((time.time() - start_time) * 1000)
    
    if success and os.path.exists(output_path):
        logger.info(f"PDF conversion successful: {output_path}")
        return True, output_path, metadata
    else:
        # Fallback to Markdown
        logger.warning("PDF conversion failed, falling back to Markdown")
        metadata.update({
            "export_format": "markdown",
            "fallback_triggered": True,
            "fallback_reason": "pdf_conversion_failed",
            "degradation_level": "fallback",
            "graceful_message": "PDF conversion failed. Returned Markdown instead."
        })
        return False, markdown_content, metadata


def cleanup_temp_pdf(file_path: str):
    """
    Clean up temporary PDF file.
    
    Args:
        file_path: Path to PDF file to delete
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.debug(f"Cleaned up temporary PDF: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to cleanup PDF {file_path}: {str(e)}")


def get_pdf_capabilities() -> Dict[str, Any]:
    """
    Get information about PDF conversion capabilities.
    
    Returns:
        Dictionary with PDF capability information
        
    Example:
        caps = get_pdf_capabilities()
        print(f"PDF available: {caps['available']}")
        print(f"Converter: {caps['converter']}")
    """
    available, converter = is_pdf_available()
    
    return {
        "available": available,
        "converter": converter,
        "supported_formats": ["markdown", "pdf"] if available else ["markdown"],
        "fallback_enabled": True,
        "message": "PDF export available" if available else "PDF export unavailable - Markdown fallback enabled"
    }
