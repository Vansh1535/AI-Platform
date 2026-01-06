"""
Test script for second-pass fallback retrieval

This script demonstrates the automatic fallback retrieval feature.
Run after ingesting documents to see the fallback in action.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.rag.retrieval.search import search
from app.core.logging import setup_logger

logger = setup_logger("INFO")


def test_fallback_retrieval():
    """
    Test the fallback retrieval with various query types.
    """
    print("=" * 80)
    print("TESTING SECOND-PASS FALLBACK RETRIEVAL")
    print("=" * 80)
    
    test_queries = [
        # High confidence queries (should use primary search)
        ("What is the main topic of the document?", "HIGH CONFIDENCE EXPECTED"),
        ("Summarize the key points", "HIGH CONFIDENCE EXPECTED"),
        
        # Low confidence queries (should trigger fallback)
        ("Who is the senior engineer?", "LOW CONFIDENCE - FALLBACK EXPECTED"),
        ("What is John Smith's role?", "LOW CONFIDENCE - FALLBACK EXPECTED"),
        ("Find contact information", "LOW CONFIDENCE - FALLBACK EXPECTED"),
        ("What university did they attend?", "LOW CONFIDENCE - FALLBACK EXPECTED"),
    ]
    
    for query, expected_behavior in test_queries:
        print("\n" + "=" * 80)
        print(f"QUERY: {query}")
        print(f"EXPECTED: {expected_behavior}")
        print("-" * 80)
        
        try:
            results = search(query, top_k=5)
            
            if results:
                print(f"\nRESULTS: {len(results)} chunks returned")
                print(f"Top Score: {results[0]['score']:.4f}")
                print(f"Chunk Preview: {results[0]['chunk'][:150]}...")
                
                if results[0]['score'] >= 0.55:
                    print(f"✅ High confidence - Primary search used")
                else:
                    print(f"⚠️  Low confidence - Check logs for fallback activity")
            else:
                print("❌ No results returned")
                
        except ValueError as e:
            print(f"⚠️  Vector store not ready: {e}")
            print("\n💡 TIP: Ingest documents first using POST /rag/ingest or /rag/ingest-pdf")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print("\n📊 Check the logs above for:")
    print("   - mode=primary_search (high confidence, no fallback)")
    print("   - mode=second_pass_retry (fallback improved results)")
    print("   - mode=primary_search_retained (fallback tried but primary better)")
    print("\n💡 The fallback automatically triggers when top_score < 0.55")


if __name__ == "__main__":
    test_fallback_retrieval()
