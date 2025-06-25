#!/usr/bin/env python3
"""
Database initialization script for nostr-relay
Creates the required database schema before starting the relay
"""

import asyncio
import sys
import os
from pathlib import Path

async def initialize_database():
    """Initialize the nostr-relay database schema"""
    try:
        print("🔧 Initializing nostr-relay database...")
        
        # Set up the configuration
        os.environ['NOSTR_RELAY_CONFIG'] = '/app/config.yaml'
        
        # Import after setting environment
        from nostr_relay.storage import get_storage
        
        # Get storage instance and initialize
        storage = get_storage()
        
        # Setup database schema
        await storage.setup()
        
        print("✅ Database schema initialized successfully")
        
        # Verify database was created
        db_path = Path("/data/nostr.sqlite3")
        if db_path.exists():
            print(f"✅ Database file created: {db_path} ({db_path.stat().st_size} bytes)")
        else:
            raise Exception("Database file was not created")
            
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main initialization function"""
    success = await initialize_database()
    
    if not success:
        print("❌ Failed to initialize database")
        sys.exit(1)
    
    print("🎉 Database initialization completed successfully")

if __name__ == "__main__":
    asyncio.run(main()) 