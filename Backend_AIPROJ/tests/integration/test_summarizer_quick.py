"""Quick test for summarizer debugging."""
import os
import sys
import tempfile
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

os.environ["LLM_PROVIDER"] = "none"
os.environ["RAG_ENABLED"] = "true"

from app.tools.summarizer import summarize_document
from app.ingestion.integration import ingest_multi_file

# Create test file
test_content = """
Machine Learning Overview

Machine learning is a subset of artificial intelligence.
It involves training algorithms on datasets to make predictions.
Common applications include image recognition and natural language processing.
"""

with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
    f.write(test_content)
    temp_path = f.name

try:
    print(f"[*] Ingesting: {temp_path}")
    ingest_result = ingest_multi_file(
        file_path=temp_path,
        source="ml_test.txt",
        normalize=True
    )
    
    doc_id = ingest_result['document_id']
    print(f"[+] Ingested: {doc_id}, Chunks: {ingest_result.get('chunk_count', 0)}")
    
    print(f"\n[*] Summarizing...")
    summary, telemetry = summarize_document(
        document_id=doc_id,
        mode="auto",
        max_chunks=5
    )
    
    print(f"\n[+] Mode: {telemetry.get('mode_used')}, Chunks: {telemetry.get('chunks_used')}")
    print(f"[+] Confidence: {telemetry.get('confidence_top', 0):.3f}")
    print(f"\n[SUMMARY]\n{summary}\n")
    
    # Check content
    if 'Machine' in summary or 'machine' in summary or 'learning' in summary:
        print("[SUCCESS] Summary contains expected content")
    else:
        print("[FAIL] Summary missing expected content")
        print(f"  Looking for: Machine, learning")
        print(f"  Got summary length: {len(summary)}")
        
finally:
    os.unlink(temp_path)
