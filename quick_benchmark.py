#!/usr/bin/env python3
"""
Quick GPU signature verification benchmark
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
            content = f"Benchmark event {secrets.token_hex(8)}"
            
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

async def benchmark_signature_verification():
    """Quick signature verification benchmark"""
    print("🚀 Quick GPU Signature Verification Benchmark")
    print("=" * 50)
    
    generator = NostrEventGenerator()
    relay_url = "ws://localhost:6969"
    batch_sizes = [1, 10, 50, 100, 500]
    
    results = []
    
    for batch_size in batch_sizes:
        print(f"Testing batch size: {batch_size}")
        
        # Generate events
        events = [generator.create_event() for _ in range(batch_size)]
        
        try:
            async with websockets.connect(relay_url) as websocket:
                start_time = time.perf_counter()
                
                # Submit all events
                for event in events:
                    await websocket.send(json.dumps(["EVENT", event]))
                
                # Wait for responses
                responses = []
                for _ in range(batch_size):
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        responses.append(json.loads(response))
                    except asyncio.TimeoutError:
                        break
                
                end_time = time.perf_counter()
                duration = end_time - start_time
                
                # Count successful verifications
                accepted = sum(1 for resp in responses if len(resp) >= 3 and resp[2])
                events_per_second = batch_size / duration if duration > 0 else 0
                success_rate = accepted / batch_size if batch_size > 0 else 0
                
                results.append({
                    'batch_size': batch_size,
                    'duration': duration,
                    'events_per_second': events_per_second,
                    'success_rate': success_rate,
                    'accepted': accepted,
                    'total_responses': len(responses)
                })
                
                print(f"  ✅ {events_per_second:.1f} events/sec, {success_rate:.1%} success rate")
                
        except Exception as e:
            print(f"  ❌ Batch failed: {e}")
    
    # Print summary
    print("\n📊 GPU SIGNATURE VERIFICATION RESULTS")
    print("=" * 50)
    
    for result in results:
        print(f"Batch Size {result['batch_size']:4d}: {result['events_per_second']:8.1f} events/sec, "
              f"{result['success_rate']:5.1%} success, {result['duration']:.3f}s")
    
    if results:
        max_throughput = max(r['events_per_second'] for r in results)
        print(f"\n🎯 Peak GPU Performance: {max_throughput:.1f} events/sec")
        
        # Compare with CPU baseline
        cpu_peak = 2188298.7  # From previous CPU benchmark
        speedup = max_throughput / cpu_peak if cpu_peak > 0 else 0
        print(f"💻 CPU Baseline: {cpu_peak:.1f} signatures/sec")
        print(f"⚡ GPU vs CPU: {speedup:.3f}x")
        
        if speedup > 1.0:
            print("🎉 GPU acceleration detected!")
        else:
            print("⚠️  GPU performance lower than CPU - check implementation")

if __name__ == "__main__":
    try:
        asyncio.run(benchmark_signature_verification())
    except KeyboardInterrupt:
        print("\n⚠️  Benchmark interrupted")
    except Exception as e:
        print(f"❌ Benchmark failed: {e}")