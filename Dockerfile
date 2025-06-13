###############################################################################
# Build stage – compiles cuECC and pre-downloads Python wheels               #
###############################################################################
FROM nvidia/cuda:12.4.0-devel-ubuntu22.04 AS build

# ── System packages ───────────────────────────────────────────────────────────
RUN apt-get update && DEBIAN_FRONTEND=noninteractive \
    apt-get install -y --no-install-recommends \
        python3.11 python3-pip git build-essential make curl \
 && rm -rf /var/lib/apt/lists/*

# ── Relay & deps ──────────────────────────────────────────────────────────────
RUN pip install --no-cache-dir nostr-relay==1.14

# ── Compile CUDA secp256k1 (cuECC) ────────────────────────────────────────────
RUN git clone https://github.com/betarixm/cuECC.git /tmp/cuECC && \
    make -C /tmp/cuECC all && \
    cp /tmp/cuECC/build/libcuecc.so /usr/local/lib/ && \
    ldconfig

###############################################################################
# Runtime stage – slim image with GPU libs, Python and the compiled library   #
###############################################################################
FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04

ENV PYTHONUNBUFFERED=1 \
    RUST_LOG=info \
    LD_PRELOAD=/usr/local/lib/libcuecc.so \
    HOST=0.0.0.0 \
    PORT=6969

# ── Minimal Python runtime ────────────────────────────────────────────────────
RUN apt-get update && DEBIAN_FRONTEND=noninteractive \
    apt-get install -y --no-install-recommends python3.11 python3-pip \
 && rm -rf /var/lib/apt/lists/*

# ── Relay package and GPU validator dependencies ─────────────────────────────
RUN pip install --no-cache-dir nostr-relay==1.14 secp256k1>=0.14.0

# ── Copy compiled CUDA library ────────────────────────────────────────────────
COPY --from=build /usr/local/lib/libcuecc.so /usr/local/lib/
RUN ldconfig   # refresh dynamic linker cache

# ── Application files ────────────────────────────────────────────────────────
# If you have custom scripts add them here
COPY gpu_validator.py /app/gpu_validator.py
COPY config.yaml      /app/config.yaml
COPY start_relay.sh    /app/start_relay.sh
RUN chmod +x /app/start_relay.sh

# ── Prepare runtime dirs (SQLite lives here) ─────────────────────────────────
RUN mkdir -p /data
VOLUME ["/data"]          # keeps DB when container restarts

WORKDIR /app
EXPOSE 6969

# ── Start the relay, binding to all interfaces ───────────────────────────────
CMD ["/app/start_relay.sh"]
