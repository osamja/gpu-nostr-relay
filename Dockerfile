# -------- build stage --------------------------------------------------------
    FROM nvidia/cuda:12.4.0-devel-ubuntu22.04 AS build

    # System deps
    RUN apt-get update && \
        DEBIAN_FRONTEND=noninteractive \
        apt-get install -y --no-install-recommends \
            python3.11 python3-pip git build-essential make curl && \
        rm -rf /var/lib/apt/lists/*
    
    # Python relay
    RUN pip install --no-cache-dir nostr-relay==1.14
    
    # CUDA secp256k1 library (cuECC)
    RUN git clone https://github.com/betarixm/cuECC.git /tmp/cuECC && \
        make -C /tmp/cuECC all && \
        cp /tmp/cuECC/libcuecc.so /usr/local/lib/
    
    # -------- runtime stage ------------------------------------------------------
    FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04
    
    # Relay env
    ENV PYTHONUNBUFFERED=1 \
        RUST_LOG=info \
        LD_PRELOAD=/usr/local/lib/libcuecc.so  # ensure CUDA lib is seen
    
    COPY --from=build /usr/local/lib/libcuecc.so /usr/local/lib/
    COPY --from=build /usr/local/bin/nostr-relay /usr/local/bin/
    COPY gpu_validator.py /app/gpu_validator.py
    COPY config.yaml /app/config.yaml
    
    WORKDIR /app
    EXPOSE 6969
    
    CMD ["nostr-relay", "-c", "/app/config.yaml", "serve"]
    