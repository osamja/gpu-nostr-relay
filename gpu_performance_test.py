#!/usr/bin/env python3
"""
Simple GPU validation performance test
"""

import asyncio
import websockets
import json
import time
import statistics
from benchmark_relay import NostrEventGenerator

async def test_gpu_throughput():
    """Test GPU validation throughput"""
    print("🚀 GPU Validation Performance Test")
    print("=" * 50)
    
    gen = NostrEventGenerator()
    
    # Test different batch sizes
    batch_sizes = [1, 5, 10, 25, 50]
    results = {}
    
    for batch_size in batch_sizes:
        print(f"\n📊 Testing batch size: {batch_size}")
        
        # Generate events
        events = [gen.create_event(f"perf test {i}") for i in range(batch_size)]
        
        # Time the validation
        start_time = time.time()
        successful = 0
        
        try:
            async with websockets.connect('ws://localhost:6969') as ws:
                for event in events:
                    await ws.send(json.dumps(['EVENT', event]))
                    response = await ws.recv()
                    
                    resp_data = json.loads(response)
                    # Check if validation passed (even if storage failed)
                    if resp_data[0] == 'OK':
                        successful += 1
                        
        except Exception as e:
            print(f"❌ Error: {e}")
            continue
            
        end_time = time.time()
        duration = end_time - start_time
        
        if duration > 0:
            throughput = successful / duration
            results[batch_size] = {
                'events': successful,
                'duration': duration,
                'throughput': throughput
            }
            print(f"   ✅ {successful}/{batch_size} events validated")
            print(f"   ⏱️  Duration: {duration:.3f}s")
            print(f"   🚀 Throughput: {throughput:.1f} events/sec")
        else:
            print(f"   ❌ Too fast to measure")
    
    # Summary
    print(f"\n📈 GPU Validation Performance Summary")
    print("=" * 50)
    
    if results:
        max_throughput = max(r['throughput'] for r in results.values())
        best_batch = max(results.keys(), key=lambda k: results[k]['throughput'])
        
        print(f"🎯 Peak throughput: {max_throughput:.1f} events/sec")
        print(f"🏆 Best batch size: {best_batch}")
        
        for batch_size, data in results.items():
            print(f"   Batch {batch_size:2d}: {data['throughput']:6.1f} events/sec")
            
        return max_throughput
    else:
        print("❌ No successful measurements")
        return 0

if __name__ == "__main__":
    gpu_perf = asyncio.run(test_gpu_throughput())
    
    # Compare with CPU
    print(f"\n🏁 Performance Comparison")
    print("=" * 30)
    
    # Read CPU results
    try:
        with open('cpu_benchmark_results.txt', 'r') as f:
            content = f.read()
            # Extract peak CPU performance
            import re
            cpu_matches = re.findall(r'(\d+\.?\d*) signatures/sec', content)
            if cpu_matches:
                cpu_peak = max(float(m) for m in cpu_matches)
                print(f"💻 CPU Peak:  {cpu_peak:,.1f} signatures/sec")
                print(f"🚀 GPU Peak:  {gpu_perf:.1f} events/sec")
                
                if gpu_perf > 0:
                    ratio = gpu_perf / cpu_peak
                    print(f"⚡ Ratio:     {ratio:.6f}x")
                    
                    if ratio > 1:
                        print("🎉 GPU is faster!")
                    else:
                        print("💭 GPU needs optimization...")
                else:
                    print("❌ GPU measurement failed")
            else:
                print("❌ No CPU data found")
    except FileNotFoundError:
        print("❌ CPU benchmark file not found")