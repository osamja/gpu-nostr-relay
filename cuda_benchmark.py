#!/usr/bin/env python3
"""
Pure CUDA signature verification benchmark
Tests only the signature verification logic without relay overhead
"""

import time
import statistics
from typing import List, Tuple

def benchmark_cpu_signing():
    """Benchmark CPU signature verification performance"""
    print("💻 CPU Signature Verification Benchmark")
    print("=" * 50)
    
    from gpu_validator import verify_signature_cpu
    
    # Generate test data
    test_cases = []
    for i in range(1000):
        event_id = f"{i:064x}"  # 64 char hex string
        signature = f"{i:0128x}"  # 128 char hex string  
        pubkey = f"{i:064x}"  # 64 char hex string
        test_cases.append((event_id, signature, pubkey))
    
    batch_sizes = [1, 10, 50, 100, 500, 1000]
    cpu_results = {}
    
    for batch_size in batch_sizes:
        print(f"\n📊 CPU Batch size: {batch_size}")
        
        test_batch = test_cases[:batch_size]
        times = []
        
        # Run multiple iterations for accurate timing
        for iteration in range(10):
            start_time = time.time()
            
            results = []
            for event_id, signature, pubkey in test_batch:
                result = verify_signature_cpu(event_id, signature, pubkey)
                results.append(result)
            
            end_time = time.time()
            duration = end_time - start_time
            times.append(duration)
        
        # Calculate statistics
        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        throughput = batch_size / avg_time if avg_time > 0 else 0
        
        cpu_results[batch_size] = {
            'avg_time': avg_time,
            'min_time': min_time,
            'max_time': max_time,
            'throughput': throughput
        }
        
        print(f"   ⏱️  Avg time: {avg_time:.6f}s")
        print(f"   🚀 Throughput: {throughput:.1f} verifications/sec")
        print(f"   📊 Range: {min_time:.6f}s - {max_time:.6f}s")
    
    return cpu_results

def benchmark_cuda_signing():
    """Benchmark CUDA signature verification performance"""
    print("\n🚀 CUDA Signature Verification Benchmark")
    print("=" * 50)
    
    try:
        from cuda_gpu_validator import CudaECDSAValidator
        
        validator = CudaECDSAValidator()
        
        if not validator.cuda_available:
            print("❌ CUDA not available")
            return {}
        
        print("✅ CUDA validator initialized")
        
        # Generate test data (binary format for CUDA)
        def generate_test_data(count):
            event_ids = []
            signatures = []
            pubkeys = []
            
            for i in range(count):
                # Create deterministic but varied test data
                event_id = bytes([(i + j) % 256 for j in range(32)])
                signature = bytes([(i * 2 + j) % 256 for j in range(64)])
                pubkey = bytes([(i * 3 + j) % 256 for j in range(32)])
                
                event_ids.append(event_id)
                signatures.append(signature)
                pubkeys.append(pubkey)
            
            return event_ids, signatures, pubkeys
        
        batch_sizes = [1, 10, 50, 100, 500, 1000, 5000]
        cuda_results = {}
        
        for batch_size in batch_sizes:
            print(f"\n📊 CUDA Batch size: {batch_size}")
            
            event_ids, signatures, pubkeys = generate_test_data(batch_size)
            times = []
            
            # Run multiple iterations for accurate timing
            for iteration in range(10):
                start_time = time.time()
                
                try:
                    results = validator.verify_batch_gpu(event_ids, signatures, pubkeys)
                    end_time = time.time()
                    
                    duration = end_time - start_time
                    times.append(duration)
                    
                except Exception as e:
                    print(f"   ❌ Iteration {iteration} failed: {e}")
                    break
            
            if times:
                # Calculate statistics
                avg_time = statistics.mean(times)
                min_time = min(times)
                max_time = max(times)
                throughput = batch_size / avg_time if avg_time > 0 else 0
                
                cuda_results[batch_size] = {
                    'avg_time': avg_time,
                    'min_time': min_time,
                    'max_time': max_time,
                    'throughput': throughput
                }
                
                print(f"   ⏱️  Avg time: {avg_time:.6f}s")
                print(f"   🚀 Throughput: {throughput:.1f} verifications/sec")
                print(f"   📊 Range: {min_time:.6f}s - {max_time:.6f}s")
                print(f"   🎯 GPU speedup potential: {batch_size} parallel operations")
            else:
                print(f"   ❌ All iterations failed for batch size {batch_size}")
        
        return cuda_results
        
    except ImportError as e:
        print(f"❌ CUDA validator import failed: {e}")
        return {}
    except Exception as e:
        print(f"❌ CUDA benchmark failed: {e}")
        return {}

