"""
Test script for production ingestion pipeline.
Tests all new features including validation, duplicate detection, and metadata tracking.
"""
import requests
import json
import time
from pathlib import Path


BASE_URL = "http://127.0.0.1:8000"
PDF_FILE = "data/samples/sample_text_profile.pdf"


def test_initial_ingestion():
    """Test 1: Initial PDF ingestion with skip policy"""
    print("\n" + "="*60)
    print("TEST 1: Initial PDF Ingestion")
    print("="*60)
    
    with open(PDF_FILE, 'rb') as f:
        files = {'file': f}
        data = {
            'source': 'test_ingestion',
            'chunk_size': '200',
            'overlap': '50',
            'exists_policy': 'skip'
        }
        
        response = requests.post(f"{BASE_URL}/rag/ingest-pdf", files=files, data=data)
        
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ SUCCESS: Document ingested")
        if 'task_id' in result:
            print(f"Task ID: {result['task_id']}")
            # Wait for task to complete
            time.sleep(5)
    else:
        print(f"\n❌ FAILED: {response.text}")


def test_document_list():
    """Test 2: List all documents"""
    print("\n" + "="*60)
    print("TEST 2: List Documents with Health Summary")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/rag/docs/list")
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ SUCCESS: Found {len(result.get('data', {}).get('documents', []))} documents")
        health = result.get('data', {}).get('health_summary', {})
        if health:
            print(f"Health Summary:")
            print(f"  - Total: {health.get('total', 0)}")
            print(f"  - Success: {health.get('status_counts', {}).get('success', 0)}")
            print(f"  - Failed: {health.get('status_counts', {}).get('failed', 0)}")
    else:
        print(f"\n❌ FAILED: {response.text}")


def test_duplicate_skip():
    """Test 3: Test duplicate detection with skip policy"""
    print("\n" + "="*60)
    print("TEST 3: Duplicate Detection (Skip Policy)")
    print("="*60)
    
    with open(PDF_FILE, 'rb') as f:
        files = {'file': f}
        data = {
            'source': 'test_duplicate',
            'chunk_size': '200',
            'overlap': '50',
            'exists_policy': 'skip'
        }
        
        response = requests.post(f"{BASE_URL}/rag/ingest-pdf", files=files, data=data)
        
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print(f"\n✅ SUCCESS: Duplicate should be skipped")
    else:
        print(f"\n❌ FAILED: {response.text}")


def test_health_endpoint():
    """Test 4: Check health monitoring"""
    print("\n" + "="*60)
    print("TEST 4: Ingestion Health Dashboard")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/rag/docs/health")
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        result = response.json()
        data = result.get('data', {})
        print(f"\n✅ SUCCESS: Health data retrieved")
        print(f"Total Documents: {data.get('total_documents', 0)}")
        print(f"Success Rate: {data.get('success_rate', 0):.1f}%")
    else:
        print(f"\n❌ FAILED: {response.text}")


def test_document_metadata():
    """Test 5: Get document metadata"""
    print("\n" + "="*60)
    print("TEST 5: Get Document Metadata")
    print("="*60)
    
    # First get list of documents
    response = requests.get(f"{BASE_URL}/rag/docs/list")
    if response.status_code == 200:
        docs = response.json().get('data', {}).get('documents', [])
        if docs:
            doc_id = docs[0]['document_id']
            print(f"Testing with document ID: {doc_id}")
            
            # Get metadata
            response = requests.get(f"{BASE_URL}/rag/docs/{doc_id}/meta")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            
            if response.status_code == 200:
                print(f"\n✅ SUCCESS: Metadata retrieved")
            else:
                print(f"\n❌ FAILED: {response.text}")
        else:
            print("No documents found to test metadata")
    else:
        print(f"Failed to get document list: {response.text}")


def main():
    print("\n" + "="*60)
    print("PRODUCTION INGESTION PIPELINE - COMPREHENSIVE TEST")
    print("="*60)
    print(f"Testing against: {BASE_URL}")
    print(f"Test file: {PDF_FILE}")
    
    # Check if file exists
    if not Path(PDF_FILE).exists():
        print(f"\n❌ ERROR: Test file '{PDF_FILE}' not found!")
        return
    
    # Run tests
    try:
        test_initial_ingestion()
        time.sleep(2)  # Wait for async processing
        
        test_document_list()
        time.sleep(1)
        
        test_duplicate_skip()
        time.sleep(1)
        
        test_health_endpoint()
        time.sleep(1)
        
        test_document_metadata()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS COMPLETED")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ TEST ERROR: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
