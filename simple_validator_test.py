#!/usr/bin/env python3
"""
Simple validator test without cuECC dependency
"""

import json
import hashlib
import secp256k1
import secrets

def verify_signature_simple(event_id_hex: str, signature_hex: str, pubkey_hex: str) -> bool:
    """Simple signature verification using secp256k1 library"""
    try:
        # Convert hex to bytes
        event_id = bytes.fromhex(event_id_hex)
        signature_bytes = bytes.fromhex(signature_hex)
        pubkey_bytes = bytes.fromhex(pubkey_hex)
        
        # Create PublicKey object - need to reconstruct from the 33-byte compressed format
        # The pubkey_hex is 32 bytes (x-coordinate), we need to add the 0x02 prefix
        pubkey_full = b'\x02' + pubkey_bytes
        pubkey = secp256k1.PublicKey(pubkey_full, raw=True)
        
        # Deserialize signature from compact format (64 bytes)
        signature = pubkey.ecdsa_deserialize_compact(signature_bytes)
        
        # Verify signature - note parameter order: (message, signature)
        return pubkey.ecdsa_verify(event_id, signature)
    except Exception as e:
        print(f"Verification error: {e}")
        return False

def create_valid_event():
    """Create a properly formatted Nostr event"""
    private_key = secp256k1.PrivateKey()
    public_key = private_key.pubkey.serialize(compressed=True)[1:]  # Remove prefix
    
    event = {
        "kind": 1,
        "created_at": 1749800000,
        "tags": [],
        "content": "Simple test event",
        "pubkey": public_key.hex(),
    }
    
    # Create event string for signing
    event_str = json.dumps([
        0,
        event["pubkey"],
        event["created_at"],
        event["kind"],
        event["tags"],
        event["content"]
    ], separators=(',', ':'), ensure_ascii=False)
    
    # Hash and sign
    event_hash = hashlib.sha256(event_str.encode()).digest()
    event["id"] = event_hash.hex()
    
    # Create signature
    signature = private_key.ecdsa_sign(event_hash)
    sig_compact = secp256k1.ffi.new("unsigned char[64]")
    result = secp256k1.lib.secp256k1_ecdsa_signature_serialize_compact(
        secp256k1.secp256k1_ctx, sig_compact, signature
    )
    
    if result:
        event["sig"] = bytes(sig_compact).hex()
    else:
        raise Exception("Failed to serialize signature")
    
    return event

def main():
    print("🔧 Simple Validator Test")
    print("=" * 30)
    
    # Create valid event
    event = create_valid_event()
    print(f"Created event ID: {event['id'][:16]}...")
    
    # Test our simple validator
    is_valid = verify_signature_simple(event["id"], event["sig"], event["pubkey"])
    print(f"Validation result: {is_valid}")
    
    if is_valid:
        print("✅ Our signature validation logic works!")
        
        # Now test with modified signature (should fail)
        bad_sig = event["sig"][:-2] + "00"  # Corrupt last byte
        is_valid_bad = verify_signature_simple(event["id"], bad_sig, event["pubkey"])
        print(f"Bad signature test: {is_valid_bad}")
        
        if not is_valid_bad:
            print("✅ Bad signature correctly rejected")
        else:
            print("❌ Bad signature incorrectly accepted")
    else:
        print("❌ Our signature validation has issues")
    
    return event

if __name__ == "__main__":
    main()