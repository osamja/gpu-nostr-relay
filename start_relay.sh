#!/bin/bash
set -e

echo "Starting GPU Nostr Relay..."
echo "Binding to ${HOST:-0.0.0.0}:${PORT:-6969}"

# Export the config file path for the application
export NOSTR_RELAY_CONFIG=/app/config.yaml

# Start uvicorn directly on the ASGI app with explicit host/port
echo "Starting nostr-relay service via uvicorn..."
exec uvicorn nostr_relay.asgi:app --host 0.0.0.0 --port 6969 