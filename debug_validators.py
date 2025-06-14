#!/usr/bin/env python3
"""
Debug script to understand nostr-relay validator system
"""

import sys
import inspect

def inspect_validator_system():
    """Inspect how nostr-relay loads and uses validators"""
    print("🔍 Inspecting nostr-relay validator system...")
    
    try:
        from nostr_relay.storage.base import get_validator
        print("✅ Found get_validator function")
        print(f"get_validator signature: {inspect.signature(get_validator)}")
        
        # Try to get a validator
        try:
            validator = get_validator("gpu_validator.validate_signature")
            print(f"✅ Successfully loaded our validator: {validator}")
        except Exception as e:
            print(f"❌ Failed to load our validator: {e}")
            
        # Try built-in validator
        try:
            builtin = get_validator("nostr_relay.validators.is_signed")
            print(f"✅ Built-in validator: {builtin}")
        except Exception as e:
            print(f"❌ Failed to load built-in: {e}")
            
    except ImportError as e:
        print(f"❌ get_validator not found: {e}")
    
    # Check validators module
    try:
        import nostr_relay.validators
        print(f"\n📋 Available built-in validators:")
        for name in dir(nostr_relay.validators):
            if not name.startswith('_'):
                attr = getattr(nostr_relay.validators, name)
                if callable(attr):
                    print(f"  {name}: {inspect.signature(attr) if inspect.isfunction(attr) else 'callable'}")
                    
    except ImportError as e:
        print(f"❌ validators module not found: {e}")

def test_event_structure():
    """Test what structure events need for validation"""
    print("\n🧪 Testing event structure requirements...")
    
    try:
        from nostr_relay.validators import is_signed
        from benchmark_relay import NostrEventGenerator
        
        gen = NostrEventGenerator()
        event_data = gen.create_event("test")
        
        # Try different event representations
        print("Testing different event objects...")
        
        # Test 1: Dict-like
        try:
            is_signed(event_data, {})
            print("✅ Dict event works")
        except Exception as e:
            print(f"❌ Dict event failed: {e}")
        
        # Test 2: Object with attributes
        class EventObj:
            def __init__(self, data):
                for k, v in data.items():
                    setattr(self, k, v)
                    
        event_obj = EventObj(event_data)
        try:
            is_signed(event_obj, {})
            print("✅ Object event works")
        except Exception as e:
            print(f"❌ Object event failed: {e}")
            
        # Test 3: Add verify method
        def verify(self):
            from gpu_validator import verify_signature_cpu
            return verify_signature_cpu(self.id, self.sig, self.pubkey)
            
        event_obj.verify = verify.__get__(event_obj, EventObj)
        try:
            is_signed(event_obj, {})
            print("✅ Event with verify() method works")
        except Exception as e:
            print(f"❌ Event with verify() failed: {e}")
            
    except Exception as e:
        print(f"❌ Event structure test failed: {e}")
        import traceback
        traceback.print_exc()

def test_config_loading():
    """Test how config loads validators"""
    print("\n⚙️  Testing config loading...")
    
    try:
        from nostr_relay.config import Config
        
        # Try different ways to load config
        configs_to_try = [
            "config.yaml",
            "/app/config.yaml", 
            {"storage": {"validators": ["gpu_validator.validate_signature"]}}
        ]
        
        for cfg in configs_to_try:
            try:
                if isinstance(cfg, str):
                    config = Config.from_path(cfg)
                else:
                    config = Config(**cfg)
                print(f"✅ Loaded config from {cfg}")
                print(f"   Storage config: {getattr(config, 'storage', 'Not found')}")
                break
            except Exception as e:
                print(f"❌ Failed to load {cfg}: {e}")
                
    except Exception as e:
        print(f"❌ Config loading test failed: {e}")

if __name__ == "__main__":
    inspect_validator_system()
    test_event_structure() 
    test_config_loading()