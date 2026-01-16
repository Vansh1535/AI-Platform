"""
Quick runner for deployment readiness tests
Run with: python run_deployment_tests.py
"""

import subprocess
import sys
from pathlib import Path

def main():
    print("\n" + "="*70)
    print("🚀 STARTING AI PLATFORM DEPLOYMENT READINESS TESTS")
    print("="*70)
    print("\nThis will test:")
    print("  ✓ Backend health and connectivity")
    print("  ✓ Database operations")
    print("  ✓ Authentication flow")
    print("  ✓ Document upload (PDF, CSV, TXT)")
    print("  ✓ ChromaDB vector store")
    print("  ✓ RAG search and Q&A")
    print("  ✓ Document summarization")
    print("  ✓ CSV analytics")
    print("  ✓ Multi-document aggregation")
    print("  ✓ ML predictions")
    print("  ✓ Export reports")
    print("  ✓ Admin dashboard")
    print("  ✓ Error handling")
    print("  ✓ Performance benchmarks")
    print("  ✓ Security validation")
    print("\n" + "="*70 + "\n")
    
    # Run pytest
    test_file = Path(__file__).parent / "tests" / "test_deployment_ready.py"
    
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(test_file),
        "-v",
        "-s",
        "--tb=short",
        "--color=yes",
        "-W", "ignore::DeprecationWarning"
    ]
    
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent)
        
        print("\n" + "="*70)
        if result.returncode == 0:
            print("✅ ALL TESTS PASSED - DEPLOYMENT READY!")
        else:
            print("❌ SOME TESTS FAILED - REVIEW BEFORE DEPLOYMENT")
        print("="*70 + "\n")
        
        return result.returncode
    except Exception as e:
        print(f"\n❌ Error running tests: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
