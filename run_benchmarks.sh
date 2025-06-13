#!/bin/bash
set -e

echo "🚀 GPU Nostr Relay Comprehensive Benchmark Suite"
echo "=================================================="

# Check if relay is running
check_relay() {
    echo "🔍 Checking if relay is running..."
    if curl -s --max-time 5 http://localhost:6969 > /dev/null 2>&1; then
        echo "✅ Relay appears to be running on port 6969"
        return 0
    else
        echo "⚠️  Relay not detected on port 6969"
        return 1
    fi
}

# Install dependencies
setup_deps() {
    echo "📦 Installing benchmark dependencies..."
    if command -v pip3 &> /dev/null; then
        pip3 install -r requirements-bench.txt
    elif command -v pip &> /dev/null; then
        pip install -r requirements-bench.txt
    else
        echo "❌ pip not found. Please install Python dependencies manually:"
        cat requirements-bench.txt
        exit 1
    fi
}

# Run CPU benchmark for comparison
run_cpu_benchmark() {
    echo ""
    echo "💻 Running CPU-only benchmark for comparison..."
    echo "================================================"
    python3 cpu_benchmark.py | tee cpu_benchmark_results.txt
}

# Run GPU relay benchmark
run_gpu_benchmark() {
    echo ""
    echo "🚀 Running GPU relay benchmark..."
    echo "=================================="
    
    if ! check_relay; then
        echo "🐳 Attempting to start relay with Docker..."
        if command -v docker &> /dev/null; then
            # Check if image exists
            if docker images | grep -q "nostr-gpu-relay:dev"; then
                echo "🔄 Starting existing relay container..."
                docker run --gpus all -d --name nostr-bench-relay -p 6969:6969 nostr-gpu-relay:dev
                sleep 5
                STARTED_CONTAINER=true
            else
                echo "🔨 Building relay image..."
                docker build -t nostr-gpu-relay:dev .
                echo "🔄 Starting relay container..."
                docker run --gpus all -d --name nostr-bench-relay -p 6969:6969 nostr-gpu-relay:dev
                sleep 10
                STARTED_CONTAINER=true
            fi
        else
            echo "❌ Docker not found and relay not running."
            echo "Please start your relay manually with: ./start_relay.sh"
            exit 1
        fi
    fi
    
    # Wait for relay to be ready
    echo "⏳ Waiting for relay to be ready..."
    for i in {1..30}; do
        if check_relay; then
            break
        fi
        sleep 1
        echo -n "."
    done
    echo ""
    
    if check_relay; then
        echo "✅ Relay is ready, starting GPU benchmark..."
        python3 benchmark_relay.py | tee gpu_benchmark_results.txt
    else
        echo "❌ Relay failed to start properly"
        exit 1
    fi
}

# Generate comparison report
generate_report() {
    echo ""
    echo "📊 Generating Performance Comparison Report..."
    echo "=============================================="
    
    cat << 'EOF' > benchmark_comparison.py
#!/usr/bin/env python3
import re
import sys

def extract_throughput(filename, pattern):
    """Extract throughput numbers from benchmark results"""
    try:
        with open(filename, 'r') as f:
            content = f.read()
        
        matches = re.findall(pattern, content)
        return [float(m) for m in matches if float(m) > 0]
    except FileNotFoundError:
        return []

def main():
    print("📊 PERFORMANCE COMPARISON REPORT")
    print("=" * 50)
    
    # Extract CPU results
    cpu_rates = extract_throughput('cpu_benchmark_results.txt', r'(\d+\.?\d*) signatures/sec')
    
    # Extract GPU results  
    gpu_rates = extract_throughput('gpu_benchmark_results.txt', r'(\d+\.?\d*) events/sec')
    
    if cpu_rates and gpu_rates:
        max_cpu = max(cpu_rates)
        max_gpu = max(gpu_rates)
        speedup = max_gpu / max_cpu if max_cpu > 0 else 0
        
        print(f"💻 Peak CPU Performance:  {max_cpu:.1f} signatures/sec")
        print(f"🚀 Peak GPU Performance:  {max_gpu:.1f} events/sec") 
        print(f"⚡ GPU Speedup:          {speedup:.1f}x faster")
        
        if speedup > 2.0:
            print("🎉 Significant GPU acceleration detected!")
        elif speedup > 1.2:
            print("✅ Moderate GPU acceleration detected")
        else:
            print("⚠️  Limited GPU acceleration - check GPU utilization")
            
        print(f"\n📈 CPU Throughput Range: {min(cpu_rates):.1f} - {max_cpu:.1f} signatures/sec")
        print(f"📈 GPU Throughput Range: {min(gpu_rates):.1f} - {max_gpu:.1f} events/sec")
        
    else:
        print("❌ Could not extract performance data from benchmark files")
        if not cpu_rates:
            print("   Missing CPU benchmark data")
        if not gpu_rates:
            print("   Missing GPU benchmark data")

if __name__ == "__main__":
    main()
EOF

    python3 benchmark_comparison.py
}

# Cleanup function
cleanup() {
    if [ "$STARTED_CONTAINER" = true ]; then
        echo "🧹 Cleaning up Docker container..."
        docker stop nostr-bench-relay 2>/dev/null || true
        docker rm nostr-bench-relay 2>/dev/null || true
    fi
}

# Set trap for cleanup
trap cleanup EXIT

# Main execution
main() {
    # Check for dependencies
    if [ ! -f "requirements-bench.txt" ]; then
        echo "❌ requirements-bench.txt not found"
        exit 1
    fi
    
    # Setup
    setup_deps
    
    # Run benchmarks
    run_cpu_benchmark
    run_gpu_benchmark
    
    # Generate report
    generate_report
    
    echo ""
    echo "🏁 Benchmark suite completed!"
    echo "📄 Results saved to:"
    echo "   - cpu_benchmark_results.txt"
    echo "   - gpu_benchmark_results.txt"
    echo ""
    echo "💡 Tips for optimization:"
    echo "   - Monitor GPU utilization with: nvidia-smi"
    echo "   - Check cuECC library loading with: ldd /usr/local/lib/libcuecc.so"
    echo "   - Increase batch sizes for better GPU utilization"
}

# Parse command line arguments
case "${1:-}" in
    "cpu-only")
        setup_deps
        run_cpu_benchmark
        ;;
    "gpu-only")
        setup_deps
        run_gpu_benchmark
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [cpu-only|gpu-only|help]"
        echo ""
        echo "Options:"
        echo "  cpu-only    Run only CPU benchmark"
        echo "  gpu-only    Run only GPU relay benchmark"  
        echo "  help        Show this help message"
        echo ""
        echo "Default: Run full benchmark suite (CPU + GPU + comparison)"
        ;;
    *)
        main
        ;;
esac 