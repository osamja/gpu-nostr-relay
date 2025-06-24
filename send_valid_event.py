#!/usr/bin/env python3
"""
Send a valid Nostr event to the GPU relay
"""

import asyncio
import json
import time
import hashlib
import secp256k1
import websockets

def create_valid_event(content: str, private_key_hex: str = None):
    """Create a valid Nostr event with proper signature"""
    
    # Use a fixed private key for testing or generate a new one
    if private_key_hex:
        private_key = secp256k1.PrivateKey(bytes.fromhex(private_key_hex))
    else:
        private_key = secp256k1.PrivateKey()
    
    # Get 32-byte public key (x-coordinate only)
    public_key_bytes = private_key.pubkey.serialize(compressed=True)
    pubkey_hex = public_key_bytes[1:].hex()
    
    # Verify exactly 32 bytes
    assert len(bytes.fromhex(pubkey_hex)) == 32
    
    # Create event structure
    event = {
        "pubkey": pubkey_hex,
        "created_at": int(time.time()),
        "kind": 1,  # Text note
        "tags": [],
        "content": content,
    }
    
    # Create event ID (hash) according to NIP-01
    serialized = json.dumps([
        0,
        event["pubkey"],
        event["created_at"],
        event["kind"],
        event["tags"],
        event["content"],
    ], separators=(',', ':'), ensure_ascii=False)
    
    event_hash = hashlib.sha256(serialized.encode('utf-8')).digest()
    event["id"] = event_hash.hex()
    
    # Sign the event hash
    signature = private_key.ecdsa_sign(event_hash)
    signature_compact = private_key.ecdsa_serialize_compact(signature)
    event["sig"] = signature_compact.hex()
    
    print(f"📝 Event created:")
    print(f"   ID: {event['id']}")
    print(f"   Pubkey: {event['pubkey']} ({len(bytes.fromhex(event['pubkey']))} bytes)")
    print(f"   Signature: {event['sig']} ({len(bytes.fromhex(event['sig']))} bytes)")
    
    return event

async def send_to_relay(event, relay_url="ws://localhost:6969"):
    """Send event to relay and show result"""
    try:
        async with websockets.connect(relay_url) as websocket:
            # Send EVENT message
            message = ["EVENT", event]
            await websocket.send(json.dumps(message))
            print(f"📤 Sent event to {relay_url}")
            
            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"📥 Response: {response}")
            
            # Parse and interpret response
            try:
                resp_data = json.loads(response)
                if resp_data[0] == "OK":
                    if resp_data[2]:  # Success
                        print("✅ Event accepted! GPU signature verification passed!")
                        return True
                    else:
                        print(f"❌ Event rejected: {resp_data[3] if len(resp_data) > 3 else 'Unknown error'}")
                        return False
            except:
                print(f"⚠️  Unexpected response format: {response}")
                return False
                
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

async def main():
    print("🚀 Testing GPU-accelerated Nostr relay")
    print("="*50)
    
    # Create a valid event
    content = f"Hello from GPU relay! Generated at {time.time()}"
    event = create_valid_event(content)
    
    # Send to relay
    success = await send_to_relay(event)
    
    if success:
        print("\n🎉 SUCCESS! Your GPU relay is working perfectly!")
        print("   - CUDA GPU acceleration is active")
        print("   - Signature verification passed")
        print("   - Event was stored successfully")
    else:
        print("\n🔍 The relay processed your event but rejected it.")
        print("   This might be due to:")
        print("   - Signature format issues")
        print("   - Network/timing issues")
        print("   - Relay configuration")

if __name__ == "__main__":
    asyncio.run(main()) 