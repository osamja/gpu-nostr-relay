import asyncio
import json
import time
import hashlib
import secp256k1
import websockets

# Generate a secp256k1 private key using the secp256k1 library
private_key = secp256k1.PrivateKey()
public_key_obj = private_key.pubkey
# Get the x-coordinate only (exactly 32 bytes, no prefix)
pk_hex = public_key_obj.serialize(compressed=True)[1:].hex()  # Remove 0x02/0x03 prefix

def create_event(content: str):
    event = {
        "pubkey": pk_hex,
        "created_at": int(time.time()),
        "kind": 1,
        "tags": [],
        "content": content,
    }
    serialized = json.dumps([
        0,
        event["pubkey"],
        event["created_at"],
        event["kind"],
        event["tags"],
        event["content"],
    ], separators=(',', ':'), ensure_ascii=False)
    event_id = hashlib.sha256(serialized.encode()).hexdigest()
    event["id"] = event_id
    
    # Sign using secp256k1 library to get the correct signature format
    signature = private_key.ecdsa_sign(bytes.fromhex(event_id))
    sig_compact = private_key.ecdsa_serialize_compact(signature)
    event["sig"] = sig_compact.hex()
    return event

async def send_event(uri: str, event):
    async with websockets.connect(uri) as ws:
        msg = json.dumps(["EVENT", event])
        await ws.send(msg)
        print("sent:", msg)
        try:
            reply = await asyncio.wait_for(ws.recv(), timeout=5.0)
            print("recv:", reply)
        except asyncio.TimeoutError:
            print("no response")

        # request all events back to verify storage
        # sub_id = "test"
        # await ws.send(json.dumps(["REQ", sub_id, {}]))
        # while True:
        #     try:
        #         resp = await asyncio.wait_for(ws.recv(), timeout=0)
        #     except asyncio.TimeoutError:
        #         break
        #     print("recv:", resp)
        #     if resp.startswith('["EOSE"'):
        #         break

if __name__ == "__main__":
    ev = create_event(str(time.time()))
    asyncio.run(send_event("ws://localhost:6969", ev))
