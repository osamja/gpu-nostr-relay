# GPU Nostr Relay Benchmarking Guide

This guide explains how to benchmark your GPU-accelerated Nostr relay and measure the performance benefits of CUDA-based signature verification.

## 🚀 Quick Start

Run the complete benchmark suite:
```bash
./run_benchmarks.sh
```

This will:
1. Install Python dependencies
2. Run CPU-only signature verification benchmark
3. Start the GPU relay (if not running)
4. Run GPU relay benchmark with various workloads
5. Generate a performance comparison report

## 📊 Benchmark Components

### 1. CPU Benchmark (`cpu_benchmark.py`)
- Tests CPU-only signature verification performance
- Provides baseline performance for comparison
- Measures signature verification rates at different batch sizes

**Usage:**
```bash
python3 cpu_benchmark.py
# OR
./run_benchmarks.sh cpu-only
```

### 2. GPU Relay Benchmark (`benchmark_relay.py`)
- Comprehensive relay testing with real WebSocket connections
- Tests signature verification throughput with GPU acceleration
- Measures concurrent connection handling
- Tests sustained load performance

**Tests included:**
- **Signature Verification Throughput**: Batch sizes from 1 to 1000 events
- **Concurrent Connections**: 25 and 50 simultaneous connections
- **Sustained Load**: Extended performance testing at different rates

**Usage:**
```bash
python3 benchmark_relay.py
# OR
./run_benchmarks.sh gpu-only
```

### 3. GPU Monitoring (`monitor_gpu.py`)
- Real-time GPU utilization monitoring during benchmarks
- Tracks GPU usage, memory usage, and temperature
- Provides summary statistics

**Usage:**
```bash
# Monitor in separate terminal during benchmarks
python3 monitor_gpu.py

# Custom monitoring interval (default: 1 second)
python3 monitor_gpu.py 0.5
```

## 🔧 Dependencies

Install benchmarking dependencies:
```bash
pip install -r requirements-bench.txt
```

**Required packages:**
- `websockets` - WebSocket client for relay testing
- `secp256k1` - Cryptographic operations
- `aiohttp` - HTTP client utilities

**Optional packages:**
- `psutil` - System resource monitoring
- `matplotlib` - Result visualization
- `pandas` - Data analysis

## 📈 Understanding Results

### GPU Acceleration Metrics

The benchmark measures GPU acceleration benefits in several ways:

1. **Signature Verification Rate**: Events processed per second
2. **Batch Processing Efficiency**: Performance scaling with batch size
3. **GPU Utilization**: How well the GPU is being used

### Expected Performance Characteristics

**Good GPU Acceleration:**
- Higher throughput at larger batch sizes (100+ events)
- GPU utilization > 50% during verification
- 2-10x speedup over CPU for large batches

**Moderate GPU Acceleration:**
- 1.2-2x speedup over CPU
- GPU utilization 20-50%
- Better performance on sustained loads

**Limited GPU Acceleration:**
- Similar performance to CPU
- Low GPU utilization < 20%
- No batch processing benefits

### Sample Output

```
🏆 BENCHMARK RESULTS SUMMARY
================================================================================

📊 Signature Verification (batch_size=100)
Duration: 0.45s
Events Processed: 100
Throughput: 222.2 events/sec
Success Rate: 100.0%

📊 Signature Verification (batch_size=1000)  
Duration: 1.23s
Events Processed: 1,000
Throughput: 813.0 events/sec
Success Rate: 100.0%

🎯 OVERALL PERFORMANCE
Peak Throughput: 813.0 events/sec
Average Success Rate: 100.0%

🚀 GPU ACCELERATION ANALYSIS
Signature verification shows GPU batch processing benefits:
  Batch size 1: 45.2 events/sec
  Batch size 100: 222.2 events/sec
  Batch size 1000: 813.0 events/sec
```

## 🔍 Troubleshooting

