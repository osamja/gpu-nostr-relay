#!/bin/bash
set -e

echo "Starting GPU Nostr Relay..."
echo "Binding to ${HOST:-0.0.0.0}:${PORT:-6969}"

# Export the config file path for the application
export NOSTR_RELAY_CONFIG=/app/config.yaml
export PYTHONPATH=/app:$PYTHONPATH

# Initialize database if it doesn't exist
if [ ! -f /data/nostr.sqlite3 ]; then
    echo "🔧 Initializing database schema..."
    python3 /app/init_db.py
    if [ $? -ne 0 ]; then
        echo "❌ Database initialization failed"
        exit 1
    fi
else
    echo "✅ Database already exists"
fi

# Apply GPU validation patch before starting relay
echo "Applying GPU validation patch..."
python3 -c "import gpu_patch; print('GPU patch loaded')"

# Start uvicorn directly on the ASGI app with explicit host/port
echo "Starting nostr-relay service via uvicorn..."
exec python3 -c "
import gpu_patch
import uvicorn
uvicorn.run('nostr_relay.asgi:app', host='0.0.0.0', port=6969)
" 