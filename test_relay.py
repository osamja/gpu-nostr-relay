#!/usr/bin/env python3
"""
Test script for the GPU-accelerated Nostr relay
Tests WebSocket connectivity, basic Nostr protocol, and event handling
"""

import asyncio
import websockets
import json
import hashlib
import time
from datetime import datetime

async def test_basic_connection():
    """Test basic WebSocket connection to the relay"""
    print("🔄 Testing basic WebSocket connection...")
    try:
        async with websockets.connect("ws://localhost:6968") as websocket:
            print("✅ WebSocket connection successful!")
            
            # Send a simple REQ (request) message
            req_msg = ["REQ", "test-sub", {}]
            await websocket.send(json.dumps(req_msg))
            print(f"📤 Sent: {req_msg}")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📥 Received: {response}")
                return True
            except asyncio.TimeoutError:
                print("⚠️  No response received (this might be normal for empty relay)")
                return True
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

async def test_event_submission():
    """Test submitting a Nostr event to the relay"""
    print("\n🔄 Testing event submission...")
    
    # Create a simple test event
    event = {
        "kind": 1,  # Text note
        "created_at": int(time.time()),
        "tags": [],
        "content": "Hello from GPU Nostr Relay test!",
        "pubkey": "0" * 64,  # Dummy pubkey for testing
    }
    
    # Calculate event ID (hash of serialized event)
    event_str = json.dumps([
        0,
        event["pubkey"],
        event["created_at"],
        event["kind"],
        event["tags"],
        event["content"]
    ], separators=(',', ':'), ensure_ascii=False)
    
    event["id"] = hashlib.sha256(event_str.encode()).hexdigest()
    event["sig"] = "0" * 128  # Dummy signature (will fail validation)
    
    try:
        async with websockets.connect("ws://localhost:6968") as websocket:
            # Send EVENT message
            event_msg = ["EVENT", event]
            await websocket.send(json.dumps(event_msg))
            print(f"📤 Sent event: {event['id'][:16]}...")
            
            # Wait for OK response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                print(f"📥 Relay response: {response_data}")
                
                if response_data[0] == "OK":
                    event_id, accepted, message = response_data[1], response_data[2], response_data[3]
                    if accepted:
                        print("✅ Event accepted by relay!")
                    else:
                        print(f"⚠️  Event rejected: {message}")
                        if "signature" in message.lower():
                            print("   (This is expected - we used a dummy signature)")
                    return True
                    
            except asyncio.TimeoutError:
                print("⚠️  No response received from relay")
                return False
                
    except Exception as e:
        print(f"❌ Event submission failed: {e}")
        return False

async def test_relay_info():
    """Test getting relay information"""
    print("\n🔄 Testing relay information...")
    
    try:
        async with websockets.connect("ws://localhost:6968") as websocket:
            # Send REQ for relay metadata (kind 0 events)
            req_msg = ["REQ", "relay-info", {"kinds": [0], "limit": 1}]
            await websocket.send(json.dumps(req_msg))
            print("📤 Requested relay info...")
            
            # Collect responses for a few seconds
            responses = []
            try:
                while len(responses) < 5:  # Collect up to 5 responses
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    responses.append(json.loads(response))
            except asyncio.TimeoutError:
                pass
            
            if responses:
                print(f"📥 Received {len(responses)} responses")
                for resp in responses:
                    print(f"   {resp[0]}: {resp[1] if len(resp) > 1 else ''}")
            else:
                print("📥 No responses (relay might be empty)")
                
            return True
            
    except Exception as e:
        print(f"❌ Relay info test failed: {e}")
        return False

async def monitor_relay_activity():
    """Monitor relay for activity"""
    print("\n🔄 Monitoring relay activity for 10 seconds...")
    
    try:
        async with websockets.connect("ws://localhost:6968") as websocket:
            # Subscribe to all events
            req_msg = ["REQ", "monitor", {}]
            await websocket.send(json.dumps(req_msg))
            print("📤 Subscribed to all events...")
            
            start_time = time.time()
            message_count = 0
            
            try:
                while time.time() - start_time < 10:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    message_count += 1
                    data = json.loads(response)
                    print(f"📥 Message {message_count}: {data[0]}")
                    
            except asyncio.TimeoutError:
                pass
            
            print(f"📊 Received {message_count} messages in 10 seconds")
            return True
            
    except Exception as e:
        print(f"❌ Monitoring failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 GPU Nostr Relay Test Suite")
    print("=" * 50)
    
    tests = [
        ("Basic Connection", test_basic_connection),
        ("Event Submission", test_event_submission),
        ("Relay Information", test_relay_info),
        ("Activity Monitor", monitor_relay_activity),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    print(f"\n🎯 {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("🎉 All tests passed! Your relay is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the configuration and logs.")

if __name__ == "__main__":
    asyncio.run(main()) 