### Low GPU Performance

If you see limited GPU acceleration:

1. **Check GPU library loading:**
   ```bash
   ldd /usr/local/lib/libcuecc.so
   ```

2. **Verify GPU is available:**
   ```bash
   nvidia-smi
   ```

3. **Monitor GPU during benchmarks:**
   ```bash
   # In separate terminal
   python3 monitor_gpu.py
   ```

4. **Check Docker GPU access:**
   ```bash
   docker run --gpus all nvidia/cuda:12.4.0-runtime-ubuntu22.04 nvidia-smi
   ```

### Connection Issues

If relay connection fails:

1. **Check if relay is running:**
   ```bash
   curl -I http://localhost:6969
   ```

2. **Start relay manually:**
   ```bash
   ./start_relay.sh
   # OR
   docker run --gpus all -p 6969:6969 nostr-gpu-relay:dev
   ```

3. **Check relay logs:**
   ```bash
   docker logs nostr-bench-relay
   ```

### Dependency Issues

If secp256k1 installation fails:

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install libsecp256k1-dev

# Try alternative installation
pip install secp256k1 --no-binary secp256k1
```

## 🎯 Optimization Tips

### Maximizing GPU Performance

1. **Use larger batch sizes** (100+ events) for better GPU utilization
2. **Ensure adequate GPU memory** for batch processing
3. **Monitor GPU temperature** to avoid throttling
4. **Use sustained load tests** to measure real-world performance

### Relay Configuration

1. **Increase worker processes** in `config.yaml` for higher concurrency
2. **Tune database connection pool** for better I/O performance
3. **Optimize WebSocket buffer sizes** for high-throughput scenarios

### System Optimization

1. **Use high-performance storage** (NVMe SSD) for database
2. **Ensure adequate system RAM** for batch processing
3. **Monitor system resources** during benchmarks

## 📋 Benchmark Checklist

Before running benchmarks:

- [ ] GPU drivers installed and working (`nvidia-smi`)
- [ ] Docker configured with GPU support (`--gpus all`)
- [ ] cuECC library compiled and loaded
- [ ] Python dependencies installed
- [ ] Adequate disk space for results and logs
- [ ] No other GPU-intensive processes running

## 🔬 Advanced Benchmarking

### Custom Benchmark Scenarios

Modify `benchmark_relay.py` to test specific scenarios:

```python
# Test specific batch sizes
await self.benchmark_signature_verification_throughput([500, 1000, 2000])

# Test higher concurrency
await self.benchmark_concurrent_connections(num_connections=200)

# Test longer sustained loads
await self.benchmark_sustained_load(duration_seconds=300, events_per_second_target=200)
```

### Performance Profiling

For detailed performance analysis:

```bash
# Profile GPU memory usage
nvidia-smi --query-gpu=memory.used --format=csv -l 1

# Profile system resources
top -p $(pgrep -f nostr-relay)

# Network performance
ss -tuln | grep 6969
```

## 📊 Result Analysis

### Comparing GPU vs CPU

The benchmark suite automatically generates comparison reports, but you can also:

1. **Calculate speedup ratios** from raw results
2. **Plot performance curves** with matplotlib
3. **Analyze batch size efficiency** for optimization
4. **Compare with other relay implementations**

### Performance Baselines

Typical performance expectations:

- **CPU (modern x86_64)**: 50-200 signatures/sec
- **GPU (mid-range)**: 200-1000 signatures/sec
- **GPU (high-end)**: 1000+ signatures/sec

Your results will vary based on:
- GPU model and compute capability
- Batch sizes used
- System configuration
- Network latency

## 🤝 Contributing

To improve the benchmark suite:

1. **Add new test scenarios** in `benchmark_relay.py`
2. **Improve GPU monitoring** in `monitor_gpu.py`
3. **Add result visualization** tools
4. **Optimize benchmark efficiency**

Submit pull requests with benchmark improvements! 