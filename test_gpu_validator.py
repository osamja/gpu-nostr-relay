#!/usr/bin/env python3
"""
Test the GPU validator in isolation to understand its behavior
"""

import asyncio
from gpu_validator import GpuSigValidator, verify_signature_cpu
import secp256k1
import hashlib
import secrets

class MockEvent:
    def __init__(self, event_id, sig, pubkey):
        self.id = event_id
        self.sig = sig
        self.pubkey = pubkey

def generate_valid_event():
    """Generate a valid event with real cryptographic signature"""
    private_key = secp256k1.PrivateKey()
    public_key = private_key.pubkey
    
    # Create event content
    event_content = {
        "id": "",
        "pubkey": public_key.serialize(compressed=False)[1:].hex(),  # Remove 0x04 prefix
        "created_at": 1234567890,
        "kind": 1,
        "tags": [],
        "content": "test message"
    }
    
    # Create event ID hash
    event_str = f'[0,"{event_content["pubkey"]}",{event_content["created_at"]},{event_content["kind"]},[],"{event_content["content"]}"]'
    event_id = hashlib.sha256(event_str.encode()).hexdigest()
    event_content["id"] = event_id
    
    # Sign the event
    signature = private_key.ecdsa_sign(bytes.fromhex(event_id))
    sig_hex = private_key.ecdsa_serialize_compact(signature).hex()
    
    return MockEvent(event_id, sig_hex, event_content["pubkey"])

def generate_invalid_event():
    """Generate an invalid event with wrong signature"""
    private_key = secp256k1.PrivateKey()
    public_key = private_key.pubkey
    
    event_id = secrets.token_hex(32)
    fake_sig = secrets.token_hex(64)
    pubkey = public_key.serialize(compressed=False)[1:].hex()
    
    return MockEvent(event_id, fake_sig, pubkey)

async def test_validator():
    print("🔬 Testing GPU Validator in Isolation")
    print("=" * 50)
    
    validator = GpuSigValidator()
    
    # Test 1: Empty batch
    print("📋 Test 1: Empty batch")
    result = await validator.validate([])
    print(f"   Result: {result}")
    assert result == [], "Empty batch should return empty list"
    print("   ✅ PASS")
    
    # Test 2: Single valid event
    print("\n📋 Test 2: Single valid event")
    valid_event = generate_valid_event()
    result = await validator.validate([valid_event])
    print(f"   Event ID: {valid_event.id[:16]}...")
    print(f"   Signature: {valid_event.sig[:16]}...")
    print(f"   Pubkey: {valid_event.pubkey[:16]}...")
    print(f"   Result: {result}")
    
    # Test individual function too
    cpu_result = verify_signature_cpu(valid_event.id, valid_event.sig, valid_event.pubkey)
    print(f"   CPU function result: {cpu_result}")
    
    # Test 3: Single invalid event
    print("\n📋 Test 3: Single invalid event")
    invalid_event = generate_invalid_event()
    result = await validator.validate([invalid_event])
    print(f"   Result: {result}")
    assert result == [False], "Invalid event should return [False]"
    print("   ✅ PASS")
    
    # Test 4: Mixed batch
    print("\n📋 Test 4: Mixed batch")
    mixed_events = [valid_event, invalid_event, generate_valid_event()]
    result = await validator.validate(mixed_events)
    print(f"   Events: {len(mixed_events)}")
    print(f"   Result: {result}")
    
    # Test 5: Large batch
    print("\n📋 Test 5: Large batch (100 events)")
    large_batch = []
    for i in range(50):
        large_batch.append(generate_valid_event())
    for i in range(50):
        large_batch.append(generate_invalid_event())
    
    result = await validator.validate(large_batch)
    print(f"   Events: {len(large_batch)}")
    print(f"   Valid results: {sum(result)}")
    print(f"   Invalid results: {len(result) - sum(result)}")
    
    print("\n🎯 Validator test complete!")

if __name__ == "__main__":
    asyncio.run(test_validator())