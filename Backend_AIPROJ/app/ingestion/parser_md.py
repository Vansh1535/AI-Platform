"""
Markdown parser - reads MD files with basic structure awareness.
"""

from pathlib import Path
from typing import Optional, List
import re
from app.core.logging import setup_logger
from .dispatcher import ParsedDocument

logger = setup_logger()


def extract_sections(text: str) -> List[str]:
    """
    Extract sections from markdown based on headers.
    
    Args:
        text: Markdown text content
        
    Returns:
        List of section texts (split by headers)
    """
    # Split by headers (# Header, ## Header, etc.)
    sections = re.split(r'\n(?=#{1,6}\s)', text)
    
    # Filter empty sections and strip whitespace
    sections = [s.strip() for s in sections if s.strip()]
    
    return sections if len(sections) > 1 else []


def parse_md(file_path: str, source: Optional[str] = None) -> ParsedDocument:
    """
    Parse Markdown file.
    
    Args:
        file_path: Path to MD file
        source: Optional source identifier
        
    Returns:
        ParsedDocument with text content and sections
        
    Raises:
        Exception: If file reading fails
    """
    try:
        logger.info(f"Parsing MD: {Path(file_path).name}")
        
        path = Path(file_path)
        
        # Read file with UTF-8 encoding
        try:
            text = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            logger.warning(f"UTF-8 decode failed, trying latin-1 for {path.name}")
            text = path.read_text(encoding='latin-1')
        
        if not text.strip():
            raise ValueError("MD file is empty")
        
        # Extract sections by headers
        sections = extract_sections(text)
        
        # Count headers
        header_count = len(re.findall(r'^#{1,6}\s', text, re.MULTILINE))
        
        # Build metadata
        metadata = {
            "source": source or path.name,
            "file_name": path.name,
            "line_count": len(text.splitlines()),
            "header_count": header_count,
            "has_sections": len(sections) > 0
        }
        
        logger.info(
            f"MD parsed successfully - {len(text)} chars, "
            f"{header_count} headers, {len(sections)} sections"
        )
        
        return ParsedDocument(
            text=text,
            sections=sections if sections else None,
            source_type="document",
            format="md",
            metadata=metadata
        )
        
    except Exception as e:
        logger.error(f"MD parsing failed for {file_path}: {str(e)}")
        raise Exception(f"Failed to parse MD: {str(e)}") from e
