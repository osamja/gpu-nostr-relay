#!/usr/bin/env python3
"""
Debug script to trace nostr-relay validator loading
"""

import sys
import pdb
import importlib
import inspect
from pathlib import Path

def debug_nostr_relay():
    """Debug nostr-relay configuration and validator loading"""
    print("🔍 Debugging nostr-relay validator loading...")
    
    # Add current directory to path for our modules
    sys.path.insert(0, str(Path.cwd()))
    
    # Import nostr-relay modules
    try:
        import nostr_relay
        import nostr_relay.storage
        import nostr_relay.storage.base
        import nostr_relay.config
        print("✅ nostr_relay modules imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import nostr_relay: {e}")
        return
    
    # Check config loading
    try:
        from nostr_relay.config import Config
        config = Config("config.yaml")
        print("✅ Config loaded successfully")
        print(f"Config dict: {config.__dict__}")
        
        # Look for storage config
        if hasattr(config, 'storage'):
            print(f"Storage config: {config.storage}")
        else:
            print("❌ No storage config found")
            
    except Exception as e:
        print(f"❌ Config loading failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Examine storage module for validator loading
    print("\n🔍 Examining storage module...")
    storage_module = nostr_relay.storage
    print(f"Storage module attributes: {[x for x in dir(storage_module) if not x.startswith('_')]}")
    
    # Look for validator-related classes/functions
    for attr_name in dir(storage_module):
        attr = getattr(storage_module, attr_name)
        if 'validator' in attr_name.lower() or (inspect.isclass(attr) and 'validate' in str(attr).lower()):
            print(f"Found validator-related: {attr_name} = {attr}")
    
    # Check base storage
    print("\n🔍 Examining storage.base module...")
    base_module = nostr_relay.storage.base
    print(f"Base module attributes: {[x for x in dir(base_module) if not x.startswith('_')]}")
    
    # Look for how validators are registered
    for attr_name in dir(base_module):
        if 'validator' in attr_name.lower():
            attr = getattr(base_module, attr_name)
            print(f"Found in base: {attr_name} = {attr}")
            if inspect.isclass(attr):
                print(f"  Methods: {[m for m in dir(attr) if not m.startswith('_')]}")

def trace_validator_calls():
    """Set up tracing to see what validators are being called"""
    print("\n🔍 Setting up validator call tracing...")
    
    # Import our validator
    try:
        from gpu_validator import validate_signature
        print("✅ Our validator imported")
        
        # Wrap it with debugging
        original_validate = validate_signature
        
        def debug_validate_signature(event, config=None):
            print(f"🎯 GPU validator called! Event ID: {getattr(event, 'id', 'unknown')[:16]}...")
            pdb.set_trace()  # Break here when our validator is called
            return original_validate(event, config)
        
        # Replace the function
        import gpu_validator
        gpu_validator.validate_signature = debug_validate_signature
        
        print("✅ Validator wrapped with debugger")
        
    except Exception as e:
        print(f"❌ Failed to wrap validator: {e}")

def inspect_event_validation():
    """Manually test event validation flow"""
    print("\n🧪 Testing event validation manually...")
    
    try:
        # Import the benchmark event generator
        sys.path.append('/app')  # Add for container compatibility
        from benchmark_relay import NostrEventGenerator
        
        gen = NostrEventGenerator()
        event = gen.create_event("debug test")
        
        print(f"Test event: {event['id'][:16]}...")
        
        # Test our validator directly
        from gpu_validator import validate_signature
        
        class MockEvent:
            def __init__(self, data):
                self.id = data['id']
                self.sig = data['sig']
                self.pubkey = data['pubkey']
                
        mock_event = MockEvent(event)
        
        try:
            validate_signature(mock_event)
            print("✅ Our validator accepts the event")
        except Exception as e:
            print(f"❌ Our validator rejects: {e}")
            
        # Now test with nostr-relay's built-in validation
        try:
            from nostr_relay.validators import is_signed
            is_signed(mock_event, {})
            print("✅ Built-in validator accepts the event")
        except Exception as e:
            print(f"❌ Built-in validator rejects: {e}")
            
    except Exception as e:
        print(f"❌ Event validation test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_nostr_relay()
    trace_validator_calls()
    inspect_event_validation()
    
    print("\n🎯 Debug setup complete. Run relay and submit events to trigger debugger.")