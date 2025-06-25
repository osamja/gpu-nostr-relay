import asyncio
import json
import hashlib
import secp256k1
import websockets

EVENTS = {}

def verify_event(event):
    serialized = json.dumps([
        0,
        event["pubkey"],
        event["created_at"],
        event["kind"],
        event["tags"],
        event["content"],
    ], separators=(',', ':'), ensure_ascii=False)
    digest = hashlib.sha256(serialized.encode()).hexdigest()
    if digest != event.get("id"):
        return False
    try:
        # Use secp256k1 library for compatibility with client
        pubkey_bytes = bytes.fromhex(event["pubkey"])
        sig_bytes = bytes.fromhex(event["sig"])
        event_id_bytes = bytes.fromhex(event["id"])
        
        # Try both compressed formats (0x02 and 0x03 prefix) 
        for prefix in [0x02, 0x03]:
            try:
                compressed_pubkey = bytes([prefix]) + pubkey_bytes
                pubkey_obj = secp256k1.PublicKey(compressed_pubkey, raw=True)
                
                # Deserialize the compact signature using the ECDSA class
                sig_obj = secp256k1.ECDSA().ecdsa_deserialize_compact(sig_bytes)
                
                # Verify the signature
                pubkey_obj.ecdsa_verify(event_id_bytes, sig_obj, raw=True)
                return True
            except Exception:
                continue
        return False
    except Exception:
        return False

async def handler(websocket):
    async for raw in websocket:
        try:
            import pdb; pdb.set_trace()
            msg = json.loads(raw)
            if msg[0] == "EVENT":
                event = msg[1]
                if verify_event(event):
                    EVENTS[event["id"]] = event
                    await websocket.send(json.dumps(["OK", event["id"], True, ""]))
                else:
                    await websocket.send(json.dumps(["OK", event.get("id", ""), False, "invalid"]))
            elif msg[0] == "REQ":
                sub_id = msg[1]
                for ev in EVENTS.values():
                    await websocket.send(json.dumps(["EVENT", sub_id, ev]))
                await websocket.send(json.dumps(["EOSE", sub_id]))
            elif msg[0] == "CLOSE":
                pass
        except Exception as e:
            print("error handling message:", e)

async def main():
    async with websockets.serve(handler, "0.0.0.0", 6969):
        print("relay running on ws://0.0.0.0:6969")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())