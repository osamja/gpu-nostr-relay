#!/bin/bash
set -e

echo "🔧 Building GPU-accelerated Nostr relay with proper DB initialization..."

# Build the container
echo "📦 Building Docker image..."
docker build -t nostr-gpu-relay:latest .

echo "✅ Build completed successfully!"

# Run the container with GPU support
echo "🚀 Starting relay with GPU acceleration..."
docker run --gpus all -it -p 6969:6969 -v $(pwd)/data:/data nostr-gpu-relay:latest 