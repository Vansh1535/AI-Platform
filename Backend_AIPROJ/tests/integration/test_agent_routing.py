"""
Test script for agent intent classification and forced RAG routing

This demonstrates the new intent-based routing where document-related
questions automatically use the RAG tool without LLM reasoning.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.workflows.simple_agent import SimpleAgent, classify_intent
from app.core.logging import setup_logger

logger = setup_logger("INFO")


def test_intent_classification():
    """
    Test the intent classifier with various prompts.
    """
    print("=" * 80)
    print("TESTING INTENT CLASSIFICATION")
    print("=" * 80)
    
    test_cases = [
        # Explicit document-related (should route to force_rag_tool)
        ("What is in the document?", "document_query"),
        ("Show me the resume details", "document_query"),
        ("Summarize the PDF content", "document_query"),
        ("According to the document, what is the name?", "document_query"),
        ("In the file, what is their role?", "document_query"),
        ("From the resume, what experience do they have?", "document_query"),
        ("The document says what about the company?", "document_query"),
        ("Who is mentioned in the document?", "document_query"),
        ("What information is in this file?", "document_query"),
        
        # Semantic patterns with document context (should route to force_rag_tool)
        ("Who is the senior engineer name?", "document_query"),  # Multiple patterns
        ("What is the person's role and title?", "document_query"),  # Multiple patterns
        
        # General questions (should route to llm_direct)
        ("What is 2 + 2?", "general_query"),
        ("Tell me a joke", "general_query"),
        ("How are you?", "general_query"),
        ("Explain quantum physics", "general_query"),
        ("Why is the sky blue?", "general_query"),
        ("Calculate the area of a circle", "general_query"),
        ("What does photosynthesis mean?", "general_query"),
        ("Compare Python and JavaScript", "general_query"),
        
        # ML prediction queries (should route to llm_direct)
        ("Predict iris with features 5.1, 3.5, 1.4, 0.2", "general_query"),
        
        # Ambiguous - should default to general to avoid false positives
        ("What is a good name for my project?", "general_query"),  # "name" but not document
        ("Tell me about machine learning", "general_query"),  # "about" but not document
    ]
    
    passed = 0
    failed = 0
    
    for prompt, expected in test_cases:
        result = classify_intent(prompt)
        status = "✅" if result == expected else "❌"
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"\n{status} Prompt: {prompt}")
        print(f"   Expected: {expected}, Got: {result}")
    
    print("\n" + "=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 80)


def test_agent_routing():
    """
    Test the agent with document and non-document queries.
    """
    print("\n\n" + "=" * 80)
    print("TESTING AGENT ROUTING")
    print("=" * 80)
    
    agent = SimpleAgent()
    
    test_prompts = [
        ("What is in the document?", "force_rag_tool"),
        ("According to the resume, what is their role?", "force_rag_tool"),
        ("What is 2 + 2?", "llm_direct"),
        ("Explain quantum physics", "llm_direct"),
    ]
    
    for prompt, expected_routing in test_prompts:
        print("\n" + "-" * 80)
        print(f"PROMPT: {prompt}")
        print(f"EXPECTED ROUTING: {expected_routing}")
        print("-" * 80)
        
        try:
            result = agent.run(prompt)
            actual_routing = result.get("routing", "unknown")
            status = "✅" if actual_routing == expected_routing else "❌"
            
            print(f"\n{status} ROUTING: {actual_routing}")
            print(f"ANSWER: {result['answer'][:200]}...")
            
            if result.get("trace"):
                print(f"TOOL CALLS: {len(result['trace'])}")
                for step in result['trace']:
                    print(f"  - {step.get('tool', 'N/A')}: {step.get('routing', 'N/A')}")
        
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print("\n📊 Check the logs above for:")
    print("   - Intent classification results")
    print("   - routing=force_rag_tool (document queries)")
    print("   - routing=llm_direct (non-document queries)")
    print("\n💡 Document queries now bypass LLM and go directly to RAG!")


if __name__ == "__main__":
    print("🧪 Testing Agent Intent Classification & Routing\n")
    
    # Test 1: Intent Classification
    test_intent_classification()
    
    # Test 2: Agent Routing
    test_agent_routing()
