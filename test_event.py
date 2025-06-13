#!/usr/bin/env python3
"""
Test event generation and validation
"""

import secp256k1
import json
import hashlib
import time
import secrets

def create_test_event():
    """Create a test event to debug signature generation"""
    print("🔑 Creating test event...")
    
    try:
        # Generate key pair
        private_key = secp256k1.PrivateKey()
        public_key = private_key.pubkey.serialize(compressed=True)[1:]  # Remove prefix
        print(f"📋 Public key: {public_key.hex()}")
        
        # Create event
        event = {
            "kind": 1,
            "created_at": int(time.time()),
            "tags": [],
            "content": f"Test event {secrets.token_hex(4)}",
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
        
        print(f"📝 Event string: {event_str}")
        
        event_hash = hashlib.sha256(event_str.encode()).digest()
        event["id"] = event_hash.hex()
        print(f"🏷️  Event ID: {event['id']}")
        
        # Sign the event
        signature = private_key.ecdsa_sign(event_hash)
        # Serialize signature to compact format (64 bytes)
        sig_compact = secp256k1.ffi.new("unsigned char[64]")
        result = secp256k1.lib.secp256k1_ecdsa_signature_serialize_compact(
            secp256k1.secp256k1_ctx, sig_compact, signature
        )
        if result:
            event["sig"] = bytes(sig_compact).hex()
        else:
            raise Exception("Failed to serialize signature")
        print(f"✏️  Signature: {event['sig']}")
        
        print("✅ Event created successfully!")
        return event
        
    except Exception as e:
        print(f"❌ Failed to create event: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    event = create_test_event()
    if event:
        print("\n📋 Final event:")
        print(json.dumps(event, indent=2))