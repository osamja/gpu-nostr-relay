#!/usr/bin/env python3
"""
Detailed cuECC library interface test
Based on analysis of the library symbols and GitHub repository
"""

import ctypes
import sys
from typing import List, Tuple

# Data structures based on the cuECC repository analysis
class CtypeUint256(ctypes.Array):
    """256-bit unsigned integer as array of 4 64-bit integers"""
    _type_ = ctypes.c_uint64
    _length_ = 4

class CtypePoint(ctypes.Structure):
    """Point structure with x, y coordinates as 256-bit integers"""
    _fields_ = [
        ("x", CtypeUint256),
        ("y", CtypeUint256)
    ]

class Point:
    """Python Point representation"""
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
    
    def __str__(self):
        return f"Point(x={hex(self.x)[:18]}..., y={hex(self.y)[:18]}...)"

def as_uint256(value: int) -> Tuple[int, int, int, int]:
    """Convert integer to tuple of 4 64-bit unsigned integers"""
    if value < 0:
        raise ValueError("Value must be non-negative")
    
    parts = []
    for i in range(4):
        parts.append(value & 0xFFFFFFFFFFFFFFFF)
        value >>= 64
    
    return tuple(parts)

def as_ctype_uint256(value: int) -> CtypeUint256:
    """Convert integer to CtypeUint256 array"""
    parts = as_uint256(value)
    arr = CtypeUint256()
    for i, part in enumerate(parts):
        arr[i] = part
    return arr

def as_python_int(arr: CtypeUint256) -> int:
    """Convert CtypeUint256 array back to Python integer"""
    result = 0
    for i in range(3, -1, -1):  # Start from most significant part
        result = (result << 64) | arr[i]
    return result

def test_cuecc_api():
    """Test the cuECC library API based on discovered functions"""
    print("🔍 Testing cuECC Library API")
    print("=" * 40)
    
    try:
        # Load the library
        lib = ctypes.CDLL("/usr/local/lib/libcuecc.so")
        print("✅ Successfully loaded libcuecc.so")
        
        # Set up the function signature based on the header analysis
        # extern "C" void getPublicKeyByPrivateKey(Point output[], u64 privateKeys[][4], int n);
        func = lib.getPublicKeyByPrivateKey
        func.argtypes = [
            ctypes.POINTER(CtypePoint),     # Point output[]
            ctypes.POINTER(CtypeUint256),   # u64 privateKeys[][4]  
            ctypes.c_int                    # int n
        ]
        func.restype = None  # void return type
        
        print("✅ Function signature configured")
        
        # Test with a few private keys
        test_private_keys = [
            0x1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF,
            0xFEDCBA0987654321FEDCBA0987654321FEDCBA0987654321FEDCBA0987654321,
            0x0000000000000000000000000000000000000000000000000000000000000001
        ]
        
        n = len(test_private_keys)
        print(f"🧪 Testing with {n} private keys")
        
        # Prepare input arrays
        private_keys_array = (CtypeUint256 * n)()
        for i, pk in enumerate(test_private_keys):
            private_keys_array[i] = as_ctype_uint256(pk)
            print(f"   Private key {i}: {hex(pk)[:18]}...")
        
        # Prepare output array
        output_points = (CtypePoint * n)()
        
        print("🚀 Calling getPublicKeyByPrivateKey...")
        
        # Call the function
        func(output_points, private_keys_array, n)
        
        print("✅ Function call completed successfully!")
        
        # Extract and display results
        results = []
        for i in range(n):
            x = as_python_int(output_points[i].x)
            y = as_python_int(output_points[i].y)
            point = Point(x, y)
            results.append(point)
            print(f"   Result {i}: {point}")
        
        # Verify results are non-zero (basic sanity check)
        all_valid = True
        for i, point in enumerate(results):
            if point.x == 0 and point.y == 0:
                print(f"❌ Result {i} is zero point - may indicate error")
                all_valid = False
        
        if all_valid:
            print("✅ All results appear valid (non-zero points)")
        
        return True, results
        
    except OSError as e:
        print(f"❌ Failed to load library: {e}")
        return False, []
    except Exception as e:
        print(f"❌ Error during API test: {e}")
        import traceback
        traceback.print_exc()
        return False, []

def test_signature_verification_approach():
    """
    Analyze what we know about signature verification with cuECC
    """
    print("\n🔍 Signature Verification Analysis")
    print("=" * 40)
    
    print("Based on cuECC repository analysis:")
    print("✅ cuECC provides: getPublicKeyByPrivateKey()")
    print("✅ Purpose: Batch public key generation")
    print("✅ GPU acceleration: CUDA kernels")
    print("❌ Direct signature verification: NOT FOUND")
    
    print("\nFor signature verification, we would need:")
    print("1. ECDSA signature verification function")
    print("2. Message hash input support")
    print("3. Batch verification capability")
    
    print("\nCurrent cuECC library appears to be focused on:")
    print("- Public key generation from private keys")
    print("- Basic elliptic curve point operations")
    print("- Educational/research purposes (not production)")
    
    print("\n⚠️  IMPORTANT: cuECC may not provide signature verification!")
    print("   Consider using it for key generation only, or look for")
    print("   additional functions in updated versions.")

def main():
    """Main test function"""
    success, results = test_cuecc_api()
    test_signature_verification_approach()
    
    if success:
        print(f"\n🎉 cuECC API test successful! Generated {len(results)} public keys.")
    else:
        print("\n❌ cuECC API test failed")
    
    return success

if __name__ == "__main__":
    main()