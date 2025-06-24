import asyncio
import json
import hashlib
from ecdsa import VerifyingKey, SECP256k1
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
        vk = VerifyingKey.from_string(bytes.fromhex(event["pubkey"]), curve=SECP256k1)
        vk.verify(bytes.fromhex(event["sig"]), bytes.fromhex(event["id"]))
        return True
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