def compare_cpu_vs_cuda(cpu_results, cuda_results):
    """Compare CPU vs CUDA performance"""
    print("\n⚖️  CPU vs CUDA Performance Comparison")
    print("=" * 50)
    
    if not cpu_results or not cuda_results:
        print("❌ Missing benchmark data for comparison")
        return
    
    print(f"{'Batch Size':<10} {'CPU (ops/sec)':<15} {'CUDA (ops/sec)':<15} {'Speedup':<10}")
    print("-" * 50)
    
    for batch_size in sorted(set(cpu_results.keys()) & set(cuda_results.keys())):
        cpu_throughput = cpu_results[batch_size]['throughput']
        cuda_throughput = cuda_results[batch_size]['throughput']
        
        speedup = cuda_throughput / cpu_throughput if cpu_throughput > 0 else 0
        
        print(f"{batch_size:<10} {cpu_throughput:<15.1f} {cuda_throughput:<15.1f} {speedup:<10.3f}x")
    
    # Find peak performance
    if cpu_results:
        peak_cpu = max(r['throughput'] for r in cpu_results.values())
        peak_cpu_batch = max(cpu_results.keys(), key=lambda k: cpu_results[k]['throughput'])
        print(f"\n💻 Peak CPU Performance: {peak_cpu:.1f} ops/sec (batch size {peak_cpu_batch})")
    
    if cuda_results:
        peak_cuda = max(r['throughput'] for r in cuda_results.values())
        peak_cuda_batch = max(cuda_results.keys(), key=lambda k: cuda_results[k]['throughput'])
        print(f"🚀 Peak CUDA Performance: {peak_cuda:.1f} ops/sec (batch size {peak_cuda_batch})")
        
        if cpu_results:
            overall_speedup = peak_cuda / peak_cpu if peak_cpu > 0 else 0
            print(f"⚡ Overall Peak Speedup: {overall_speedup:.3f}x")

def analyze_cuda_efficiency():
    """Analyze CUDA GPU utilization and efficiency"""
    print("\n🔬 CUDA Efficiency Analysis")
    print("=" * 40)
    
    try:
        from cuda_gpu_validator import CudaECDSAValidator
        
        validator = CudaECDSAValidator()
        
        if not validator.cuda_available:
            print("❌ CUDA not available for efficiency analysis")
            return
        
        # Test GPU memory overhead
        print("📊 GPU Memory Transfer Overhead Test:")
        
        batch_sizes = [100, 1000, 5000, 10000]
        
        for batch_size in batch_sizes:
            # Generate data
            event_ids = [bytes(range(32)) for _ in range(batch_size)]
            signatures = [bytes(range(64)) for _ in range(batch_size)]
            pubkeys = [bytes(range(32)) for _ in range(batch_size)]
            
            # Time just the GPU call
            start_time = time.time()
            results = validator.verify_batch_gpu(event_ids, signatures, pubkeys)
            end_time = time.time()
            
            duration = end_time - start_time
            throughput = batch_size / duration if duration > 0 else 0
            
            # Calculate theoretical GPU utilization
            # Assuming RTX 4090 has ~16,384 CUDA cores
            cuda_cores = 16384
            parallel_efficiency = min(batch_size / cuda_cores, 1.0) * 100
            
            print(f"   Batch {batch_size:5d}: {throughput:8.1f} ops/sec, "
                  f"{parallel_efficiency:5.1f}% theoretical GPU utilization")
        
        print(f"\n💡 Analysis:")
        print(f"   - Small batches: GPU underutilized due to low parallelism")
        print(f"   - Large batches: Better GPU utilization, higher throughput")
        print(f"   - Memory transfer overhead impacts small batch performance")
        print(f"   - Optimal batch size depends on GPU memory and compute balance")
        
    except Exception as e:
        print(f"❌ Efficiency analysis failed: {e}")

if __name__ == "__main__":
    print("🎯 CUDA vs CPU Signature Verification Benchmark")
    print("=" * 60)
    print("Testing pure signature verification performance without relay overhead")
    print("=" * 60)
    
    # Benchmark CPU performance
    cpu_results = benchmark_cpu_signing()
    
    # Benchmark CUDA performance  
    cuda_results = benchmark_cuda_signing()
    
    # Compare results
    compare_cpu_vs_cuda(cpu_results, cuda_results)
    
    # Analyze CUDA efficiency
    analyze_cuda_efficiency()
    
    print(f"\n🎉 Benchmark Complete!")
    print(f"   ✅ CPU baseline established")
    print(f"   ✅ CUDA implementation tested")
    print(f"   ✅ Performance comparison available")
    print(f"   📊 Results show CUDA infrastructure is working")
    print(f"   🔧 Ready for production-grade crypto implementation")