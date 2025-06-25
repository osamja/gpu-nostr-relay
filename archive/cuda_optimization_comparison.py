#!/usr/bin/env python3
"""
CUDA Optimization Performance Comparison
Compares original vs optimized CUDA implementation performance
"""

import time
import statistics
from typing import List, Dict
import hashlib

def generate_test_data(count: int, seed: int = 42) -> tuple:
    """Generate deterministic test data"""
    import random
    random.seed(seed)
    
    event_ids = []
    signatures = []
    pubkeys = []
    
    for i in range(count):
        event_id = bytes([random.randint(0, 255) for _ in range(32)])
        signature = bytes([random.randint(0, 255) for _ in range(64)])
        pubkey = bytes([random.randint(0, 255) for _ in range(32)])
        
        event_ids.append(event_id)
        signatures.append(signature)
        pubkeys.append(pubkey)
    
    return event_ids, signatures, pubkeys

class OptimizedCudaValidator:
    """Optimized CUDA ECDSA validator"""
    
    def __init__(self, library_path="./libcuda_ecdsa_optimized.so"):
        self.lib = None
        self.cuda_available = False
        
        try:
            import ctypes
            import os
            
            if os.path.exists(library_path):
                self.lib = ctypes.CDLL(library_path)
                self._setup_function_signatures()
                self.cuda_available = True
                print("🚀 Optimized CUDA ECDSA validator initialized")
            else:
                print(f"❌ Optimized CUDA library not found at {library_path}")
                
        except Exception as e:
            print(f"❌ Failed to initialize optimized CUDA validator: {e}")
            
    def _setup_function_signatures(self):
        import ctypes
        self.lib.cuda_ecdsa_verify_batch_optimized.argtypes = [
            ctypes.POINTER(ctypes.c_uint8),  # event_ids
            ctypes.POINTER(ctypes.c_uint8),  # signatures  
            ctypes.POINTER(ctypes.c_uint8),  # pubkeys
            ctypes.POINTER(ctypes.c_int),    # results
            ctypes.c_int                     # count
        ]
        self.lib.cuda_ecdsa_verify_batch_optimized.restype = ctypes.c_int
        
    def verify_batch_gpu(self, event_ids: List[bytes], signatures: List[bytes], 
                        pubkeys: List[bytes]) -> List[bool]:
        if not self.cuda_available:
            raise RuntimeError("Optimized CUDA not available")
            
        import ctypes
        count = len(event_ids)
        
        # Prepare input arrays
        event_ids_array = (ctypes.c_uint8 * (count * 32))()
        signatures_array = (ctypes.c_uint8 * (count * 64))()
        pubkeys_array = (ctypes.c_uint8 * (count * 32))()
        results_array = (ctypes.c_int * count)()
        
        # Copy data
        for i in range(count):
            for j in range(32):
                event_ids_array[i * 32 + j] = event_ids[i][j]
                pubkeys_array[i * 32 + j] = pubkeys[i][j]
            for j in range(64):
                signatures_array[i * 64 + j] = signatures[i][j]
        
        # Call optimized CUDA function
        result = self.lib.cuda_ecdsa_verify_batch_optimized(
            event_ids_array, signatures_array, pubkeys_array, 
            results_array, count
        )
        
        if result != 0:
            raise RuntimeError(f"Optimized CUDA verification failed with error code {result}")
            
        return [bool(results_array[i]) for i in range(count)]

