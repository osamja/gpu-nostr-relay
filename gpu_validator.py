"""
Custom validator plug-in for nostr-relay
Uses cuECC's CUDA batch verifier for secp256k1 signatures.
"""

from ctypes import cdll, c_int, c_char_p, POINTER
from pathlib import Path

# ---- load the shared library ------------------------------------------------
LIB_PATH = Path("/usr/local/lib/libcuecc.so")
cuecc = cdll.LoadLibrary(str(LIB_PATH))

# C function prototype: int verify_batch(int n, const char **msgs, const char **sigs)
cuecc.verify_batch.argtypes = [c_int, POINTER(c_char_p), POINTER(c_char_p)]
cuecc.verify_batch.restype = c_int  # returns number of *valid* signatures

# ---- nostr-relay hook -------------------------------------------------------
# nostr-relay will import this class and call .validate(events) asynchronously
class GpuSigValidator:
    async def validate(self, events):
        """
        `events` is a list of Event objects.
        Each Event has `.id` (32-byte SHA-256 digest hex) and `.sig` (64-byte hex).
        Returns a list[bool] aligned with `events` indicating validity.
        """
        n = len(events)
        if n == 0:
            return []

        # prepare C arrays of pointers to null-terminated bytes
        MsgArray = c_char_p * n
        SigArray = c_char_p * n
        msgs = MsgArray(*[bytes.fromhex(e.id) for e in events])
        sigs = SigArray(*[bytes.fromhex(e.sig) for e in events])

        valid_count = cuecc.verify_batch(n, msgs, sigs)

        # very naive: assume the function validates *all* or *none*
        # (replace with bitmask output if you extend the C side)
        return [True] * valid_count + [False] * (n - valid_count)
