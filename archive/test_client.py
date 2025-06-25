#!/usr/bin/env python3
"""
Simple Nostr client to test GPU relay
"""

import asyncio
import json
import time
import hashlib
import secp256k1
import websockets

def create_nostr_event(content: str, private_key_hex: str = None):
    """Create a proper Nostr event"""
    
    # Generate private key if not provided
    if private_key_hex:
        private_key = secp256k1.PrivateKey(bytes.fromhex(private_key_hex))
    else:
        private_key = secp256k1.PrivateKey()
    
    # Get public key (x-coordinate only - exactly 32 bytes)
    public_key_bytes = private_key.pubkey.serialize(compressed=True)
    pubkey_hex = public_key_bytes[1:].hex()  # Remove 0x02/0x03 prefix to get 32 bytes
    
    # Verify we have exactly 32 bytes (64 hex characters)
    assert len(bytes.fromhex(pubkey_hex)) == 32, f"Public key must be 32 bytes, got {len(bytes.fromhex(pubkey_hex))}"
    
    # Create event
    event = {
        "pubkey": pubkey_hex,
        "created_at": int(time.time()),
        "kind": 1,
        "tags": [],
        "content": content,
    }
    
    # Create event ID according to NIP-01
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
    
    # Sign the event
    signature = private_key.ecdsa_sign(event_hash)
    signature_compact = private_key.ecdsa_serialize_compact(signature)
    event["sig"] = signature_compact.hex()
    
    return event

async def send_event_to_relay(uri: str, event):
    """Send event to Nostr relay"""
    try:
        async with websockets.connect(uri) as websocket:
            # Send EVENT message
            msg = json.dumps(["EVENT", event])
            await websocket.send(msg)
            print(f"📤 Sent: {json.dumps(event, indent=2)}")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                print(f"📥 Response: {response}")
                
                # Parse response
                resp_data = json.loads(response)
                if resp_data[0] == "OK":
                    if resp_data[2]:  # success
                        print("✅ Event accepted by relay!")
                        return True
                    else:
                        print(f"❌ Event rejected: {resp_data[3] if len(resp_data) > 3 else 'Unknown error'}")
                        return False
                        
            except asyncio.TimeoutError:
                print("⏰ No response from relay")
                return False
                
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

async def test_relay(relay_url: str = "ws://localhost:6969"):
    """Test the relay with a simple event"""
    print(f"🧪 Testing relay at {relay_url}")
    
    # Create test event
    test_content = f"Hello from GPU relay test! Time: {time.time()}"
    event = create_nostr_event(test_content)
    
    print(f"📝 Created event with ID: {event['id']}")
    
    # Send to relay
    success = await send_event_to_relay(relay_url, event)
    
    if success:
        print("🎉 Test successful!")
    else:
        print("😞 Test failed")

if __name__ == "__main__":
    asyncio.run(test_relay()) 