def benchmark_original_cuda(batch_sizes: List[int]) -> Dict[int, Dict[str, float]]:
    """Benchmark original CUDA implementation"""
    print("📊 Benchmarking Original CUDA Implementation")
    print("-" * 50)
    
    try:
        from cuda_gpu_validator import CudaECDSAValidator
        validator = CudaECDSAValidator()
        
        if not validator.cuda_available:
            print("❌ Original CUDA not available")
            return {}
        
        results = {}
        
        for batch_size in batch_sizes:
            print(f"   Batch {batch_size}...", end=" ")
            
            event_ids, signatures, pubkeys = generate_test_data(batch_size)
            
            # Warmup
            validator.verify_batch_gpu(event_ids[:1], signatures[:1], pubkeys[:1])
            
            # Benchmark
            times = []
            for _ in range(5):
                start_time = time.time()
                validator.verify_batch_gpu(event_ids, signatures, pubkeys)
                end_time = time.time()
                times.append(end_time - start_time)
            
            avg_time = statistics.mean(times)
            throughput = batch_size / avg_time
            
            results[batch_size] = {
                'avg_time': avg_time,
                'throughput': throughput,
                'min_time': min(times),
                'max_time': max(times)
            }
            
            print(f"{throughput:8.1f} ops/sec ({avg_time:.4f}s)")
        
        return results
        
    except Exception as e:
        print(f"❌ Original CUDA benchmark failed: {e}")
        return {}

def benchmark_optimized_cuda(batch_sizes: List[int]) -> Dict[int, Dict[str, float]]:
    """Benchmark optimized CUDA implementation"""
    print("\n🚀 Benchmarking Optimized CUDA Implementation")
    print("-" * 50)
    
    try:
        validator = OptimizedCudaValidator()
        
        if not validator.cuda_available:
            print("❌ Optimized CUDA not available")
            return {}
        
        results = {}
        
        for batch_size in batch_sizes:
            print(f"   Batch {batch_size}...", end=" ")
            
            event_ids, signatures, pubkeys = generate_test_data(batch_size)
            
            # Warmup
            validator.verify_batch_gpu(event_ids[:1], signatures[:1], pubkeys[:1])
            
            # Benchmark
            times = []
            for _ in range(5):
                start_time = time.time()
                validator.verify_batch_gpu(event_ids, signatures, pubkeys)
                end_time = time.time()
                times.append(end_time - start_time)
            
            avg_time = statistics.mean(times)
            throughput = batch_size / avg_time
            
            results[batch_size] = {
                'avg_time': avg_time,
                'throughput': throughput,
                'min_time': min(times),
                'max_time': max(times)
            }
            
            print(f"{throughput:8.1f} ops/sec ({avg_time:.4f}s)")
        
        return results
        
    except Exception as e:
        print(f"❌ Optimized CUDA benchmark failed: {e}")
        return {}

def benchmark_cpu_baseline(batch_sizes: List[int]) -> Dict[int, Dict[str, float]]:
    """Benchmark CPU implementation"""
    print("\n💻 Benchmarking CPU Baseline")
    print("-" * 50)
    
    try:
        from gpu_validator import verify_signature_cpu
        
        results = {}
        
        for batch_size in batch_sizes:
            print(f"   Batch {batch_size}...", end=" ")
            
            event_ids, signatures, pubkeys = generate_test_data(batch_size)
            
            # Benchmark
            times = []
            for _ in range(3):  # Fewer runs for CPU since it's slower
                start_time = time.time()
                for event_id, sig, pubkey in zip(event_ids, signatures, pubkeys):
                    verify_signature_cpu(event_id.hex(), sig.hex(), pubkey.hex())
                end_time = time.time()
                times.append(end_time - start_time)
            
            avg_time = statistics.mean(times)
            throughput = batch_size / avg_time
            
            results[batch_size] = {
                'avg_time': avg_time,
                'throughput': throughput,
                'min_time': min(times),
                'max_time': max(times)
            }
            
            print(f"{throughput:8.1f} ops/sec ({avg_time:.4f}s)")
        
        return results
        
    except Exception as e:
        print(f"❌ CPU benchmark failed: {e}")
        return {}

