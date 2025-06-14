"""
CUDA GPU-accelerated ECDSA signature verification
"""

import ctypes
import os
import numpy as np
from typing import List, Tuple

class CudaECDSAValidator:
    """GPU-accelerated ECDSA signature validator using custom CUDA implementation"""
    
    def __init__(self, library_path="./libcuda_ecdsa.so"):
        """Initialize CUDA ECDSA validator"""
        self.lib = None
        self.cuda_available = False
        
        try:
            # Load the CUDA library
            if os.path.exists(library_path):
                self.lib = ctypes.CDLL(library_path)
                self._setup_function_signatures()
                self.cuda_available = True
                print("🚀 CUDA ECDSA validator initialized successfully")
            else:
                print(f"❌ CUDA library not found at {library_path}")
                
        except Exception as e:
            print(f"❌ Failed to initialize CUDA validator: {e}")
            
    def _setup_function_signatures(self):
        """Setup ctypes function signatures"""
        # cuda_ecdsa_verify_batch function signature
        self.lib.cuda_ecdsa_verify_batch.argtypes = [
            ctypes.POINTER(ctypes.c_uint8),  # event_ids
            ctypes.POINTER(ctypes.c_uint8),  # signatures  
            ctypes.POINTER(ctypes.c_uint8),  # pubkeys
            ctypes.POINTER(ctypes.c_int),    # results
            ctypes.c_int                     # count
        ]
        self.lib.cuda_ecdsa_verify_batch.restype = ctypes.c_int
        
    def verify_batch_gpu(self, event_ids: List[bytes], signatures: List[bytes], 
                        pubkeys: List[bytes]) -> List[bool]:
        """
        Verify batch of signatures using GPU
        
        Args:
            event_ids: List of 32-byte event ID hashes
            signatures: List of 64-byte signatures (32-byte r + 32-byte s)
            pubkeys: List of 32-byte public keys (x-coordinate)
            
        Returns:
            List of boolean verification results
        """
        if not self.cuda_available:
            raise RuntimeError("CUDA not available")
            
        count = len(event_ids)
        if count != len(signatures) or count != len(pubkeys):
            raise ValueError("Input arrays must have same length")
            
        if count == 0:
            return []
            
        # Prepare input arrays
        event_ids_array = (ctypes.c_uint8 * (count * 32))()
        signatures_array = (ctypes.c_uint8 * (count * 64))()
        pubkeys_array = (ctypes.c_uint8 * (count * 32))()
        results_array = (ctypes.c_int * count)()
        
        # Copy data to ctypes arrays
        for i in range(count):
            if len(event_ids[i]) != 32:
                raise ValueError(f"Event ID {i} must be 32 bytes")
            if len(signatures[i]) != 64:
                raise ValueError(f"Signature {i} must be 64 bytes")
            if len(pubkeys[i]) != 32:
                raise ValueError(f"Public key {i} must be 32 bytes")
                
            for j in range(32):
                event_ids_array[i * 32 + j] = event_ids[i][j]
                pubkeys_array[i * 32 + j] = pubkeys[i][j]
                
            for j in range(64):
                signatures_array[i * 64 + j] = signatures[i][j]
        
        # Call CUDA function
        result = self.lib.cuda_ecdsa_verify_batch(
            event_ids_array, signatures_array, pubkeys_array, 
            results_array, count
        )
        
        if result != 0:
            raise RuntimeError(f"CUDA verification failed with error code {result}")
            
        # Convert results to Python list
        return [bool(results_array[i]) for i in range(count)]

def verify_signature_gpu(event_id_hex: str, signature_hex: str, pubkey_hex: str) -> bool:
    """
    GPU signature verification function - compatible with existing interface
    """
    try:
        # Convert hex to bytes
        event_id = bytes.fromhex(event_id_hex)
        signature = bytes.fromhex(signature_hex)
        pubkey = bytes.fromhex(pubkey_hex)
        
        # Use global validator instance
        global _cuda_validator
        if '_cuda_validator' not in globals():
            _cuda_validator = CudaECDSAValidator()
            
        if not _cuda_validator.cuda_available:
            # Fallback to CPU
            from gpu_validator import verify_signature_cpu
            return verify_signature_cpu(event_id_hex, signature_hex, pubkey_hex)
        
        # Use GPU verification
        results = _cuda_validator.verify_batch_gpu([event_id], [signature], [pubkey])
        return results[0] if results else False
        
    except Exception as e:
        print(f"GPU verification error: {e}")
        # Fallback to CPU
        try:
            from gpu_validator import verify_signature_cpu
            return verify_signature_cpu(event_id_hex, signature_hex, pubkey_hex)
        except:
            return False

# Batch verification function for optimal GPU usage
def verify_signatures_batch_gpu(events_data: List[Tuple[str, str, str]]) -> List[bool]:
    """
    Batch GPU signature verification for optimal performance
    
    Args:
        events_data: List of (event_id_hex, signature_hex, pubkey_hex) tuples
        
    Returns:
        List of boolean verification results
    """
    if not events_data:
        return []
        
    try:
        global _cuda_validator
        if '_cuda_validator' not in globals():
            _cuda_validator = CudaECDSAValidator()
            
        if not _cuda_validator.cuda_available:
            # Fallback to CPU batch processing
            from gpu_validator import verify_signature_cpu
            return [verify_signature_cpu(event_id, sig, pubkey) 
                   for event_id, sig, pubkey in events_data]
        
        # Convert to bytes
        event_ids = [bytes.fromhex(event_id) for event_id, _, _ in events_data]
        signatures = [bytes.fromhex(sig) for _, sig, _ in events_data]
        pubkeys = [bytes.fromhex(pubkey) for _, _, pubkey in events_data]
        
        # GPU batch verification
        return _cuda_validator.verify_batch_gpu(event_ids, signatures, pubkeys)
        
    except Exception as e:
        print(f"Batch GPU verification error: {e}")
        # Fallback to CPU
        try:
            from gpu_validator import verify_signature_cpu
            return [verify_signature_cpu(event_id, sig, pubkey) 
                   for event_id, sig, pubkey in events_data]
        except:
            return [False] * len(events_data)

if __name__ == "__main__":
    # Test the CUDA validator
    print("🧪 Testing CUDA ECDSA validator...")
    
    validator = CudaECDSAValidator()
    
    if validator.cuda_available:
        print("✅ CUDA validator ready for testing")
        
        # Create test data
        test_event_id = b'a' * 32
        test_signature = b'b' * 64  
        test_pubkey = b'c' * 32
        
        try:
            results = validator.verify_batch_gpu(
                [test_event_id], [test_signature], [test_pubkey]
            )
            print(f"✅ Test verification result: {results[0]}")
        except Exception as e:
            print(f"❌ Test failed: {e}")
    else:
        print("❌ CUDA validator not available")