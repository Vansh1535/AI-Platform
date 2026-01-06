"""
Basic tests for ingestion pipeline enhancements.
Tests validation, duplicate detection, and metadata tracking.
"""

import pytest
import tempfile
import os
from pathlib import Path
from app.rag.ingestion.document_registry import DocumentRegistry
from app.rag.ingestion.validators import (
    validate_file_exists,
    validate_file_size,
    validate_ingestion_config,
    ValidationError
)
from app.rag.ingestion.checksum import (
    compute_file_checksum,
    check_duplicate_policy,
    generate_document_id
)


class TestDocumentRegistry:
    """Tests for document registry functionality."""
    
    def test_registry_initialization(self):
        """Test that registry initializes with SQLite database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_registry.db"
            registry = DocumentRegistry(db_path=db_path)
            
            assert db_path.exists()
            assert registry.db_path == db_path
    
    def test_register_ingestion_start(self):
        """Test registering the start of an ingestion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_registry.db"
            registry = DocumentRegistry(db_path=db_path)
            
            result = registry.register_ingestion_start(
                document_id="test-doc-123",
                filename="test.pdf",
                file_type="pdf",
                file_size_bytes=1024,
                checksum_hash="abc123" * 10,  # 64 char hash
                source_path="/tmp/test.pdf",
                chunk_size=200,
                overlap=50,
                exists_policy="skip"
            )
            
            assert result["document_id"] == "test-doc-123"
            assert result["status"] == "processing"
    
    def test_register_ingestion_success(self):
        """Test marking ingestion as successful."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_registry.db"
            registry = DocumentRegistry(db_path=db_path)
            
            # Start ingestion
            registry.register_ingestion_start(
                document_id="test-doc-123",
                filename="test.pdf",
                file_type="pdf",
                file_size_bytes=1024,
                checksum_hash="abc123" * 10,
                source_path="/tmp/test.pdf"
            )
            
            # Mark as successful
            result = registry.register_ingestion_success(
                document_id="test-doc-123",
                page_count=5,
                chunk_count=20,
                token_estimate=5000,
                processing_time_ms=1500
            )
            
            assert result["status"] == "success"
            assert result["chunk_count"] == 20
            
            # Verify metadata
            meta = registry.get_document_meta("test-doc-123")
            assert meta is not None
            assert meta["ingestion_status"] == "success"
            assert meta["chunk_count"] == 20
            assert meta["page_count"] == 5
    
    def test_find_by_checksum(self):
        """Test finding documents by checksum."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_registry.db"
            registry = DocumentRegistry(db_path=db_path)
            
            checksum = "abc123" * 10
            
            # Register document
            registry.register_ingestion_start(
                document_id="test-doc-123",
                filename="test.pdf",
                file_type="pdf",
                file_size_bytes=1024,
                checksum_hash=checksum,
                source_path="/tmp/test.pdf"
            )
            
            # Find by checksum
            docs = registry.find_by_checksum(checksum)
            assert len(docs) == 1
            assert docs[0]["document_id"] == "test-doc-123"
    
    def test_list_documents_with_health_summary(self):
        """Test listing documents with health summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_registry.db"
            registry = DocumentRegistry(db_path=db_path)
            
            # Add multiple documents
            for i in range(3):
                registry.register_ingestion_start(
                    document_id=f"doc-{i}",
                    filename=f"test-{i}.pdf",
                    file_type="pdf",
                    file_size_bytes=1024,
                    checksum_hash=f"hash{i}" * 10,
                    source_path=f"/tmp/test-{i}.pdf"
                )
                
                registry.register_ingestion_success(
                    document_id=f"doc-{i}",
                    page_count=5,
                    chunk_count=20,
                    token_estimate=5000,
                    processing_time_ms=1500
                )
            
            # List documents
            result = registry.list_documents()
            assert len(result["documents"]) == 3
            assert result["total_count"] == 3
            assert "health_summary" in result
            assert "success" in result["health_summary"]


class TestValidators:
    """Tests for validation utilities."""
    
    def test_validate_file_exists_success(self):
        """Test validation of existing file."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"test content")
            tmp_path = tmp.name
        
        try:
            result = validate_file_exists(tmp_path)
            assert result["filename"].endswith(".pdf")
            assert result["file_size_bytes"] > 0
            assert result["file_extension"] == ".pdf"
        finally:
            os.unlink(tmp_path)
    
    def test_validate_file_exists_not_found(self):
        """Test validation fails for non-existent file."""
        with pytest.raises(ValidationError) as exc_info:
            validate_file_exists("/nonexistent/file.pdf")
        
        assert exc_info.value.error_type == "FILE_NOT_FOUND"
    
    def test_validate_file_size_success(self):
        """Test file size validation with valid size."""
        validate_file_size(1024 * 1024)  # 1 MB - should pass
    
    def test_validate_file_size_too_small(self):
        """Test validation fails for too small file."""
        with pytest.raises(ValidationError) as exc_info:
            validate_file_size(10)  # Too small
        
        assert exc_info.value.error_type == "FILE_TOO_SMALL"
    
    def test_validate_file_size_too_large(self):
        """Test validation fails for too large file."""
        with pytest.raises(ValidationError) as exc_info:
            validate_file_size(100 * 1024 * 1024)  # 100 MB - too large
        
        assert exc_info.value.error_type == "FILE_TOO_LARGE"
    
    def test_validate_ingestion_config_success(self):
        """Test validation of valid ingestion config."""
        validate_ingestion_config(
            chunk_size=200,
            overlap=50,
            tokenizer_name="character"
        )
    
    def test_validate_ingestion_config_invalid_overlap(self):
        """Test validation fails when overlap >= chunk_size."""
        with pytest.raises(ValidationError) as exc_info:
            validate_ingestion_config(
                chunk_size=100,
                overlap=100,
                tokenizer_name="character"
            )
        
        assert exc_info.value.error_type == "INVALID_OVERLAP"


