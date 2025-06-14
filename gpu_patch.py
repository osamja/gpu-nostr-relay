"""
GPU Validator Patch for nostr-relay
Monkey patches Event.verify to use our GPU signature validation
"""

def apply_gpu_patch():
    """Apply GPU validation patch to nostr-relay Event class"""
    try:
        from nostr_relay.storage.base import Event
        
        def gpu_verify(self):
            """GPU-accelerated signature verification"""
            print(f"🎯 GPU_VERIFY CALLED for event {self.id[:16]}...")
            
            # Try CUDA GPU verification first
            try:
                from cuda_gpu_validator import verify_signature_gpu
                result = verify_signature_gpu(self.id, self.sig, self.pubkey)
                print(f"🚀 CUDA_GPU_VERIFY RESULT: {result}")
                return result
            except Exception as e:
                print(f"⚠️  CUDA GPU verification failed: {e}")
                # Fallback to CPU
                from gpu_validator import verify_signature_cpu
                result = verify_signature_cpu(self.id, self.sig, self.pubkey)
                print(f"💻 CPU_FALLBACK RESULT: {result}")
                return result
        
        # Patch the Event class
        Event.verify = gpu_verify
        
        print("🚀 GPU validation patch applied successfully")
        
    except Exception as e:
        print(f"❌ GPU patch failed: {e}")
        # Fallback to original behavior
        pass

# Apply patch when module is imported
apply_gpu_patch()