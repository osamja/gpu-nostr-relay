"""
GPU-accelerated signature validator for nostr-relay
Template showing recommended implementation patterns
"""

import ctypes
from ctypes import c_int, c_void_p, POINTER, c_ubyte, c_size_t
import secp256k1
from typing import List, Optional

class GpuSigValidator:
    """GPU-accelerated signature validator with fallback to CPU"""
    
    def __init__(self, library_path: Optional[str] = None):
        self.gpu_lib = None
        self.gpu_available = False
        
        if library_path:
            try:
                self.gpu_lib = ctypes.CDLL(library_path)
                self._setup_gpu_functions()
                self.gpu_available = True
                print(f"GPU acceleration enabled: {library_path}")
            except Exception as e:
                print(f"GPU library not available: {e}, falling back to CPU")
                self.gpu_available = False
    
    def _setup_gpu_functions(self):
        """Setup GPU library function signatures"""
        if not self.gpu_lib:
            return
            
        # Example function signatures for cuECC or similar library
        # These would need to be adjusted based on actual library API
        
        # Batch verification function (hypothetical)
        self.gpu_lib.batch_verify_signatures.argtypes = [
            POINTER(c_ubyte),  # event_ids (32 bytes each)
            POINTER(c_ubyte),  # signatures (64 bytes each)  
            POINTER(c_ubyte),  # pubkeys (32 bytes each)
            c_size_t,          # count
            POINTER(c_int)     # results array
        ]
        self.gpu_lib.batch_verify_signatures.restype = c_int
        
        # Initialize GPU context
        self.gpu_lib.init_gpu_context.argtypes = []
        self.gpu_lib.init_gpu_context.restype = c_int
        
        # Cleanup GPU context
        self.gpu_lib.cleanup_gpu_context.argtypes = []
        self.gpu_lib.cleanup_gpu_context.restype = None
        
        # Initialize GPU context
        result = self.gpu_lib.init_gpu_context()
        if result != 0:
            raise RuntimeError(f"Failed to initialize GPU context: {result}")
    
    def verify_signature_cpu(self, event_id_hex: str, signature_hex: str, pubkey_hex: str) -> bool:
        """CPU signature verification (current implementation)"""
        try:
            # Convert hex to bytes
            event_id = bytes.fromhex(event_id_hex)
            signature_bytes = bytes.fromhex(signature_hex)
            pubkey_bytes = bytes.fromhex(pubkey_hex)
            
            # Create PublicKey object - pubkey_hex is 32 bytes (x-coordinate), add 0x02 prefix for compressed format
            pubkey_full = b'\x02' + pubkey_bytes
            pubkey = secp256k1.PublicKey(pubkey_full, raw=True)
            
            # Deserialize signature from compact format (64 bytes)
            signature = pubkey.ecdsa_deserialize_compact(signature_bytes)
            
            # Verify signature - parameter order: (message, signature)
            return pubkey.ecdsa_verify(event_id, signature)
        except Exception:
            return False
    
    def verify_signatures_gpu_batch(self, events) -> List[bool]:
        """GPU batch signature verification"""
        if not self.gpu_available or not events:
            return []
        
        count = len(events)
        
        # Prepare input arrays
        event_ids = (c_ubyte * (32 * count))()
        signatures = (c_ubyte * (64 * count))()
        pubkeys = (c_ubyte * (32 * count))()
        results = (c_int * count)()
        
        # Fill input arrays
        for i, event in enumerate(events):
            try:
                # Copy event ID (32 bytes)
                event_id_bytes = bytes.fromhex(event.id)
                ctypes.memmove(ctypes.byref(event_ids, i * 32), event_id_bytes, 32)
                
                # Copy signature (64 bytes)
                sig_bytes = bytes.fromhex(event.sig)
                ctypes.memmove(ctypes.byref(signatures, i * 64), sig_bytes, 64)
                
                # Copy pubkey (32 bytes)
                pubkey_bytes = bytes.fromhex(event.pubkey)
                ctypes.memmove(ctypes.byref(pubkeys, i * 32), pubkey_bytes, 32)
                
            except Exception as e:
                print(f"Error preparing batch data for event {i}: {e}")
                return [False] * count
        
        # Call GPU batch verification
        try:
            result = self.gpu_lib.batch_verify_signatures(
                event_ids,
                signatures, 
                pubkeys,
                count,
                results
            )
            
            if result != 0:
                print(f"GPU batch verification failed: {result}")
                return [False] * count
                
            # Convert results to Python bool list
            return [bool(results[i]) for i in range(count)]
            
        except Exception as e:
            print(f"GPU batch verification error: {e}")
            return [False] * count
    
    async def validate(self, events) -> List[bool]:
        """
        Validate a batch of events using GPU acceleration when available
        Returns list[bool] aligned with events indicating validity
        """
        if not events:
            return []
        
        # Try GPU batch processing first
        if self.gpu_available and len(events) > 10:  # Use GPU for larger batches
            try:
                return self.verify_signatures_gpu_batch(events)
            except Exception as e:
                print(f"GPU validation failed, falling back to CPU: {e}")
        
        # Fallback to CPU verification
        results = []
        for event in events:
            try:
                is_valid = self.verify_signature_cpu(event.id, event.sig, event.pubkey)
                results.append(is_valid)
            except Exception:
                results.append(False)
        
        return results
    
    def __del__(self):
        """Cleanup GPU resources"""
        if self.gpu_available and self.gpu_lib:
            try:
                self.gpu_lib.cleanup_gpu_context()
            except:
                pass


def validate_signature(event, config=None):
    """
    Validator function for nostr-relay (single event validation)
    Raises StorageError if event is invalid, returns None if valid
    """
    from nostr_relay.storage.base import StorageError
    
    validator = GpuSigValidator()
    
    try:
        is_valid = validator.verify_signature_cpu(event.id, event.sig, event.pubkey)
        if not is_valid:
            raise StorageError("invalid: Bad signature")
    except Exception as e:
        raise StorageError(f"invalid: Signature validation error - {str(e)}")


# Global validator instance for batch processing
_gpu_validator = None

def get_gpu_validator(library_path: Optional[str] = None) -> GpuSigValidator:
    """Get or create global GPU validator instance"""
    global _gpu_validator
    if _gpu_validator is None:
        _gpu_validator = GpuSigValidator(library_path)
    return _gpu_validator