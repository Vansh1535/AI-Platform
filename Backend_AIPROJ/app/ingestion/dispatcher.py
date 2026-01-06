"""
Ingestion dispatcher - routes files to appropriate parsers based on type.
Maintains backward compatibility with existing PDF pipeline.
"""

import mimetypes
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from app.core.logging import setup_logger

logger = setup_logger()


@dataclass
class ParsedDocument:
    """
    Unified document representation after parsing.
    All parsers must return this structure.
    """
    text: str  # Main content for embedding
    sections: Optional[List[str]] = None  # Optional section breakdown
    source_type: str = "document"  # "document" or "table"
    format: str = "unknown"  # pdf, txt, md, docx, csv
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return asdict(self)


# File extension to format mapping
EXTENSION_MAP = {
    '.pdf': 'pdf',
    '.txt': 'txt',
    '.md': 'md',
    '.markdown': 'md',
    '.docx': 'docx',
    '.csv': 'csv'
}

# MIME type to format mapping (fallback)
MIME_MAP = {
    'application/pdf': 'pdf',
    'text/plain': 'txt',
    'text/markdown': 'md',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
    'text/csv': 'csv',
    'application/csv': 'csv'
}


def detect_file_type(file_path: str) -> tuple[str, str]:
    """
    Detect file type by extension and MIME type.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Tuple of (format, mime_type)
        
    Raises:
        ValueError: If file type cannot be determined or is unsupported
    """
    path = Path(file_path)
    
    # Check if file exists
    if not path.exists():
        raise ValueError(f"File not found: {file_path}")
    
    # Get extension
    extension = path.suffix.lower()
    
    # Try extension first (most reliable)
    if extension in EXTENSION_MAP:
        detected_format = EXTENSION_MAP[extension]
        logger.info(f"File type detected by extension: {detected_format} ({extension})")
        
        # Get MIME type for validation
        mime_type, _ = mimetypes.guess_type(file_path)
        return detected_format, mime_type or "unknown"
    
    # Fallback to MIME type detection
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type and mime_type in MIME_MAP:
        detected_format = MIME_MAP[mime_type]
        logger.info(f"File type detected by MIME: {detected_format} ({mime_type})")
        return detected_format, mime_type
    
    # Unable to detect
    raise ValueError(
        f"Unsupported or unrecognized file type: {extension} "
        f"(MIME: {mime_type}). Supported formats: PDF, TXT, MD, DOCX, CSV"
    )


def dispatch_file(file_path: str, source: Optional[str] = None) -> ParsedDocument:
    """
    Dispatch file to appropriate parser based on detected type.
    
    Args:
        file_path: Path to the file to parse
        source: Optional source identifier
        
    Returns:
        ParsedDocument: Unified parsed document structure
        
    Raises:
        ValueError: If file type is unsupported
        Exception: If parsing fails with structured error metadata
    """
    try:
        # Detect file type
        file_format, mime_type = detect_file_type(file_path)
        
        logger.info(f"Dispatching file to {file_format.upper()} parser: {Path(file_path).name}")
        
        # Route to appropriate parser
        if file_format == 'pdf':
            from .parser_pdf import parse_pdf
            result = parse_pdf(file_path, source)
        elif file_format == 'txt':
            from .parser_txt import parse_txt
            result = parse_txt(file_path, source)
        elif file_format == 'md':
            from .parser_md import parse_md
            result = parse_md(file_path, source)
        elif file_format == 'docx':
            from .parser_docx import parse_docx
            result = parse_docx(file_path, source)
        elif file_format == 'csv':
            from .parser_csv import parse_csv
            result = parse_csv(file_path, source)
        else:
            raise ValueError(f"No parser available for format: {file_format}")
        
        # Enrich metadata
        result.metadata.update({
            "mime_type": mime_type,
            "ingestion_method": "multi_file_ingest_v1",
            "file_size_bytes": Path(file_path).stat().st_size
        })
        
        logger.info(
            f"Parsing complete - Format: {result.format}, "
            f"Source Type: {result.source_type}, "
            f"Content Length: {len(result.text)} chars"
        )
        
        return result
        
    except ValueError as e:
        # File type detection or validation errors
        logger.error(f"File dispatch failed: {str(e)}")
        raise
        
    except Exception as e:
        # Parser errors - return structured error
        logger.error(f"Parser error for {file_path}: {str(e)}")
        
        # Create error document with metadata
        error_metadata = {
            "error": str(e),
            "error_type": type(e).__name__,
            "file_path": file_path,
            "ingestion_method": "multi_file_ingest_v1",
            "parsing_failed": True
        }
        
        raise Exception(
            f"Failed to parse file {Path(file_path).name}: {str(e)}"
        ) from e


def get_supported_formats() -> List[str]:
    """
    Get list of supported file formats.
    
    Returns:
        List of supported format strings
    """
    return list(set(EXTENSION_MAP.values()))


def is_supported_format(file_path: str) -> bool:
    """
    Check if file format is supported.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if format is supported, False otherwise
    """
    try:
        detect_file_type(file_path)
        return True
    except ValueError:
        return False
