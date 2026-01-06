"""
Content normalization utilities.
Standardizes text content before chunking and embedding.
"""

import re
from typing import Optional
from app.core.logging import setup_logger

logger = setup_logger()


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text.
    - Replace multiple spaces with single space
    - Replace multiple newlines with double newline
    - Strip leading/trailing whitespace
    
    Args:
        text: Input text
        
    Returns:
        Normalized text
    """
    # Replace multiple spaces with single space
    text = re.sub(r' +', ' ', text)
    
    # Replace more than 2 newlines with exactly 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def remove_control_characters(text: str) -> str:
    """
    Remove control characters except newlines and tabs.
    
    Args:
        text: Input text
        
    Returns:
        Cleaned text
    """
    # Keep newlines, carriage returns, and tabs
    text = ''.join(char for char in text if char in '\n\r\t' or ord(char) >= 32)
    return text


def normalize_unicode(text: str) -> str:
    """
    Normalize Unicode characters to standard forms.
    
    Args:
        text: Input text
        
    Returns:
        Normalized text
    """
    import unicodedata
    
    # Normalize to NFKC form (compatibility composition)
    # This converts things like ﬁ -> fi, ¼ -> 1/4, etc.
    text = unicodedata.normalize('NFKC', text)
    
    return text


def remove_excessive_punctuation(text: str) -> str:
    """
    Clean up excessive punctuation while preserving meaningful usage.
    
    Args:
        text: Input text
        
    Returns:
        Cleaned text
    """
    # Replace multiple punctuation marks with single ones (except ...)
    text = re.sub(r'([!?]){2,}', r'\1', text)
    text = re.sub(r'(\.){4,}', '...', text)
    
    return text


def normalize_content(
    text: str,
    remove_control_chars: bool = True,
    normalize_whitespace_flag: bool = True,
    normalize_unicode_flag: bool = True,
    remove_punctuation: bool = False
) -> str:
    """
    Apply full content normalization pipeline.
    
    Args:
        text: Input text
        remove_control_chars: Remove non-printable control characters
        normalize_whitespace_flag: Normalize whitespace
        normalize_unicode_flag: Normalize Unicode characters
        remove_punctuation: Remove excessive punctuation
        
    Returns:
        Normalized text
    """
    if not text:
        return text
    
    original_length = len(text)
    
    # Apply normalization steps
    if remove_control_chars:
        text = remove_control_characters(text)
    
    if normalize_unicode_flag:
        text = normalize_unicode(text)
    
    if remove_punctuation:
        text = remove_excessive_punctuation(text)
    
    if normalize_whitespace_flag:
        text = normalize_whitespace(text)
    
    final_length = len(text)
    
    if original_length != final_length:
        logger.debug(
            f"Content normalized: {original_length} -> {final_length} chars "
            f"({final_length/original_length*100:.1f}%)"
        )
    
    return text


def truncate_text(text: str, max_length: int, add_ellipsis: bool = True) -> str:
    """
    Truncate text to maximum length while trying to break at word boundaries.
    
    Args:
        text: Input text
        max_length: Maximum length
        add_ellipsis: Add "..." to indicate truncation
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    # Try to break at last space before max_length
    truncate_at = max_length - 3 if add_ellipsis else max_length
    
    # Find last space
    last_space = text.rfind(' ', 0, truncate_at)
    
    if last_space > 0:
        truncated = text[:last_space]
    else:
        truncated = text[:truncate_at]
    
    if add_ellipsis:
        truncated += '...'
    
    return truncated
