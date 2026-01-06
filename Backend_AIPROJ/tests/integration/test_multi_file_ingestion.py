"""
Tests for multi-file ingestion system.
Tests TXT, MD, DOCX, and CSV parsing and integration.
"""

import pytest
from pathlib import Path
import tempfile
import os
from app.ingestion.dispatcher import dispatch_file, detect_file_type, ParsedDocument
from app.ingestion.parser_txt import parse_txt
from app.ingestion.parser_md import parse_md
from app.ingestion.parser_csv import parse_csv
from app.ingestion.normalize import normalize_content, normalize_whitespace


class TestTxtParser:
    """Tests for TXT file parsing."""
    
    def test_parse_simple_txt(self):
        """Test parsing a simple TXT file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("Hello World!\nThis is a test document.\n\nIt has multiple lines.")
            temp_path = f.name
        
        try:
            result = parse_txt(temp_path, "test_source")
            
            assert isinstance(result, ParsedDocument)
            assert result.format == "txt"
            assert result.source_type == "document"
            assert "Hello World!" in result.text
            assert result.metadata["file_name"].endswith(".txt")
            assert result.metadata["line_count"] == 4
        finally:
            os.unlink(temp_path)
    
    def test_parse_empty_txt(self):
        """Test parsing an empty TXT file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("")
            temp_path = f.name
        
        try:
            with pytest.raises(Exception, match="empty"):
                parse_txt(temp_path, "test_source")
        finally:
            os.unlink(temp_path)
    
    def test_parse_unicode_txt(self):
        """Test parsing TXT with Unicode characters."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("Hello 世界! Привет мир! 🌍")
            temp_path = f.name
        
        try:
            result = parse_txt(temp_path, "test_source")
            
            assert "世界" in result.text
            assert "мир" in result.text
            assert "🌍" in result.text
        finally:
            os.unlink(temp_path)


class TestMdParser:
    """Tests for Markdown file parsing."""
    
    def test_parse_simple_md(self):
        """Test parsing a simple Markdown file."""
        content = """# Main Title

This is the introduction.

## Section 1

Content of section 1.

## Section 2

Content of section 2.
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name
        
        try:
            result = parse_md(temp_path, "test_source")
            
            assert isinstance(result, ParsedDocument)
            assert result.format == "md"
            assert result.source_type == "document"
            assert "Main Title" in result.text
            assert result.metadata["header_count"] == 3
            assert result.sections is not None
            assert len(result.sections) > 0
        finally:
            os.unlink(temp_path)
    
    def test_parse_md_without_headers(self):
        """Test parsing Markdown file without headers."""
        content = "Just plain text without headers.\nMultiple lines.\n"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name
        
        try:
            result = parse_md(temp_path, "test_source")
            
            assert result.metadata["header_count"] == 0
            assert result.sections is None  # No sections without headers
        finally:
            os.unlink(temp_path)
    
    def test_parse_md_with_code_blocks(self):
        """Test parsing Markdown with code blocks."""
        content = """# Code Example

Here's some code:

```python
def hello():
    print("Hello World!")
```

End of example.
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name
        
        try:
            result = parse_md(temp_path, "test_source")
            
            assert "```python" in result.text
            assert "def hello():" in result.text
        finally:
            os.unlink(temp_path)


class TestCsvParser:
    """Tests for CSV file parsing."""
    
    def test_parse_simple_csv(self):
        """Test parsing a simple CSV file."""
        content = """Name,Age,City
