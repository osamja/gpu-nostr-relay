import unittest
import sys
import os

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from minimal_client import create_event
from minimal_relay import verify_event

class TestVerifyEvent(unittest.TestCase):
    
    def test_verify_valid_event(self):
        """Test that verify_event returns True for a properly signed event"""
        # Create a valid event using the client
        test_content = "Test message for verification"
        
        event = create_event(test_content)
        
        # Verify the event should pass validation
        result = verify_event(event)
        self.assertTrue(result, "Valid event should pass verification")
    
    def test_verify_invalid_signature(self):
        """Test that verify_event returns False for an event with invalid signature"""
        # Create a valid event
        event = create_event("Test message")
        
        # Corrupt the signature
        event["sig"] = "invalid_signature_hex"
        
        # Verification should fail
        result = verify_event(event)
        self.assertFalse(result, "Event with invalid signature should fail verification")
    
    def test_verify_invalid_id(self):
        """Test that verify_event returns False for an event with incorrect ID"""
        # Create a valid event
        event = create_event("Test message")
        
        # Corrupt the event ID
        event["id"] = "invalid_id_hash"
        
        # Verification should fail
        result = verify_event(event)
        self.assertFalse(result, "Event with invalid ID should fail verification")

if __name__ == "__main__":
    unittest.main() 