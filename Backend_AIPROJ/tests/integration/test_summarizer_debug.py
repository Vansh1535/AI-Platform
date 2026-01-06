"""Debug test - check what's in vector store and what we retrieve."""
import os
import sys
import tempfile
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

os.environ["LLM_PROVIDER"] = "none"
os.environ["RAG_ENABLED"] = "true"

from app.rag.retrieval.search import search
from app.ingestion.integration import ingest_multi_file

# Create test file
test_content = "Machine learning is amazing. Deep learning uses neural networks."

with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
    f.write(test_content)
    temp_path = f.name

try:
    print(f"[*] Ingesting: {temp_path}")
    ingest_result = ingest_multi_file(
        file_path=temp_path,
        source="ml_debug.txt",
        normalize=True,
        exists_policy="overwrite"  # Force re-ingest
    )
    
    doc_id = ingest_result['document_id']
    print(f"[+] Document ID: {doc_id}")
    print(f"[+] Chunks: {ingest_result.get('chunk_count', 0)}")
    
    # Now search
    print(f"\n[*] Searching for: 'machine learning'")
    results, telemetry = search("machine learning", top_k=10)
    
    print(f"\n[+] Found {len(results)} results")
    for i, chunk in enumerate(results):
        chunk_id = chunk.get("id", "unknown")
        score = chunk.get("score", 0)
        text = chunk.get("chunk", "")[:80]
        print(f"\n  [{i+1}] ID: {chunk_id}")
        print(f"      Score: {score:.3f}")
        print(f"      Text: {text}...")
        
finally:
    os.unlink(temp_path)
