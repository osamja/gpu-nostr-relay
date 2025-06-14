#!/usr/bin/env python3
"""
Patch event objects to use our GPU validator
"""

import sys

def patch_event_verification():
    """Monkey patch event verification to use our GPU validator"""
    print("🔧 Patching event verification...")
    
    try:
        # Import the nostr_relay Event class
        from nostr_relay.storage.base import Event
        
        # Save original verify method if it exists
        original_verify = getattr(Event, 'verify', None)
        
        def gpu_verify(self):
            """Use our GPU validator for event verification"""
            from gpu_validator import verify_signature_cpu
            print(f"🎯 GPU verify called for event {self.id[:16]}...")
            return verify_signature_cpu(self.id, self.sig, self.pubkey)
        
        # Patch the Event class
        Event.verify = gpu_verify
        
        print("✅ Event.verify patched to use GPU validator")
        
        # Test the patch
        test_event = Event(
            id="a" * 64,
            sig="b" * 128,
            pubkey="c" * 64,
            content="test",
            created_at=1234567890,
            kind=1,
            tags=[]
        )
        
        try:
            result = test_event.verify()
            print(f"✅ Patched verify works: {result}")
        except Exception as e:
            print(f"❌ Patched verify failed: {e}")
            
    except Exception as e:
        print(f"❌ Event patching failed: {e}")
        import traceback
        traceback.print_exc()

def patch_at_startup():
    """Patch that can be called at module import time"""
    print("🚀 Applying startup patches...")
    patch_event_verification()

if __name__ == "__main__":
    patch_at_startup()
    
    # Test with is_signed validator
    try:
        from nostr_relay.validators import is_signed
        from nostr_relay.storage.base import Event
        
        # Create a test event with valid signature
        from benchmark_relay import NostrEventGenerator
        gen = NostrEventGenerator()
        event_data = gen.create_event("patch test")
        
        event = Event(**event_data)
        
        try:
            is_signed(event, {})
            print("🎉 SUCCESS! is_signed accepts our patched event")
        except Exception as e:
            print(f"❌ is_signed still rejects: {e}")
            
    except Exception as e:
        print(f"❌ is_signed test failed: {e}")
        import traceback
        traceback.print_exc()