class TestChecksum:
    """Tests for checksum and duplicate detection."""
    
    def test_compute_file_checksum(self):
        """Test computing SHA-256 checksum."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test content")
            tmp_path = tmp.name
        
        try:
            checksum = compute_file_checksum(tmp_path)
            assert len(checksum) == 64  # SHA-256 hex length
            assert isinstance(checksum, str)
        finally:
            os.unlink(tmp_path)
    
    def test_compute_file_checksum_deterministic(self):
        """Test checksum is deterministic (same file = same hash)."""
        content = b"deterministic test content"
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp1:
            tmp1.write(content)
            tmp1_path = tmp1.name
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp2:
            tmp2.write(content)
            tmp2_path = tmp2.name
        
        try:
            checksum1 = compute_file_checksum(tmp1_path)
            checksum2 = compute_file_checksum(tmp2_path)
            assert checksum1 == checksum2
        finally:
            os.unlink(tmp1_path)
            os.unlink(tmp2_path)
    
    def test_check_duplicate_policy_skip(self):
        """Test skip policy returns existing document."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_registry.db"
            registry = DocumentRegistry(db_path=db_path)
            
            checksum = "abc123" * 10
            
            # Register existing document
            registry.register_ingestion_start(
                document_id="existing-doc",
                filename="test.pdf",
                file_type="pdf",
                file_size_bytes=1024,
                checksum_hash=checksum,
                source_path="/tmp/test.pdf"
            )
            
            # Check policy
            result = check_duplicate_policy(checksum, registry, "skip")
            assert result["action"] == "skip"
            assert result["reason"] == "duplicate_exists"
            assert len(result["existing_docs"]) == 1
    
    def test_check_duplicate_policy_version_as_new(self):
        """Test version_as_new policy creates new version."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_registry.db"
            registry = DocumentRegistry(db_path=db_path)
            
            checksum = "abc123" * 10
            
            # Register existing document
            registry.register_ingestion_start(
                document_id="existing-doc",
                filename="test.pdf",
                file_type="pdf",
                file_size_bytes=1024,
                checksum_hash=checksum,
                source_path="/tmp/test.pdf"
            )
            
            # Check policy
            result = check_duplicate_policy(checksum, registry, "version_as_new")
            assert result["action"] == "version_as_new"
            assert result["version"] == 2
    
    def test_generate_document_id_deterministic(self):
        """Test document ID generation is deterministic."""
        doc_id1 = generate_document_id("test.pdf", "abc123" * 10, 1)
        doc_id2 = generate_document_id("test.pdf", "abc123" * 10, 1)
        assert doc_id1 == doc_id2
        
        # Different versions should produce different IDs
        doc_id_v2 = generate_document_id("test.pdf", "abc123" * 10, 2)
        assert doc_id1 != doc_id_v2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
