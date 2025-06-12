#!/bin/bash
set -e

echo "Starting GPU Nostr Relay..."
echo "Setting up relay with network proxy workaround..."

# Install socat for port forwarding
apt-get update && apt-get install -y socat

# Start the nostr-relay in the background (it will bind to 127.0.0.1:6969)
echo "Starting nostr-relay service..."
nostr-relay -c /app/config.yaml serve --use-uvicorn &
RELAY_PID=$!

# Wait for the relay to start
echo "Waiting for relay to start..."
sleep 5

# Start socat to forward 0.0.0.0:6968 to 127.0.0.1:6969 (where relay actually binds)
echo "Starting network proxy 0.0.0.0:6968 -> 127.0.0.1:6969..."
socat TCP-LISTEN:6968,bind=0.0.0.0,fork,reuseaddr TCP:127.0.0.1:6969 &
SOCAT_PID=$!

echo "✅ GPU Nostr Relay is now accessible on 0.0.0.0:6968"
echo "   Relay PID: $RELAY_PID"
echo "   Proxy PID: $SOCAT_PID"

# Wait for both processes
wait $RELAY_PID $SOCAT_PID 