John Doe,30,New York
Jane Smith,25,San Francisco
Bob Johnson,35,Chicago
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8', newline='') as f:
            f.write(content)
            temp_path = f.name
        
        try:
            result = parse_csv(temp_path, "test_source")
            
            assert isinstance(result, ParsedDocument)
            assert result.format == "csv"
            assert result.source_type == "table"  # CSV is marked as table
            assert result.metadata["row_count"] == 3
            assert result.metadata["column_count"] == 3
            assert "Name" in result.metadata["columns"]
            assert "Age" in result.metadata["columns"]
            
            # Check projection contains schema info
            assert "Schema:" in result.text
            assert "Total Columns: 3" in result.text
            assert "Total Rows: 3" in result.text
            assert "Sample Data" in result.text
        finally:
            os.unlink(temp_path)
    
    def test_parse_csv_with_numeric_columns(self):
        """Test CSV with numeric columns."""
        content = """Product,Price,Quantity
Widget,10.50,100
Gadget,25.99,50
Tool,15.00,75
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8', newline='') as f:
            f.write(content)
            temp_path = f.name
        
        try:
            result = parse_csv(temp_path, "test_source")
            
            # Check column types
            assert result.metadata["column_types"]["Price"] == "numeric"
            assert result.metadata["column_types"]["Quantity"] == "numeric"
            assert result.metadata["column_types"]["Product"] == "text"
            
            # Check numeric summary in projection
            assert "Numeric Column Summary" in result.text
        finally:
            os.unlink(temp_path)
    
    def test_parse_csv_different_delimiter(self):
        """Test CSV with semicolon delimiter."""
        content = """Name;Age;City
John;30;NYC
Jane;25;SF
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8', newline='') as f:
            f.write(content)
            temp_path = f.name
        
        try:
            result = parse_csv(temp_path, "test_source")
            
            assert result.metadata["delimiter"] == ";"
            assert result.metadata["column_count"] == 3
        finally:
            os.unlink(temp_path)
    
    def test_parse_empty_csv(self):
        """Test parsing empty CSV."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8', newline='') as f:
            f.write("")
            temp_path = f.name
        
        try:
            with pytest.raises(Exception, match="empty"):
                parse_csv(temp_path, "test_source")
        finally:
            os.unlink(temp_path)


class TestDispatcher:
    """Tests for file type detection and dispatching."""
    
    def test_detect_txt_by_extension(self):
        """Test TXT detection by file extension."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            temp_path = f.name
        
        try:
            format_type, mime = detect_file_type(temp_path)
            assert format_type == "txt"
        finally:
            os.unlink(temp_path)
    
    def test_detect_md_by_extension(self):
        """Test MD detection by file extension."""
        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as f:
            temp_path = f.name
        
        try:
            format_type, mime = detect_file_type(temp_path)
            assert format_type == "md"
        finally:
            os.unlink(temp_path)
    
    def test_detect_csv_by_extension(self):
        """Test CSV detection by file extension."""
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            temp_path = f.name
        
        try:
            format_type, mime = detect_file_type(temp_path)
            assert format_type == "csv"
        finally:
            os.unlink(temp_path)
    
    def test_unsupported_file_type(self):
        """Test unsupported file type raises error."""
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError, match="Unsupported"):
                detect_file_type(temp_path)
        finally:
            os.unlink(temp_path)
    
    def test_dispatch_txt_file(self):
        """Test dispatching TXT file to correct parser."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("Test content")
            temp_path = f.name
        
        try:
            result = dispatch_file(temp_path, "test_source")
            
            assert result.format == "txt"
            assert "multi_file_ingest_v1" in result.metadata["ingestion_method"]
            assert "mime_type" in result.metadata
        finally:
            os.unlink(temp_path)


class TestNormalization:
    """Tests for content normalization."""
    
    def test_normalize_whitespace(self):
        """Test whitespace normalization."""
        text = "Hello    World\n\n\n\nNext   line"
        normalized = normalize_whitespace(text)
        
        assert "Hello World" in normalized
        assert normalized.count('\n') == 2  # Max 2 newlines
    
    def test_normalize_full_content(self):
        """Test full content normalization."""
        text = "Hello    World\n\n\n\nTest!!!\nEnd"
        normalized = normalize_content(text)
        
        assert len(normalized) <= len(text)
        assert normalized.strip() == normalized  # No leading/trailing whitespace
    
    def test_normalize_unicode(self):
        """Test Unicode normalization."""
        text = "ﬁle"  # Unicode ligature
        normalized = normalize_content(text, normalize_unicode_flag=True)
        
        assert "fi" in normalized  # Ligature expanded


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
