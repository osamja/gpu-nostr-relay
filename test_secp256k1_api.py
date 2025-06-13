#!/usr/bin/env python3
"""
Test secp256k1 API to understand correct usage
"""

import secp256k1
import hashlib

def test_secp256k1_api():
    """Test the secp256k1 library API"""
    print("🔍 Testing secp256k1 API")
    print("=" * 30)
    
    # Create a private key
    private_key = secp256k1.PrivateKey()
    print(f"Private key created: {private_key.private_key[:8].hex()}...")
    
    # Get public key
    public_key = private_key.pubkey
    print(f"Public key type: {type(public_key)}")
    
    # Test message
    message = b"Hello, Nostr!"
    message_hash = hashlib.sha256(message).digest()
    
    # Sign the message
    signature = private_key.ecdsa_sign(message_hash)
    print(f"Signature type: {type(signature)}")
    print(f"Signature methods: {[m for m in dir(signature) if not m.startswith('_')]}")
    
    # Try to verify with the public key
    try:
        is_valid = public_key.ecdsa_verify(message_hash, signature)
        print(f"Direct verification: {is_valid}")
        
        if is_valid:
            print("✅ Basic sign/verify works")
        else:
            print("❌ Basic sign/verify failed")
            
    except Exception as e:
        print(f"Direct verification failed: {e}")
    
    # Try to serialize signature to compact format
    try:
        sig_compact = public_key.ecdsa_serialize_compact(signature)
        print(f"Compact signature length: {len(sig_compact)} bytes")
        print(f"Compact signature: {sig_compact[:16].hex()}...")
        
        # Try to deserialize and verify
        sig_deserialized = public_key.ecdsa_deserialize_compact(sig_compact)
        is_valid_2 = public_key.ecdsa_verify(message_hash, sig_deserialized)
        print(f"Serialize/deserialize verification: {is_valid_2}")
        
        if is_valid_2:
            print("✅ Compact serialization works")
            return sig_compact
        else:
            print("❌ Compact serialization failed")
            
    except Exception as e:
        print(f"Compact serialization failed: {e}")
        
    # Try alternative: serialize public key
    try:
        pubkey_serialized = public_key.serialize(compressed=True)
        print(f"Serialized pubkey length: {len(pubkey_serialized)} bytes")
        print(f"Serialized pubkey: {pubkey_serialized.hex()}")
        
        # Reconstruct public key from serialized form
        pubkey_reconstructed = secp256k1.PublicKey(pubkey_serialized, raw=True)
        is_valid_3 = pubkey_reconstructed.ecdsa_verify(message_hash, signature)
        print(f"Reconstructed pubkey verification: {is_valid_3}")
        
    except Exception as e:
        print(f"Pubkey reconstruction failed: {e}")

if __name__ == "__main__":
    test_secp256k1_api()