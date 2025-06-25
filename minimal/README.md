# Minimal Nostr Client and Relay

A simple implementation of a Nostr (Notes and Other Stuff Transmitted by Relays) client and relay for testing and educational purposes.

## Overview

This minimal implementation consists of two main components:
- **`minimal_relay.py`**: A basic Nostr relay that accepts and stores events
- **`minimal_client.py`**: A simple client that creates and sends Nostr events

## Prerequisites

Install the required dependencies:

```bash
pip install websockets secp256k1 ecdsa
```

## Components

### Minimal Relay (`minimal_relay.py`)

A lightweight Nostr relay implementation that:
- Listens on `ws://0.0.0.0:6969` by default
- Accepts `EVENT` messages and validates them using ECDSA signature verification
- Stores valid events in memory
- Responds to `REQ` messages by returning all stored events
- Supports `CLOSE` messages (no-op)

**Features:**
- Event validation using ECDSA with SECP256k1 curve
- In-memory event storage
- Basic Nostr protocol message handling (EVENT, REQ, CLOSE)
- JSON-based communication over WebSockets

### Minimal Client (`minimal_client.py`)

A simple Nostr client that:
- Generates a secp256k1 key pair
- Creates properly formatted Nostr events
- Signs events with ECDSA
- Sends events to a relay via WebSocket

**Features:**
- Automatic key generation using secp256k1
- Proper event serialization according to Nostr specification
- Event signing with compact signature format
- WebSocket communication with relay

## Usage

### Starting the Relay

```bash
cd minimal/
python minimal_relay.py
```

The relay will start and listen on `ws://0.0.0.0:6969`. You should see:
```
relay running on ws://0.0.0.0:6969
```

### Running the Client

In a separate terminal:

```bash
cd minimal/
python minimal_client.py
```

The client will:
1. Generate a new key pair
2. Create an event with the current timestamp as content
3. Send the event to the relay at `ws://localhost:6969`
4. Display the sent message and relay response

Example output:
```
sent: ["EVENT", {"pubkey": "...", "created_at": 1699123456, "kind": 1, "tags": [], "content": "1699123456.789", "id": "...", "sig": "..."}]
recv: ["OK", "event_id_here", true, ""]
```

## Event Structure

Events follow the Nostr specification with these fields:
- `id`: SHA-256 hash of the serialized event data
- `pubkey`: 32-byte public key in hex format
- `created_at`: Unix timestamp
- `kind`: Event type (1 for text notes)
- `tags`: Array of tags (empty in this minimal implementation)
- `content`: Event content
- `sig`: ECDSA signature in compact format

## Protocol Messages

The implementation supports basic Nostr protocol messages:

### EVENT Message
```json
["EVENT", <event object>]
```

### REQ Message
```json
["REQ", <subscription_id>, <filters>]
```

### OK Response
```json
["OK", <event_id>, <true|false>, <message>]
```

### EOSE Message
```json
["EOSE", <subscription_id>]
```

## Limitations

This is a minimal implementation intended for testing and educational purposes:

- **No persistence**: Events are stored only in memory
- **No filtering**: REQ messages return all stored events regardless of filters
- **No subscriptions**: Real-time event streaming is not implemented
- **Single connection**: The relay handles connections independently
- **No authentication**: No access control or rate limiting
- **Basic validation**: Minimal event validation beyond signature verification

## Testing

### Running the E2E Test

A minimal end-to-end test is provided to verify the basic functionality:

```bash
cd minimal/
python test_e2e.py
```

The test will:
1. Start a relay server on localhost:8888
2. Create and send a test event using the client functionality
3. Verify the relay responds with an OK message
4. Request all events back and verify the event was stored correctly
5. Clean up the test server

### Manual Testing

You can also test the relay with multiple clients or extend the client to:
- Send multiple events
- Subscribe to events from other clients
- Implement custom event content

## Debugging

The relay includes a debug breakpoint (`pdb.set_trace()`) that you may want to remove for production use. To remove it, edit `minimal_relay.py` and delete or comment out line 30:

```python
# import pdb; pdb.set_trace()  # Remove this line
```

## Next Steps

To extend this implementation, consider:
- Adding event persistence (database storage)
- Implementing proper subscription filtering
- Adding rate limiting and authentication
- Supporting additional event kinds
- Adding real-time event broadcasting to subscribers
- Implementing NIP (Nostr Implementation Possibilities) specifications

## License

This minimal implementation is provided for educational purposes. 