"""
PostgreSQL Database Setup Script

Run this script to set up the local PostgreSQL database for the RAG platform.
"""

import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env file
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from app.core.db import initialize_database, check_database_connection, get_database_stats
from app.core.logging import setup_logger

logger = setup_logger("INFO")


async def main():
    """Main setup function."""
    print("=" * 70)
    print("PostgreSQL Database Setup for RAG Platform")
    print("=" * 70)
    print()
    
    try:
        # Step 1: Initialize database
        print("Step 1: Initializing database connection...")
        await initialize_database()
        print("✅ Database initialized")
        print()
        
        # Step 2: Verify connection
        print("Step 2: Verifying database connection...")
        is_available, error = await check_database_connection()
        
        if not is_available:
            print(f"❌ Database connection failed: {error}")
            print()
            print("Troubleshooting:")
            print("1. Make sure PostgreSQL is installed and running")
            print("2. Check your .env file has correct database credentials:")
            print("   DB_HOST=localhost")
            print("   DB_PORT=5432")
            print("   DB_USER=postgres")
            print("   DB_PASS=postgres")
            print("   DB_NAME=rag_platform")
            print("3. Ensure the database 'rag_platform' exists:")
            print("   CREATE DATABASE rag_platform;")
            return 1
        
        print("✅ Database connection verified")
        print()
        
        # Step 3: Get database stats
        print("Step 3: Retrieving database statistics...")
        stats = await get_database_stats()
        
        print(f"  Pool Size: {stats.get('pool_size', 'unknown')}")
        print(f"  In Use: {stats.get('connections_in_use', 0)}")
        print(f"  Available: {stats.get('available_connections', 0)}")
        print()
        
        print("Table Counts:")
        for table, count in stats.get("table_counts", {}).items():
            print(f"  {table}: {count}")
        
        print()
        print("=" * 70)
        print("✅ Database setup complete!")
        print("=" * 70)
        print()
        print("You can now:")
        print("1. Start the application: python app/main.py")
        print("2. View documents: python scripts/db/list_documents.py")
        print("3. Query registry: python scripts/db/query_registry.py --help")
        print()
        
        return 0
        
    except Exception as e:
        print(f"❌ Setup failed: {str(e)}")
        print()
        print("Please check:")
        print("1. PostgreSQL is installed and running")
        print("2. Database 'rag_platform' exists")
        print("3. .env file has correct credentials")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