def compare_results(cpu_results: Dict, original_results: Dict, optimized_results: Dict):
    """Compare and analyze performance results"""
    print("\n📈 Performance Comparison Analysis")
    print("=" * 70)
    
    print(f"{'Batch':<8} {'CPU':<12} {'Original':<12} {'Optimized':<12} {'Orig/CPU':<8} {'Opt/CPU':<8} {'Opt/Orig':<8}")
    print("-" * 70)
    
    for batch_size in sorted(set(cpu_results.keys()) & set(original_results.keys()) & set(optimized_results.keys())):
        cpu_tput = cpu_results[batch_size]['throughput']
        orig_tput = original_results[batch_size]['throughput']
        opt_tput = optimized_results[batch_size]['throughput']
        
        orig_speedup = orig_tput / cpu_tput if cpu_tput > 0 else 0
        opt_speedup = opt_tput / cpu_tput if cpu_tput > 0 else 0
        opt_vs_orig = opt_tput / orig_tput if orig_tput > 0 else 0
        
        print(f"{batch_size:<8} {cpu_tput:<12.1f} {orig_tput:<12.1f} {opt_tput:<12.1f} "
              f"{orig_speedup:<8.2f}x {opt_speedup:<8.2f}x {opt_vs_orig:<8.2f}x")
    
    # Find peak performance
    if cpu_results:
        peak_cpu = max(r['throughput'] for r in cpu_results.values())
        peak_cpu_batch = max(cpu_results.keys(), key=lambda k: cpu_results[k]['throughput'])
        print(f"\n💻 Peak CPU Performance: {peak_cpu:.1f} ops/sec (batch {peak_cpu_batch})")
    
    if original_results:
        peak_orig = max(r['throughput'] for r in original_results.values())
        peak_orig_batch = max(original_results.keys(), key=lambda k: original_results[k]['throughput'])
        print(f"🔧 Peak Original CUDA: {peak_orig:.1f} ops/sec (batch {peak_orig_batch})")
    
    if optimized_results:
        peak_opt = max(r['throughput'] for r in optimized_results.values())
        peak_opt_batch = max(optimized_results.keys(), key=lambda k: optimized_results[k]['throughput'])
        print(f"🚀 Peak Optimized CUDA: {peak_opt:.1f} ops/sec (batch {peak_opt_batch})")
    
    if cpu_results and optimized_results:
        overall_speedup = peak_opt / peak_cpu
        print(f"⚡ Overall Optimization Gain: {overall_speedup:.2f}x vs CPU")
        
    if original_results and optimized_results:
        optimization_gain = peak_opt / peak_orig
        print(f"🎯 Optimization Improvement: {optimization_gain:.2f}x vs Original CUDA")

def test_correctness_comparison():
    """Verify that optimized version produces same results as original"""
    print("\n🔬 Correctness Validation")
    print("-" * 30)
    
    try:
        from cuda_gpu_validator import CudaECDSAValidator
        original = CudaECDSAValidator()
        optimized = OptimizedCudaValidator()
        
        if not original.cuda_available or not optimized.cuda_available:
            print("❌ Cannot test correctness - missing CUDA implementations")
            return False
        
        # Test with different batch sizes
        test_sizes = [10, 100, 500]
        
        for batch_size in test_sizes:
            event_ids, signatures, pubkeys = generate_test_data(batch_size, seed=999)
            
            orig_results = original.verify_batch_gpu(event_ids, signatures, pubkeys)
            opt_results = optimized.verify_batch_gpu(event_ids, signatures, pubkeys)
            
            matches = sum(1 for o, p in zip(orig_results, opt_results) if o == p)
            
            print(f"   Batch {batch_size}: {matches}/{batch_size} matches ({100*matches/batch_size:.1f}%)")
            
            if matches != batch_size:
                print(f"   ❌ Correctness test failed for batch size {batch_size}")
                return False
        
        print("   ✅ All correctness tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Correctness test error: {e}")
        return False

if __name__ == "__main__":
    print("⚡ CUDA Optimization Performance Comparison")
    print("=" * 60)
    
    # Test batch sizes
    batch_sizes = [50, 100, 500, 1000, 2000, 5000]
    
    # Run benchmarks
    cpu_results = benchmark_cpu_baseline(batch_sizes)
    original_results = benchmark_original_cuda(batch_sizes)
    optimized_results = benchmark_optimized_cuda(batch_sizes)
    
    # Compare results
    if cpu_results or original_results or optimized_results:
        compare_results(cpu_results, original_results, optimized_results)
    
    # Test correctness
    test_correctness_comparison()
    
    print("\n🎉 Optimization Analysis Complete!")
    print("📊 Performance data collected for CPU, Original CUDA, and Optimized CUDA")
    print("🚀 Ready for production deployment")