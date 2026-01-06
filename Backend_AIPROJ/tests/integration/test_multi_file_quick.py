"""
Quick test script for multi-file ingestion.
Tests TXT, MD, and CSV file ingestion.
"""

import sys
from pathlib import Path
import tempfile
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ingestion.dispatcher import dispatch_file
from app.ingestion.integration import ingest_multi_file


def test_txt_ingestion():
    """Test TXT file ingestion."""
    print("\n" + "="*60)
    print("TEST 1: TXT File Ingestion")
    print("="*60)
    
    # Create temp TXT file
    content = """Project Documentation

This document contains information about the project structure.

Key Features:
- Multi-file support
- Automatic chunking
- Vector embeddings
- RAG retrieval

The system supports PDF, TXT, MD, DOCX, and CSV files.
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(content)
        temp_path = f.name
    
    try:
        # Test parsing
        print(f"\n1. Parsing file: {Path(temp_path).name}")
        parsed = dispatch_file(temp_path, "test_doc")
        
        print(f"   ✓ Format: {parsed.format}")
        print(f"   ✓ Source Type: {parsed.source_type}")
        print(f"   ✓ Content Length: {len(parsed.text)} chars")
        print(f"   ✓ Metadata: {parsed.metadata}")
        
        print("\n   Content Preview:")
        print(f"   {parsed.text[:150]}...")
        
        print("\n✅ TXT ingestion test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ TXT ingestion test FAILED: {str(e)}")
        return False
    finally:
        os.unlink(temp_path)


def test_md_ingestion():
    """Test Markdown file ingestion."""
    print("\n" + "="*60)
    print("TEST 2: Markdown File Ingestion")
    print("="*60)
    
    # Create temp MD file
    content = """# Multi-File Ingestion System

## Overview

This system supports multiple file formats for RAG.

## Supported Formats

### Documents
- PDF (existing pipeline)
- TXT (plain text)
- MD (markdown)
- DOCX (Microsoft Word)

### Data Tables
- CSV (with intelligent projection)

## Features

Each format maintains:
- Checksum verification
- Duplicate detection
- Metadata tracking
- Vector embeddings
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
        f.write(content)
        temp_path = f.name
    
    try:
        # Test parsing
        print(f"\n1. Parsing file: {Path(temp_path).name}")
        parsed = dispatch_file(temp_path, "test_md")
        
        print(f"   ✓ Format: {parsed.format}")
        print(f"   ✓ Source Type: {parsed.source_type}")
        print(f"   ✓ Content Length: {len(parsed.text)} chars")
        print(f"   ✓ Headers: {parsed.metadata.get('header_count', 0)}")
        print(f"   ✓ Sections: {len(parsed.sections) if parsed.sections else 0}")
        
        if parsed.sections:
            print(f"\n   First Section Preview:")
            print(f"   {parsed.sections[0][:100]}...")
        
        print("\n✅ MD ingestion test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ MD ingestion test FAILED: {str(e)}")
        return False
    finally:
        os.unlink(temp_path)


def test_csv_ingestion():
    """Test CSV file ingestion with projection."""
    print("\n" + "="*60)
    print("TEST 3: CSV File Ingestion (with projection)")
    print("="*60)
    
    # Create temp CSV file
    content = """Name,Department,Salary,Years
Alice Johnson,Engineering,95000,5
Bob Smith,Marketing,72000,3
Carol Williams,Engineering,105000,8
David Brown,Sales,68000,2
Eve Davis,Engineering,88000,4
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8', newline='') as f:
        f.write(content)
        temp_path = f.name
    
    try:
        # Test parsing
        print(f"\n1. Parsing file: {Path(temp_path).name}")
        parsed = dispatch_file(temp_path, "employees")
        
        print(f"   ✓ Format: {parsed.format}")
        print(f"   ✓ Source Type: {parsed.source_type}")
        print(f"   ✓ Rows: {parsed.metadata['row_count']}")
        print(f"   ✓ Columns: {parsed.metadata['column_count']}")
        print(f"   ✓ Column Names: {', '.join(parsed.metadata['columns'])}")
        print(f"   ✓ Column Types: {parsed.metadata['column_types']}")
        
        print(f"\n   Projection Length: {len(parsed.text)} chars")
        print(f"\n   Projection Preview (first 400 chars):")
        print("   " + "-"*56)
        for line in parsed.text[:400].split('\n'):
            print(f"   {line}")
        print("   " + "-"*56)
        
        print("\n✅ CSV ingestion test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ CSV ingestion test FAILED: {str(e)}")
        return False
    finally:
        os.unlink(temp_path)


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("MULTI-FILE INGESTION TEST SUITE")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("TXT", test_txt_ingestion()))
    results.append(("MD", test_md_ingestion()))
    results.append(("CSV", test_csv_ingestion()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for format_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{format_name:10s} {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(main())
