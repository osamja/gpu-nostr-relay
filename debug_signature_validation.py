#!/usr/bin/env python3
"""
Debug signature validation - step by step analysis
"""

import secp256k1
import hashlib
import json

def create_real_nostr_event():
    """Create a real Nostr event following the spec exactly"""
    private_key = secp256k1.PrivateKey()
    public_key = private_key.pubkey
    
    # Get the 32-byte x-coordinate (Nostr pubkey format)
    # Extract from the serialized public key (remove 0x04 prefix for uncompressed)
    pubkey_full = public_key.serialize(compressed=False)
    pubkey_hex = pubkey_full[1:33].hex()  # Skip 0x04 prefix, take x-coordinate
    
    # Create event data
    event_data = [
        0,                    # version
        pubkey_hex,          # pubkey 
        1234567890,          # created_at
        1,                   # kind
        [],                  # tags
        "Hello Nostr!"       # content
    ]
    
    # Serialize for hashing (exact JSON with no spaces)
    event_json = json.dumps(event_data, separators=(',', ':'), ensure_ascii=False)
    print(f"Event JSON: {event_json}")
    
    # Hash the event
    event_id = hashlib.sha256(event_json.encode('utf-8')).digest()
    event_id_hex = event_id.hex()
    
    # Sign the hash
    signature = private_key.ecdsa_sign(event_id)
    sig_hex = private_key.ecdsa_serialize_compact(signature).hex()
    
    return {
        'id': event_id_hex,
        'sig': sig_hex,
        'pubkey': pubkey_hex,
        'private_key': private_key
    }

def test_verification_steps(event):
    """Test each step of verification"""
    print("🔍 Step-by-step signature verification:")
    print(f"   Event ID: {event['id']}")
    print(f"   Signature: {event['sig']}")
    print(f"   Pubkey: {event['pubkey']}")
    
    try:
        # Step 1: Convert hex to bytes
        event_id_bytes = bytes.fromhex(event['id'])
        signature_bytes = bytes.fromhex(event['sig'])
        pubkey_bytes = bytes.fromhex(event['pubkey'])
        
        print(f"   ✅ Hex conversion successful")
        print(f"      Event ID bytes: {len(event_id_bytes)} bytes")
        print(f"      Signature bytes: {len(signature_bytes)} bytes") 
        print(f"      Pubkey bytes: {len(pubkey_bytes)} bytes")
        
        # Step 2: Create PublicKey - try different approaches
        approaches = [
            ("Compressed with 0x02 prefix", lambda: secp256k1.PublicKey(b'\x02' + pubkey_bytes, raw=True)),
            ("Compressed with 0x03 prefix", lambda: secp256k1.PublicKey(b'\x03' + pubkey_bytes, raw=True)),
            ("From private key", lambda: event['private_key'].pubkey)
        ]
        
        for name, func in approaches:
            try:
                pubkey_obj = func()
                print(f"   ✅ {name}: Created PublicKey")
                
                # Step 3: Deserialize signature
                try:
                    sig_obj = pubkey_obj.ecdsa_deserialize_compact(signature_bytes)
                    print(f"      ✅ Signature deserialized")
                    
                    # Step 4: Verify
                    is_valid = pubkey_obj.ecdsa_verify(event_id_bytes, sig_obj)
                    print(f"      ✅ Verification result: {is_valid}")
                    
                    if is_valid:
                        print(f"   🎉 SUCCESS with {name}")
                        return True
                        
                except Exception as e:
                    print(f"      ❌ Signature verification failed: {e}")
                    
            except Exception as e:
                print(f"   ❌ {name}: {e}")
        
        return False
        
    except Exception as e:
        print(f"   ❌ Hex conversion failed: {e}")
        return False

if __name__ == "__main__":
    print("🔬 Signature Validation Debug")
    print("=" * 50)
    
    # Create a real event
    event = create_real_nostr_event()
    
    # Test our current implementation
    from gpu_validator import verify_signature_cpu
    print(f"\n🧪 Current implementation result:")
    result = verify_signature_cpu(event['id'], event['sig'], event['pubkey'])
    print(f"   Result: {result}")
    
    # Debug step by step
    print(f"\n🔍 Detailed debugging:")
    test_verification_steps(event)