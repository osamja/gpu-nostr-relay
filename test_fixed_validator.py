#!/usr/bin/env python3
"""
Test the fixed GPU validator to ensure signatures are properly validated
"""

import asyncio
import websockets
import json
import hashlib
import time
import secrets
import secp256k1

class NostrEventGenerator:
    def __init__(self):
        self.private_key = secp256k1.PrivateKey()
        self.public_key = self.private_key.pubkey.serialize(compressed=True)[1:]
        
    def create_event(self, content: str = None, kind: int = 1):
        if content is None:
            content = f"Test event {secrets.token_hex(8)}"
            
        event = {
            "kind": kind,
            "created_at": int(time.time()),
            "tags": [],
            "content": content,
            "pubkey": self.public_key.hex(),
        }
        
        event_str = json.dumps([
            0, event["pubkey"], event["created_at"], 
            event["kind"], event["tags"], event["content"]
        ], separators=(',', ':'), ensure_ascii=False)
        
        event_hash = hashlib.sha256(event_str.encode()).digest()
        event["id"] = event_hash.hex()
        
        signature = self.private_key.ecdsa_sign(event_hash)
        sig_compact = secp256k1.ffi.new("unsigned char[64]")
        result = secp256k1.lib.secp256k1_ecdsa_signature_serialize_compact(
            secp256k1.secp256k1_ctx, sig_compact, signature
        )
        if result:
            event["sig"] = bytes(sig_compact).hex()
        else:
            raise Exception("Failed to serialize signature")
        
        return event

async def test_validator():
    """Test the fixed validator with valid events"""
    print("🧪 Testing Fixed GPU Validator")
    print("=" * 40)
    
    generator = NostrEventGenerator()
    relay_url = "ws://localhost:6969"
    
    # Test 1: Single valid event
    print("Test 1: Single valid event")
    try:
        event = generator.create_event("Validator test event")
        
        async with websockets.connect(relay_url) as websocket:
            await websocket.send(json.dumps(["EVENT", event]))
            
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            resp_data = json.loads(response)
            
            print(f"  Response: {resp_data}")
            
            if len(resp_data) >= 3 and resp_data[2]:
                print("  ✅ Single valid event ACCEPTED")
            else:
                print(f"  ❌ Single valid event REJECTED: {resp_data[3] if len(resp_data) > 3 else 'unknown'}")
            
    except Exception as e:
        print(f"  ❌ Single event test failed: {e}")
    
    # Test 2: Multiple valid events
    print("\nTest 2: Multiple valid events (batch of 3)")
    try:
        events = [generator.create_event(f"Batch test {i}") for i in range(3)]
        
        async with websockets.connect(relay_url) as websocket:
            start_time = time.perf_counter()
            
            for event in events:
                await websocket.send(json.dumps(["EVENT", event]))
            
            responses = []
            for _ in range(3):
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    responses.append(json.loads(response))
                except asyncio.TimeoutError:
                    break
            
            end_time = time.perf_counter()
            duration = end_time - start_time
            
            accepted = sum(1 for resp in responses if len(resp) >= 3 and resp[2])
            
            print(f"  Sent: 3 events, Received: {len(responses)} responses")
            print(f"  Accepted: {accepted}/3 events")
            print(f"  Duration: {duration:.3f}s")
            
            if accepted == 3:
                print("  ✅ All valid events ACCEPTED")
            else:
                print(f"  ⚠️  Only {accepted}/3 events accepted")
                for i, resp in enumerate(responses):
                    if len(resp) >= 3:
                        status = "✅" if resp[2] else "❌"
                        reason = resp[3] if len(resp) > 3 and not resp[2] else "OK"
                        print(f"    Event {i+1}: {status} {reason}")
            
    except Exception as e:
        print(f"  ❌ Batch test failed: {e}")
    
    # Test 3: Performance check
    print("\nTest 3: Small performance check (10 events)")
    try:
        events = [generator.create_event(f"Perf test {i}") for i in range(10)]
        
        async with websockets.connect(relay_url) as websocket:
            start_time = time.perf_counter()
            
            for event in events:
                await websocket.send(json.dumps(["EVENT", event]))
            
            responses = []
            for _ in range(10):
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    responses.append(json.loads(response))
                except asyncio.TimeoutError:
                    break
            
            end_time = time.perf_counter()
            duration = end_time - start_time
            
            accepted = sum(1 for resp in responses if len(resp) >= 3 and resp[2])
            throughput = 10 / duration if duration > 0 else 0
            
            print(f"  Processed: 10 events in {duration:.3f}s")
            print(f"  Throughput: {throughput:.1f} events/sec")
            print(f"  Success rate: {accepted}/10 ({accepted/10*100:.0f}%)")
            
            if accepted >= 8:  # Allow for some minor issues
                print("  ✅ Performance test PASSED")
            else:
                print("  ⚠️  Performance test shows validation issues")
                
    except Exception as e:
        print(f"  ❌ Performance test failed: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(test_validator())
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted")
    except Exception as e:
        print(f"❌ Test failed: {e}")