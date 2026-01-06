"""
Checksum utilities for document duplicate detection.
Provides SHA-256 hashing for file integrity and duplicate prevention.
"""

import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
from app.core.logging import setup_logger

logger = setup_logger("INFO")


def compute_file_checksum(file_path: str, algorithm: str = "sha256") -> str:
    """
    Compute cryptographic checksum for a file.
    
    Args:
        file_path: Path to file
        algorithm: Hash algorithm (sha256, md5, sha1)
    
    Returns:
        str: Hexadecimal checksum hash
    
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If algorithm is unsupported
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Select hash algorithm
    if algorithm == "sha256":
        hasher = hashlib.sha256()
    elif algorithm == "md5":
        hasher = hashlib.md5()
    elif algorithm == "sha1":
        hasher = hashlib.sha1()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")
    
    # Read file in chunks to handle large files
    chunk_size = 8192
    
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    
    checksum = hasher.hexdigest()
    logger.info(f"Computed {algorithm} checksum: {checksum[:16]}... for {path.name}")
    
    return checksum


def check_duplicate_policy(
    checksum: str,
    registry,
    exists_policy: str = "skip"
) -> Dict[str, Any]:
    """
    Check if document exists and apply duplicate policy.
    
    Args:
        checksum: Document checksum hash
        registry: DocumentRegistry instance
        exists_policy: Policy to apply (skip/overwrite/version_as_new)
    
    Returns:
        dict: Policy decision with action and metadata
    """
    existing_docs = registry.find_by_checksum(checksum)
    
    if not existing_docs:
        logger.info(f"No existing document found for checksum: {checksum[:16]}...")
        return {
            "action": "ingest",
            "reason": "new_document",
            "existing_docs": []
        }
    
    logger.info(f"Found {len(existing_docs)} existing document(s) with checksum: {checksum[:16]}...")
    
    # Apply policy
    if exists_policy == "skip":
        logger.info(f"Policy: SKIP - Using existing document")
        return {
            "action": "skip",
            "reason": "duplicate_exists",
            "existing_docs": existing_docs,
            "existing_doc_id": existing_docs[0]["document_id"]
        }
    
    elif exists_policy == "overwrite":
        logger.info(f"Policy: OVERWRITE - Replacing existing document")
        return {
            "action": "overwrite",
            "reason": "policy_overwrite",
            "existing_docs": existing_docs,
            "existing_doc_id": existing_docs[0]["document_id"]
        }
    
    elif exists_policy == "version_as_new":
        logger.info(f"Policy: VERSION_AS_NEW - Creating new version")
        return {
            "action": "version_as_new",
            "reason": "policy_version",
            "existing_docs": existing_docs,
            "version": len(existing_docs) + 1
        }
    
    else:
        logger.warning(f"Unknown exists_policy: {exists_policy}, defaulting to skip")
        return {
            "action": "skip",
            "reason": "invalid_policy",
            "existing_docs": existing_docs
        }


def generate_document_id(filename: str, checksum: str, version: int = 1) -> str:
    """
    Generate deterministic document ID.
    
    Args:
        filename: Original filename
        checksum: Document checksum
        version: Version number
    
    Returns:
        str: Document ID (format: checksum[:8]-v{version})
    """
    # Use first 8 characters of checksum + version
    doc_id = f"{checksum[:8]}-v{version}"
    
    logger.info(f"Generated document ID: {doc_id} for {filename}")
    return doc_id


def verify_file_integrity(file_path: str, expected_checksum: str) -> bool:
    """
    Verify file integrity against expected checksum.
    
    Args:
        file_path: Path to file
        expected_checksum: Expected SHA-256 checksum
    
    Returns:
        bool: True if checksums match, False otherwise
    """
    actual_checksum = compute_file_checksum(file_path)
    
    if actual_checksum == expected_checksum:
        logger.info(f"File integrity verified: {file_path}")
        return True
    else:
        logger.error(f"File integrity check FAILED: {file_path}")
        logger.error(f"Expected: {expected_checksum}")
        logger.error(f"Actual: {actual_checksum}")
        return False
