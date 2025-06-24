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

# ── Compile custom CUDA ECDSA verification library ────────────────────────────
COPY cuda_ecdsa.cu /tmp/cuda_ecdsa.cu
COPY Makefile /tmp/Makefile
RUN cd /tmp && \
    make && \
    cp libcuda_ecdsa.so /usr/local/lib/ && \
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
RUN pip install --no-cache-dir nostr-relay==1.14 secp256k1>=0.14.0 numpy

# ── Copy compiled CUDA libraries ─────────────────────────────────────────────
COPY --from=build /usr/local/lib/libcuecc.so /usr/local/lib/
COPY --from=build /usr/local/lib/libcuda_ecdsa.so /usr/local/lib/
RUN ldconfig   # refresh dynamic linker cache

# ── Application files ────────────────────────────────────────────────────────
# If you have custom scripts add them here
COPY gpu_validator.py /app/gpu_validator.py
COPY cuda_gpu_validator.py /app/cuda_gpu_validator.py
COPY gpu_patch.py     /app/gpu_patch.py
COPY config.yaml      /app/config.yaml
COPY init_db.py       /app/init_db.py
COPY start_relay.sh    /app/start_relay.sh
RUN chmod +x /app/start_relay.sh /app/init_db.py

# ── Prepare runtime dirs (SQLite lives here) ─────────────────────────────────
RUN mkdir -p /data && \
    chmod 755 /data && \
    chown -R nobody:nogroup /data 2>/dev/null || true
VOLUME ["/data"]          # keeps DB when container restarts

WORKDIR /app
EXPOSE 6969

# ── Ensure startup script is executable ──────────────────────────────────────
RUN chmod +x /app/start_relay.sh

# ── Start the relay, binding to all interfaces ───────────────────────────────
CMD ["/app/start_relay.sh"]
