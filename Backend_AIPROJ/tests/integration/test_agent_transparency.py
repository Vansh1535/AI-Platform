"""
Test script for decision transparency and user-facing messages.
Tests both standard and verbose modes.
"""
import requests
import json


BASE_URL = "http://127.0.0.1:8000"


def test_document_query_standard():
    """Test 1: Document query in standard mode (minimal meta)"""
    print("\n" + "="*60)
    print("TEST 1: Document Query (Standard Mode)")
    print("="*60)
    
    response = requests.post(f"{BASE_URL}/agent/run", json={
        "prompt": "What is in the document?",
        "max_iterations": 5
    })
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"\n📝 Answer: {result['answer'][:100]}...")
    print(f"💬 User Message: {result['user_message']}")
    print(f"📊 Meta (minimal): {json.dumps(result.get('meta', {}), indent=2)}")
    print(f"🔄 Iterations: {result['iterations']}")


def test_document_query_verbose():
    """Test 2: Document query in verbose mode (full agent_meta)"""
    print("\n" + "="*60)
    print("TEST 2: Document Query (Verbose Mode)")
    print("="*60)
    
    response = requests.post(f"{BASE_URL}/agent/run?verbose=true", json={
        "prompt": "What does the document say about experience?",
        "max_iterations": 5
    })
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"\n📝 Answer: {result['answer'][:100]}...")
    print(f"💬 User Message: {result['user_message']}")
    print(f"\n🔍 Agent Meta (Extended):")
    agent_meta = result.get('agent_meta', {})
    print(f"  - Decision Route: {agent_meta.get('decision_route')}")
    print(f"  - Reason: {agent_meta.get('reason')}")
    print(f"  - Tool Selected: {agent_meta.get('tool_selected')}")
    print(f"  - Tool Confidence: {agent_meta.get('tool_confidence')}")
    print(f"  - Alternatives Considered: {agent_meta.get('alternatives_considered')}")
    print(f"  - Provider Used: {agent_meta.get('provider_used')}")
    print(f"  - Latency (Agent Total): {agent_meta.get('latency_ms_agent_total')}ms")
    print(f"  - Latency (Tool Execution): {agent_meta.get('latency_ms_tool_execution')}ms")
    print(f"  - Fallback Triggered: {agent_meta.get('fallback_triggered')}")
    print(f"  - Safe Degraded Mode: {agent_meta.get('safe_degraded_mode')}")


def test_llm_query_verbose():
    """Test 3: LLM direct query in verbose mode"""
    print("\n" + "="*60)
    print("TEST 3: LLM Direct Query (Verbose Mode)")
    print("="*60)
    
    response = requests.post(f"{BASE_URL}/agent/run?verbose=true", json={
        "prompt": "What is 2+2?",
        "max_iterations": 5
    })
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"\n📝 Answer: {result['answer']}")
    print(f"💬 User Message: {result['user_message']}")
    print(f"\n🔍 Agent Meta (Extended):")
    agent_meta = result.get('agent_meta', {})
    print(f"  - Decision Route: {agent_meta.get('decision_route')}")
    print(f"  - Reason: {agent_meta.get('reason')}")
    print(f"  - Tool Selected: {agent_meta.get('tool_selected')}")
    print(f"  - Alternatives Considered: {agent_meta.get('alternatives_considered')}")
    print(f"  - Provider Used: {agent_meta.get('provider_used')}")
    print(f"  - Latency (Agent Total): {agent_meta.get('latency_ms_agent_total')}ms")
    print(f"  - Latency (LLM): {agent_meta.get('latency_ms_llm')}ms")


def test_ml_prediction_verbose():
    """Test 4: ML prediction in verbose mode"""
    print("\n" + "="*60)
    print("TEST 4: ML Prediction (Verbose Mode)")
    print("="*60)
    
    response = requests.post(f"{BASE_URL}/agent/run?verbose=true", json={
        "prompt": "Predict iris species for: 5.1, 3.5, 1.4, 0.2",
        "max_iterations": 5
    })
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"\n📝 Answer: {result['answer']}")
    print(f"💬 User Message: {result['user_message']}")
    print(f"\n🔍 Agent Meta (Extended):")
    agent_meta = result.get('agent_meta', {})
    print(f"  - Decision Route: {agent_meta.get('decision_route')}")
    print(f"  - Tool Selected: {agent_meta.get('tool_selected')}")
    print(f"  - Provider Used: {agent_meta.get('provider_used')}")
    print(f"  - Latency (Total): {agent_meta.get('latency_ms_agent_total')}ms")
    print(f"  - Latency (Tool): {agent_meta.get('latency_ms_tool_execution')}ms")
    print(f"  - Fallback Triggered: {agent_meta.get('fallback_triggered')}")


def main():
    print("\n" + "="*60)
    print("AGENT DECISION TRANSPARENCY - COMPREHENSIVE TEST")
    print("="*60)
    print("Testing new features:")
    print("  ✓ agent_meta with 15+ transparency fields")
    print("  ✓ user_message with graceful explanations")
    print("  ✓ verbose=true/false mode support")
    print("  ✓ Decision logging and instrumentation")
    
    try:
        test_document_query_standard()
        test_document_query_verbose()
        test_llm_query_verbose()
        test_ml_prediction_verbose()
        
        print("\n" + "="*60)
        print("✅ ALL TRANSPARENCY TESTS COMPLETED")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ TEST ERROR: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
