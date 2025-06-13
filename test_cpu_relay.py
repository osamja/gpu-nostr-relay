#!/usr/bin/env python3
"""
Test CPU-only relay performance by running standard nostr-relay
"""

import asyncio
import websockets
import json
import hashlib
import time
import secrets
import secp256k1
import subprocess
import os
import signal

class NostrEventGenerator:
    def __init__(self):
        self.private_key = secp256k1.PrivateKey()
        self.public_key = self.private_key.pubkey.serialize(compressed=True)[1:]
        
    def create_event(self, content: str = None, kind: int = 1):
        if content is None:
            content = f"CPU test event {secrets.token_hex(8)}"
            
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

async def test_relay_throughput():
    """Test standard nostr-relay throughput"""
    print("🚀 CPU Relay Throughput Test")
    print("=" * 40)
    
    generator = NostrEventGenerator()
    relay_url = "ws://localhost:6969"
    
    # Test single event first
    print("Testing single event submission...")
    
    try:
        event = generator.create_event("Single test event")
        
        async with websockets.connect(relay_url) as websocket:
            await websocket.send(json.dumps(["EVENT", event]))
            
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            resp_data = json.loads(response)
            
            print(f"Response: {resp_data}")
            
            if len(resp_data) >= 3:
                success = resp_data[2]
                if success:
                    print("✅ Single event accepted")
                else:
                    print(f"❌ Single event rejected: {resp_data[3] if len(resp_data) > 3 else 'unknown reason'}")
            
    except Exception as e:
        print(f"❌ Single event test failed: {e}")
        return
    
    # Test small batch
    print("\nTesting small batch (5 events)...")
    
    try:
        events = [generator.create_event(f"Batch event {i}") for i in range(5)]
        
        async with websockets.connect(relay_url) as websocket:
            start_time = time.perf_counter()
            
            for event in events:
                await websocket.send(json.dumps(["EVENT", event]))
            
            responses = []
            for _ in range(5):
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    responses.append(json.loads(response))
                except asyncio.TimeoutError:
                    break
            
            end_time = time.perf_counter()
            duration = end_time - start_time
            
            accepted = sum(1 for resp in responses if len(resp) >= 3 and resp[2])
            throughput = 5 / duration if duration > 0 else 0
            
            print(f"✅ {accepted}/5 events accepted in {duration:.3f}s")
            print(f"📊 Throughput: {throughput:.1f} events/sec")
            
    except Exception as e:
        print(f"❌ Batch test failed: {e}")

def start_cpu_relay():
    """Start CPU-only relay"""
    print("🔄 Starting CPU-only relay...")
    
    env = os.environ.copy()
    env["HOST"] = "0.0.0.0"
    env["PORT"] = "6969"
    
    try:
        process = subprocess.Popen([
            "python3", "-m", "uvicorn", 
            "nostr_relay.asgi:app", 
            "--host", "0.0.0.0", 
            "--port", "6969"
        ], env=env)
        
        print(f"🚀 CPU relay started (PID: {process.pid})")
        print("⏳ Waiting for relay to be ready...")
        
        # Wait for relay to start
        time.sleep(3)
        
        return process
        
    except Exception as e:
        print(f"❌ Failed to start CPU relay: {e}")
        return None

async def main():
    """Main test function"""
    # Start CPU relay
    relay_process = start_cpu_relay()
    
    if not relay_process:
        return
    
    try:
        # Wait a bit more for startup
        await asyncio.sleep(2)
        
        # Test relay
        await test_relay_throughput()
        
    finally:
        # Cleanup
        print("\n🧹 Stopping CPU relay...")
        relay_process.terminate()
        relay_process.wait()
        print("✅ CPU relay stopped")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted")
    except Exception as e:
        print(f"❌ Test failed: {e}")