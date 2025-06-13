#!/usr/bin/env python3
"""
Simple test to verify relay connection and event generation
"""

import asyncio
import websockets
import json
import time

async def test_relay_connection():
    """Test basic relay connection"""
    print("🔍 Testing relay connection...")
    
    try:
        async with websockets.connect("ws://localhost:6969") as websocket:
            print("✅ Connected to relay")
            
            # Send a REQ message to get relay info
            req = json.dumps(["REQ", "test", {"kinds": [1], "limit": 1}])
            await websocket.send(req)
            print("📤 Sent REQ message")
            
            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"📥 Received: {response}")
            
            # Send close
            close_msg = json.dumps(["CLOSE", "test"])
            await websocket.send(close_msg)
            print("✅ Connection test successful")
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
    
    return True

async def main():
    success = await test_relay_connection()
    if success:
        print("🎉 Relay is working!")
    else:
        print("😞 Relay connection failed")

if __name__ == "__main__":
    asyncio.run(main())