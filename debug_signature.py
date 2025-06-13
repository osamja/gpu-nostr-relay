#!/usr/bin/env python3
"""
Debug signature validation to understand the issue
"""

import json
import hashlib
import secp256k1
import secrets

def create_test_event():
    """Create a test event and validate it locally"""
    
    # Generate keys
    private_key = secp256k1.PrivateKey()
    public_key = private_key.pubkey.serialize(compressed=True)[1:]  # Remove prefix
    
    print(f"Private key: {private_key.private_key.hex()}")
    print(f"Public key: {public_key.hex()}")
    
    # Create event
    event = {
        "kind": 1,
        "created_at": 1749800000,  # Fixed timestamp for testing
        "tags": [],
        "content": "Debug test event",
        "pubkey": public_key.hex(),
    }
    
    # Create the canonical event string according to NIP-01
    event_str = json.dumps([
        0,
        event["pubkey"],
        event["created_at"],
        event["kind"],
        event["tags"],
        event["content"]
    ], separators=(',', ':'), ensure_ascii=False)
    
    print(f"Event string: {event_str}")
    
    # Hash the event
    event_hash = hashlib.sha256(event_str.encode()).digest()
    event["id"] = event_hash.hex()
    
    print(f"Event ID: {event['id']}")
    
    # Sign the event
    signature = private_key.ecdsa_sign(event_hash)
    sig_compact = secp256k1.ffi.new("unsigned char[64]")
    result = secp256k1.lib.secp256k1_ecdsa_signature_serialize_compact(
        secp256k1.secp256k1_ctx, sig_compact, signature
    )
    
    if result:
        event["sig"] = bytes(sig_compact).hex()
        print(f"Signature: {event['sig']}")
    else:
        raise Exception("Failed to serialize signature")
    
    # Verify signature locally
    print("\nLocal verification:")
    try:
        # Reconstruct verification data
        event_id = bytes.fromhex(event["id"])
        signature_bytes = bytes.fromhex(event["sig"]) 
        pubkey_bytes = bytes.fromhex(event["pubkey"])
        
        # Use the same private key to verify (since we have it)
        is_valid = private_key.pubkey.ecdsa_verify(event_id, private_key.ecdsa_sign(event_id))
        print(f"Direct verification with same key: {is_valid}")
        
        # Try manual verification with public key
        try:
            pubkey_obj = secp256k1.PublicKey(b'\x02' + pubkey_bytes, raw=True)
            signature_obj = secp256k1.Signature(signature_bytes, raw=True)
            is_valid_manual = pubkey_obj.verify(event_id, signature_obj, raw=True)
            print(f"Manual verification result: {is_valid_manual}")
        except Exception as e2:
            print(f"Manual verification failed: {e2}")
        
        print("✅ Basic signature creation works")
            
    except Exception as e:
        print(f"❌ Local verification failed: {e}")
    
    return event

def test_gpu_validator_directly():
    """Test our GPU validator code directly"""
    print("\n" + "="*50)
    print("Testing GPU validator directly")
    print("="*50)
    
    # Import our validator
    import sys
    sys.path.append('/home/samus/programming-projects/gpu-nostr-relay')
    
    from gpu_validator import verify_signature_cpu
    
    event = create_test_event()
    
    # Test our CPU fallback validator
    try:
        result = verify_signature_cpu(event["id"], event["sig"], event["pubkey"])
        print(f"GPU validator CPU fallback result: {result}")
        
        if result:
            print("✅ Our validator works correctly")
        else:
            print("❌ Our validator has an issue")
            
    except Exception as e:
        print(f"❌ GPU validator test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔍 Debugging Signature Validation")
    print("=" * 50)
    
    event = create_test_event()
    test_gpu_validator_directly()
    
    print(f"\nFinal event:")
    print(json.dumps(event, indent=2))