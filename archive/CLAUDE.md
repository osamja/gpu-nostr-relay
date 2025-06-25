# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a GPU-accelerated Nostr relay that uses CUDA for batch signature verification. The project extends the `nostr-relay` Python package with custom GPU validation to significantly improve performance for signature verification operations.

## Key Architecture Components

### GPU Acceleration System
- **`gpu_validator.py`**: Core GPU signature validation using cuECC CUDA library
- **cuECC Integration**: Custom CUDA library for secp256k1 signature verification
- **Batch Processing**: Validates multiple signatures in parallel on GPU
- **Fallback Logic**: Simple validation approach (all-or-none based on count)

### Configuration System
- **`config.yaml`**: Main relay configuration with server, storage, and logging settings
- **Environment Variables**: `HOST`, `PORT`, `NOSTR_RELAY_CONFIG`, `LD_PRELOAD`
- **SQLite Backend**: Uses WAL mode for concurrent access

### Container Architecture
- **Multi-stage Docker build**: Separate build and runtime stages
- **CUDA Runtime**: Requires `nvidia/cuda:12.4.0-runtime-ubuntu22.04`
- **GPU Requirements**: Must run with `--gpus all` flag
- **Persistent Storage**: `/data` volume for SQLite database

## Common Development Commands

### Build and Run
```bash
# Build Docker image
docker build -t nostr-gpu-relay:dev .

# Run with GPU support
docker run --gpus all -it -p 6969:6969 nostr-gpu-relay:dev

# Run with persistent data
docker run --gpus all -it -p 6969:6969 -v $(pwd)/data:/data nostr-gpu-relay:dev
```

### Testing
```bash
# Run basic relay tests
python3 test_relay.py

# Run comprehensive benchmark suite
./run_benchmarks.sh

# Run CPU-only benchmark
python3 cpu_benchmark.py

# Run GPU relay benchmark
python3 benchmark_relay.py
```

### Benchmarking Dependencies
```bash
# Install benchmarking dependencies
pip install -r requirements-bench.txt
```

## Testing Strategy

### Basic Functionality Testing
- **`test_relay.py`**: Custom async test suite (no pytest/unittest)
- Tests WebSocket connections, event submission, and relay info retrieval
- Includes pass/fail reporting and activity monitoring

### Performance Benchmarking
- **CPU Baseline**: `cpu_benchmark.py` for signature verification baseline
- **GPU Performance**: `benchmark_relay.py` for relay throughput testing
- **GPU Monitoring**: `monitor_gpu.py` for real-time GPU utilization
- **Automated Suite**: `run_benchmarks.sh` for complete benchmark workflow

### Benchmark Test Scenarios
- Signature verification throughput (1-1000 events)
- Concurrent connections (25-50 simultaneous)
- Sustained load testing at various rates
- GPU vs CPU performance comparison

## Development Environment

### System Requirements
- **CUDA 12.4.0**: Required for GPU acceleration
- **Python 3.11+**: Runtime environment
- **Docker**: For containerized development
- **NVIDIA GPU**: With compute capability for cuECC

### Key Dependencies
- **nostr-relay==1.14**: Base relay implementation
- **cuECC**: Custom CUDA library (compiled from source)
- **uvicorn**: ASGI server
- **aiosqlite**: Async SQLite operations

## Important Implementation Details

### GPU Validator Integration
The `GpuSigValidator` class in `gpu_validator.py` implements the nostr-relay validation interface:
- Uses ctypes to interface with cuECC library
- Converts event IDs and signatures to byte arrays
- Returns validation results as boolean list
- Current implementation is naive (all-or-none validation)

### Database Configuration
- SQLite with WAL journal mode for concurrent access
- Database file: `/data/nostr.sqlite3` (or `nostr.db`)
- Uses aiosqlite for async operations
- Garbage collection runs every 5 minutes

### Container Environment
- Uses `LD_PRELOAD` to load cuECC library
- Binds to all interfaces (0.0.0.0) on port 6969
- Runs uvicorn directly with nostr_relay.asgi:app
- Requires GPU passthrough for acceleration

## Performance Optimization Notes

### Batch Processing
- GPU validation is most efficient with larger batch sizes
- Current implementation validates in single batches
- Consider implementing streaming validation for continuous loads

### Memory Management
- GPU memory usage scales with batch size
- Monitor GPU utilization during high-load scenarios
- Consider implementing GPU memory pooling for sustained loads

### Monitoring
- Use `monitor_gpu.py` to track GPU utilization
- Monitor relay performance with comprehensive benchmark suite
- Check SQLite WAL file growth for database performance

## Debugging and Troubleshooting

### GPU Issues
- Verify CUDA installation and GPU compatibility
- Check cuECC library compilation and linking
- Ensure `--gpus all` flag is used with Docker
- Monitor GPU memory usage during validation

### Connection Issues
- Verify port 6969 is accessible
- Check WebSocket client compatibility
- Monitor concurrent connection limits
- Review uvicorn worker configuration

### Performance Issues
- Run benchmark suite to identify bottlenecks
- Compare GPU vs CPU performance metrics
- Monitor database WAL file size and performance
- Check memory usage patterns during sustained load