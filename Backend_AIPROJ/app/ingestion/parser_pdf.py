"""
PDF parser - reuses existing PDF processing pipeline.
Maintains backward compatibility with current implementation.
"""

from pathlib import Path
from typing import Optional
from app.core.logging import setup_logger
from app.docqa.pipeline.process_pdf import process_pdf
from .dispatcher import ParsedDocument

logger = setup_logger()


def parse_pdf(file_path: str, source: Optional[str] = None) -> ParsedDocument:
    """
    Parse PDF file using existing pipeline.
    
    Args:
        file_path: Path to PDF file
        source: Optional source identifier
        
    Returns:
        ParsedDocument with extracted text and metadata
        
    Raises:
        Exception: If PDF processing fails
    """
    try:
        logger.info(f"Parsing PDF: {Path(file_path).name}")
        
        # Use existing PDF processing pipeline
        pages = process_pdf(file_path)
        
        if not pages:
            raise ValueError("PDF processing returned no pages")
        
        # Combine all page text
        full_text = "\n\n".join(page["text"] for page in pages if page.get("text"))
        
        # Extract sections by page (optional breakdown)
        sections = [page["text"] for page in pages if page.get("text")]
        
        # Build metadata
        metadata = {
            "page_count": len(pages),
            "source": source or Path(file_path).name,
            "file_name": Path(file_path).name
        }
        
        # Add any existing metadata from pages
        if pages and "metadata" in pages[0]:
            metadata.update(pages[0]["metadata"])
        
        logger.info(f"PDF parsed successfully - {len(pages)} pages, {len(full_text)} chars")
        
        return ParsedDocument(
            text=full_text,
            sections=sections if len(sections) > 1 else None,
            source_type="document",
            format="pdf",
            metadata=metadata
        )
        
    except Exception as e:
        logger.error(f"PDF parsing failed for {file_path}: {str(e)}")
        raise Exception(f"Failed to parse PDF: {str(e)}") from e
