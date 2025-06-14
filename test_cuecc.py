#!/usr/bin/env python3
"""
Test cuECC library interface
"""

import ctypes
import sys

def test_cuecc_library():
    """Test loading and exploring cuECC library"""
    print("🔍 Testing cuECC library interface...")
    
    try:
        # Load the cuECC library
        lib = ctypes.CDLL("/usr/local/lib/libcuecc.so")
        print("✅ Successfully loaded libcuecc.so")
        
        # Try to find common function names
        common_names = [
            'verify', 'batch_verify', 'ecc_verify', 'secp256k1_verify',
            'signature_verify', 'cuda_verify', 'init', 'cleanup',
            'batch_signature_verify', 'verify_batch', 'ecdsa_verify'
        ]
        
        found_functions = []
        for name in common_names:
            try:
                func = getattr(lib, name)
                found_functions.append(name)
                print(f"✅ Found function: {name}")
            except AttributeError:
                pass
        
        if not found_functions:
            print("❌ No obvious verification functions found")
            print("🔍 Trying to call any exported functions...")
            
            # Try some common patterns
            test_patterns = [
                'main', '__init', '_Z*', 'test*'
            ]
            
            for pattern in test_patterns:
                try:
                    if pattern.endswith('*'):
                        # Can't easily search for patterns, skip
                        continue
                    func = getattr(lib, pattern)
                    print(f"✅ Found: {pattern}")
                except AttributeError:
                    pass
        
        # Try to call a test function if we find one
        if 'init' in found_functions:
            try:
                result = lib.init()
                print(f"✅ init() returned: {result}")
            except Exception as e:
                print(f"❌ init() failed: {e}")
        
        return found_functions
        
    except OSError as e:
        print(f"❌ Failed to load library: {e}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return []

def test_basic_gpu_call():
    """Test basic GPU functionality"""
    print("\n🧪 Testing basic GPU calls...")
    
    try:
        lib = ctypes.CDLL("/usr/local/lib/libcuecc.so")
        
        # Create some test data
        event_id = b'a' * 32  # 32-byte event ID
        signature = b'b' * 64  # 64-byte signature
        pubkey = b'c' * 32     # 32-byte public key
        
        print(f"✅ Test data prepared:")
        print(f"   Event ID: {len(event_id)} bytes")
        print(f"   Signature: {len(signature)} bytes")
        print(f"   Pubkey: {len(pubkey)} bytes")
        
        # Try to call verification (this will likely fail but gives us info)
        try:
            # This is speculative - we don't know the real function name yet
            result = lib.verify(event_id, signature, pubkey)
            print(f"✅ Verification call succeeded: {result}")
        except AttributeError:
            print("❌ No 'verify' function found")
        except Exception as e:
            print(f"❌ Verification call failed: {e}")
            
    except Exception as e:
        print(f"❌ GPU test failed: {e}")

if __name__ == "__main__":
    functions = test_cuecc_library()
    test_basic_gpu_call()
    
    if functions:
        print(f"\n📋 Found {len(functions)} functions: {functions}")
    else:
        print("\n❌ No functions found - library may have different interface")