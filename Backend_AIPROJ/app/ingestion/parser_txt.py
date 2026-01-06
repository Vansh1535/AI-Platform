"""
Plain text parser - reads TXT files.
"""

from pathlib import Path
from typing import Optional
from app.core.logging import setup_logger
from .dispatcher import ParsedDocument

logger = setup_logger()


def parse_txt(file_path: str, source: Optional[str] = None) -> ParsedDocument:
    """
    Parse plain text file.
    
    Args:
        file_path: Path to TXT file
        source: Optional source identifier
        
    Returns:
        ParsedDocument with text content
        
    Raises:
        Exception: If file reading fails
    """
    try:
        logger.info(f"Parsing TXT: {Path(file_path).name}")
        
        path = Path(file_path)
        
        # Read file with UTF-8 encoding (fallback to latin-1 if needed)
        try:
            text = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            logger.warning(f"UTF-8 decode failed, trying latin-1 for {path.name}")
            text = path.read_text(encoding='latin-1')
        
        if not text.strip():
            raise ValueError("TXT file is empty")
        
        # Build metadata
        metadata = {
            "source": source or path.name,
            "file_name": path.name,
            "line_count": len(text.splitlines())
        }
        
        logger.info(f"TXT parsed successfully - {len(text)} chars, {metadata['line_count']} lines")
        
        return ParsedDocument(
            text=text,
            sections=None,  # Plain text has no natural sections
            source_type="document",
            format="txt",
            metadata=metadata
        )
        
    except Exception as e:
        logger.error(f"TXT parsing failed for {file_path}: {str(e)}")
        raise Exception(f"Failed to parse TXT: {str(e)}") from e
