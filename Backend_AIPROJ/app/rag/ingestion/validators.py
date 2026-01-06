"""
Validation utilities for document ingestion.
Ensures files are valid before processing to prevent corrupted data.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import pdfplumber
from app.core.logging import setup_logger

logger = setup_logger("INFO")

# Configuration
MAX_FILE_SIZE_MB = 50
MIN_FILE_SIZE_BYTES = 100
MIN_TEXT_LENGTH = 10


class ValidationError(Exception):
    """Structured validation error with details."""
    
    def __init__(self, error_type: str, message: str, details: Optional[Dict] = None):
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "error_type": self.error_type,
            "message": self.message,
            "details": self.details
        }


def validate_file_exists(file_path: str) -> Dict[str, Any]:
    """
    Validate that file exists and is accessible.
    
    Args:
        file_path: Path to file
    
    Returns:
        dict: Validation result with file metadata
    
    Raises:
        ValidationError: If file doesn't exist or isn't accessible
    """
    path = Path(file_path)
    
    if not path.exists():
        raise ValidationError(
            error_type="FILE_NOT_FOUND",
            message=f"File not found: {file_path}",
            details={"file_path": file_path}
        )
    
    if not path.is_file():
        raise ValidationError(
            error_type="NOT_A_FILE",
            message=f"Path is not a file: {file_path}",
            details={"file_path": file_path}
        )
    
    try:
        file_size = path.stat().st_size
    except Exception as e:
        raise ValidationError(
            error_type="FILE_ACCESS_ERROR",
            message=f"Cannot access file: {str(e)}",
            details={"file_path": file_path, "error": str(e)}
        )
    
    logger.info(f"File exists: {file_path} ({file_size} bytes)")
    
    return {
        "file_path": str(path.absolute()),
        "filename": path.name,
        "file_size_bytes": file_size,
        "file_extension": path.suffix.lower()
    }


def validate_file_size(file_size_bytes: int) -> None:
    """
    Validate file size is within acceptable limits.
    
    Args:
        file_size_bytes: File size in bytes
    
    Raises:
        ValidationError: If file size is invalid
    """
    if file_size_bytes < MIN_FILE_SIZE_BYTES:
        raise ValidationError(
            error_type="FILE_TOO_SMALL",
            message=f"File is too small ({file_size_bytes} bytes). Minimum: {MIN_FILE_SIZE_BYTES} bytes.",
            details={
                "file_size_bytes": file_size_bytes,
                "min_size_bytes": MIN_FILE_SIZE_BYTES
            }
        )
    
    max_size_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    
    if file_size_bytes > max_size_bytes:
        raise ValidationError(
            error_type="FILE_TOO_LARGE",
            message=f"File exceeds maximum size ({file_size_bytes / 1024 / 1024:.2f} MB). Maximum: {MAX_FILE_SIZE_MB} MB.",
            details={
                "file_size_bytes": file_size_bytes,
                "max_size_bytes": max_size_bytes,
                "file_size_mb": round(file_size_bytes / 1024 / 1024, 2),
                "max_size_mb": MAX_FILE_SIZE_MB
            }
        )
    
    logger.info(f"File size valid: {file_size_bytes} bytes ({file_size_bytes / 1024 / 1024:.2f} MB)")


def validate_pdf(file_path: str) -> Dict[str, Any]:
    """
    Validate PDF file integrity and extract metadata.
    
    Args:
        file_path: Path to PDF file
    
    Returns:
        dict: PDF metadata (page_count, has_text, etc.)
    
    Raises:
        ValidationError: If PDF is corrupted or invalid
    """
    logger.info(f"Validating PDF: {file_path}")
    
    try:
        with pdfplumber.open(file_path) as pdf:
            page_count = len(pdf.pages)
            
            if page_count == 0:
                raise ValidationError(
                    error_type="EMPTY_PDF",
                    message="PDF contains no pages",
                    details={"file_path": file_path}
                )
            
            # Extract text from first few pages to verify readability
            text_sample = ""
            pages_to_check = min(3, page_count)
            
            for i in range(pages_to_check):
                try:
                    page_text = pdf.pages[i].extract_text() or ""
                    text_sample += page_text
                except Exception as e:
                    logger.warning(f"Could not extract text from page {i + 1}: {e}")
            
            has_text = len(text_sample.strip()) >= MIN_TEXT_LENGTH
            
            if not has_text:
                logger.warning(f"PDF appears to have no extractable text: {file_path}")
            
            # Extract metadata
            metadata = pdf.metadata or {}
            
            validation_result = {
                "page_count": page_count,
                "has_text": has_text,
                "text_sample_length": len(text_sample),
                "metadata": {
                    "title": metadata.get("Title"),
                    "author": metadata.get("Author"),
                    "creator": metadata.get("Creator"),
                    "producer": metadata.get("Producer")
                }
            }
            
            logger.info(f"PDF validation successful: {page_count} pages, text={has_text}")
            return validation_result
    
    except pdfplumber.pdfminer.pdfparser.PDFSyntaxError as e:
        raise ValidationError(
            error_type="CORRUPTED_PDF",
            message=f"PDF file is corrupted or invalid: {str(e)}",
            details={"file_path": file_path, "error": str(e)}
        )
    
    except Exception as e:
        raise ValidationError(
            error_type="PDF_VALIDATION_ERROR",
            message=f"Failed to validate PDF: {str(e)}",
            details={"file_path": file_path, "error": str(e)}
        )


def validate_text_content(text: str, min_length: int = MIN_TEXT_LENGTH) -> None:
    """
    Validate that extracted text meets minimum requirements.
    
    Args:
        text: Extracted text content
        min_length: Minimum acceptable text length
    
    Raises:
        ValidationError: If text is insufficient
    """
    text_length = len(text.strip())
    
    if text_length < min_length:
        raise ValidationError(
            error_type="INSUFFICIENT_TEXT",
            message=f"Extracted text too short ({text_length} chars). Minimum: {min_length} chars.",
            details={
                "text_length": text_length,
                "min_length": min_length
            }
        )
    
    logger.info(f"Text content valid: {text_length} characters")


def validate_ingestion_config(
    chunk_size: int,
    overlap: int,
    tokenizer_name: str
) -> None:
    """
    Validate chunking configuration parameters.
    
    Args:
        chunk_size: Size of text chunks
        overlap: Overlap between chunks
        tokenizer_name: Name of tokenizer
    
    Raises:
        ValidationError: If configuration is invalid
    """
    if chunk_size <= 0:
        raise ValidationError(
            error_type="INVALID_CHUNK_SIZE",
            message=f"Chunk size must be positive: {chunk_size}",
            details={"chunk_size": chunk_size}
        )
    
    if overlap < 0:
        raise ValidationError(
            error_type="INVALID_OVERLAP",
            message=f"Overlap cannot be negative: {overlap}",
            details={"overlap": overlap}
        )
    
    if overlap >= chunk_size:
        raise ValidationError(
            error_type="INVALID_OVERLAP",
            message=f"Overlap ({overlap}) must be less than chunk_size ({chunk_size})",
            details={"overlap": overlap, "chunk_size": chunk_size}
        )
    
    valid_tokenizers = ["character", "word", "sentence"]
    if tokenizer_name not in valid_tokenizers:
        raise ValidationError(
            error_type="INVALID_TOKENIZER",
            message=f"Unknown tokenizer: {tokenizer_name}. Valid: {valid_tokenizers}",
            details={"tokenizer_name": tokenizer_name, "valid_tokenizers": valid_tokenizers}
        )
    
    logger.info(f"Ingestion config valid: chunk_size={chunk_size}, overlap={overlap}, tokenizer={tokenizer_name}")


def validate_document_for_ingestion(
    file_path: str,
    chunk_size: int = 200,
    overlap: int = 50,
    tokenizer_name: str = "character"
) -> Dict[str, Any]:
    """
    Complete validation pipeline for document ingestion.
    
    Args:
        file_path: Path to document
        chunk_size: Chunking size
        overlap: Chunk overlap
        tokenizer_name: Tokenizer name
    
    Returns:
        dict: Complete validation result with metadata
    
    Raises:
        ValidationError: If any validation step fails
    """
    logger.info(f"Starting validation pipeline for: {file_path}")
    
    # Step 1: File exists and accessible
    file_info = validate_file_exists(file_path)
    
    # Step 2: File size check
    validate_file_size(file_info["file_size_bytes"])
    
    # Step 3: PDF-specific validation
    if file_info["file_extension"] == ".pdf":
        pdf_info = validate_pdf(file_path)
        file_info.update(pdf_info)
    else:
        raise ValidationError(
            error_type="UNSUPPORTED_FILE_TYPE",
            message=f"Unsupported file type: {file_info['file_extension']}. Currently only PDF is supported.",
            details={"file_extension": file_info["file_extension"]}
        )
    
    # Step 4: Validate ingestion config
    validate_ingestion_config(chunk_size, overlap, tokenizer_name)
    
    file_info["chunking_config"] = {
        "chunk_size": chunk_size,
        "overlap": overlap,
        "tokenizer_name": tokenizer_name
    }
    
    logger.info(f"Validation pipeline complete for: {file_path}")
    return file_info
