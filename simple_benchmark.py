#!/usr/bin/env python3
"""
Simple benchmark to test event submission
"""

import asyncio
import websockets
import json
import secp256k1
import hashlib
import time
import secrets

async def create_and_send_event():
    """Create and send a single event to test the pipeline"""
    print("🔑 Creating test event...")
    
    # Generate key pair
    private_key = secp256k1.PrivateKey()
    public_key = private_key.pubkey.serialize(compressed=True)[1:]  # Remove prefix
    
    # Create event
    event = {
        "kind": 1,
        "created_at": int(time.time()),
        "tags": [],
        "content": f"Benchmark test {secrets.token_hex(4)}",
        "pubkey": public_key.hex(),
    }
    
    # Create event hash (Nostr format)
    event_str = json.dumps([
        0,
        event["pubkey"],
        event["created_at"],
        event["kind"],
        event["tags"],
        event["content"]
    ], separators=(',', ':'), ensure_ascii=False)
    
    event_hash = hashlib.sha256(event_str.encode()).digest()
    event["id"] = event_hash.hex()
    
    # Sign the event
    signature = private_key.ecdsa_sign(event_hash)
    sig_compact = secp256k1.ffi.new("unsigned char[64]")
    result = secp256k1.lib.secp256k1_ecdsa_signature_serialize_compact(
        secp256k1.secp256k1_ctx, sig_compact, signature
    )
    if result:
        event["sig"] = bytes(sig_compact).hex()
    else:
        raise Exception("Failed to serialize signature")
    
    print(f"📋 Event created: {event['id'][:16]}...")
    
    # Send to relay
    try:
        async with websockets.connect("ws://localhost:6969") as websocket:
            print("✅ Connected to relay")
            
            # Send EVENT message
            event_msg = json.dumps(["EVENT", event])
            await websocket.send(event_msg)
            print("📤 Sent event")
            
            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            print(f"📥 Response: {response}")
            
            return True
            
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

async def main():
    print("🚀 Simple GPU Relay Benchmark")
    print("=" * 40)
    
    success = await create_and_send_event()
    if success:
        print("✅ Event submission successful!")
    else:
        print("❌ Event submission failed!")

if __name__ == "__main__":
    asyncio.run(main())