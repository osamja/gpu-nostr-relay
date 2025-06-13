"""
Custom validator plug-in for nostr-relay
CPU-based signature verification (GPU placeholder for future implementation)
"""

import secp256k1

def verify_signature_cpu(event_id_hex: str, signature_hex: str, pubkey_hex: str) -> bool:
    """CPU signature verification"""
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

class GpuSigValidator:
    """CPU-based signature validator (GPU implementation planned)"""
    
    async def validate(self, events):
        """
        Validate a batch of events using CPU verification
        Returns list[bool] aligned with events indicating validity
        """
        if not events:
            return []
        
        results = []
        for event in events:
            try:
                is_valid = verify_signature_cpu(event.id, event.sig, event.pubkey)
                results.append(is_valid)
            except Exception:
                results.append(False)
        
        return results