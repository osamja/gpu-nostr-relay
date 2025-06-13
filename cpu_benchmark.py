#!/usr/bin/env python3
"""
CPU-only benchmark for comparison with GPU-accelerated relay
This helps measure the performance benefits of GPU acceleration
"""

import asyncio
import websockets
import json
import hashlib
import time
import secrets
import statistics
from dataclasses import dataclass
from typing import List, Dict, Any

# Try to import secp256k1, fall back to basic crypto if not available
try:
    import secp256k1
    HAS_SECP256K1 = True
except ImportError:
    HAS_SECP256K1 = False
    print("⚠️  secp256k1 not available, using dummy signatures")

@dataclass
class CPUBenchmarkResult:
    """Container for CPU benchmark results"""
    test_name: str
    duration: float
    signatures_verified: int
    signatures_per_second: float
    
class CPUSignatureValidator:
    """CPU-only signature verification for comparison"""
    
    def __init__(self):
        pass
    
    def verify_signature(self, message_hash: bytes, signature: bytes, pubkey: bytes) -> bool:
        """Verify a single signature using CPU"""
        if not HAS_SECP256K1:
            # Simulate CPU work for testing
            time.sleep(0.0001)  # Simulate verification time
            return True
            
        try:
            pubkey_obj = secp256k1.PublicKey(pubkey, raw=True)
            return pubkey_obj.ecdsa_verify(message_hash, signature)
        except:
            return False
    
    def verify_batch_cpu(self, message_hashes: List[bytes], signatures: List[bytes], pubkeys: List[bytes]) -> List[bool]:
        """Verify signatures sequentially on CPU"""
        results = []
        for msg_hash, sig, pubkey in zip(message_hashes, signatures, pubkeys):
            results.append(self.verify_signature(msg_hash, sig, pubkey))
        return results

class CPUBenchmark:
    """CPU-only benchmark for comparison"""
    
    def __init__(self):
        self.validator = CPUSignatureValidator()
        self.results: List[CPUBenchmarkResult] = []
    
    def generate_test_data(self, count: int):
        """Generate test signature verification data"""
        data = []
        
        for i in range(count):
            if HAS_SECP256K1:
                # Generate real signature data
                private_key = secp256k1.PrivateKey()
                message = f"Test message {i}".encode()
                message_hash = hashlib.sha256(message).digest()
                signature = private_key.ecdsa_sign(message_hash, raw=True)
                pubkey = private_key.pubkey.serialize(compressed=False)[1:]  # Uncompressed pubkey without prefix
                
                data.append({
                    'message_hash': message_hash,
                    'signature': signature,
                    'pubkey': pubkey
                })
            else:
                # Generate dummy data for testing
                data.append({
                    'message_hash': secrets.token_bytes(32),
                    'signature': secrets.token_bytes(64),
                    'pubkey': secrets.token_bytes(64)
                })
        
        return data
    
    def benchmark_cpu_verification(self, batch_sizes: List[int] = [1, 10, 50, 100, 500, 1000]):
        """Benchmark CPU signature verification"""
        print("🔄 Benchmarking CPU signature verification...")
        
        for batch_size in batch_sizes:
            print(f"  Testing CPU batch size: {batch_size}")
            
            # Generate test data
            test_data = self.generate_test_data(batch_size)
            
            message_hashes = [d['message_hash'] for d in test_data]
            signatures = [d['signature'] for d in test_data]
            pubkeys = [d['pubkey'] for d in test_data]
            
            # Benchmark verification
            start_time = time.perf_counter()
            results = self.validator.verify_batch_cpu(message_hashes, signatures, pubkeys)
            end_time = time.perf_counter()
            
            duration = end_time - start_time
            signatures_per_second = batch_size / duration if duration > 0 else 0
            valid_count = sum(results)
            
            result = CPUBenchmarkResult(
                test_name=f"CPU Verification (batch_size={batch_size})",
                duration=duration,
                signatures_verified=batch_size,
                signatures_per_second=signatures_per_second
            )
            
            self.results.append(result)
            print(f"    ✅ {signatures_per_second:.1f} signatures/sec, {valid_count}/{batch_size} valid")
    
    def print_cpu_results(self):
        """Print CPU benchmark results"""
        print("\n" + "=" * 60)
        print("💻 CPU SIGNATURE VERIFICATION RESULTS")
        print("=" * 60)
        
        for result in self.results:
            print(f"\n📊 {result.test_name}")
            print(f"Duration: {result.duration:.4f}s")
            print(f"Signatures: {result.signatures_verified:,}")
            print(f"Rate: {result.signatures_per_second:.1f} signatures/sec")
        
        if self.results:
            max_cpu_rate = max(r.signatures_per_second for r in self.results)
            print(f"\n🎯 Peak CPU Performance: {max_cpu_rate:.1f} signatures/sec")

def main():
    """Run CPU benchmark"""
    print("💻 CPU-Only Signature Verification Benchmark")
    print("=" * 50)
    
    benchmark = CPUBenchmark()
    benchmark.benchmark_cpu_verification([1, 10, 50, 100, 500, 1000])
    benchmark.print_cpu_results()
    
    print("\n📝 To compare with GPU performance:")
    print("   1. Start your GPU relay: ./start_relay.sh")
    print("   2. Run: python benchmark_relay.py")
    print("   3. Compare the signature verification rates!")

if __name__ == "__main__":
    main() 