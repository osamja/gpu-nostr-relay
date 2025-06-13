#!/usr/bin/env python3
"""
GPU monitoring script to track utilization during benchmarks
"""

import subprocess
import time
import sys
import threading
from datetime import datetime

class GPUMonitor:
    def __init__(self):
        self.monitoring = False
        self.gpu_data = []
        
    def check_nvidia_smi(self):
        """Check if nvidia-smi is available"""
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'], 
                                  capture_output=True, text=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def get_gpu_stats(self):
        """Get current GPU utilization stats"""
        try:
            result = subprocess.run([
                'nvidia-smi', 
                '--query-gpu=gpu_name,utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu',
                '--format=csv,noheader,nounits'
            ], capture_output=True, text=True, check=True)
            
            lines = result.stdout.strip().split('\n')
            gpu_stats = []
            
            for line in lines:
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 6:
                    gpu_stats.append({
                        'name': parts[0],
                        'gpu_util': int(parts[1]),
                        'mem_util': int(parts[2]),
                        'mem_used': int(parts[3]),
                        'mem_total': int(parts[4]),
                        'temp': int(parts[5]),
                        'timestamp': datetime.now()
                    })
            
            return gpu_stats
            
        except (subprocess.CalledProcessError, ValueError):
            return []
    
    def monitor_loop(self, interval=1.0):
        """Main monitoring loop"""
        print("🔍 Starting GPU monitoring...")
        print("GPU Name | GPU% | Mem% | Memory | Temp | Time")
        print("-" * 60)
        
        while self.monitoring:
            stats = self.get_gpu_stats()
            
            for gpu_stat in stats:
                self.gpu_data.append(gpu_stat)
                
                # Print current stats
                print(f"{gpu_stat['name'][:15]:<15} | "
                      f"{gpu_stat['gpu_util']:3}% | "
                      f"{gpu_stat['mem_util']:3}% | "
                      f"{gpu_stat['mem_used']:5}/{gpu_stat['mem_total']:5}MB | "
                      f"{gpu_stat['temp']:2}°C | "
                      f"{gpu_stat['timestamp'].strftime('%H:%M:%S')}")
            
            time.sleep(interval)
    
    def start_monitoring(self, interval=1.0):
        """Start monitoring in background thread"""
        if not self.check_nvidia_smi():
            print("❌ nvidia-smi not found. Cannot monitor GPU.")
            return False
            
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop, args=(interval,))
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        return True
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=2.0)
    
    def print_summary(self):
        """Print monitoring summary"""
        if not self.gpu_data:
            print("No GPU data collected")
            return
        
        print("\n" + "=" * 50)
        print("📊 GPU UTILIZATION SUMMARY")
        print("=" * 50)
        
        # Group by GPU name
        gpu_groups = {}
        for data in self.gpu_data:
            name = data['name']
            if name not in gpu_groups:
                gpu_groups[name] = []
            gpu_groups[name].append(data)
        
        for gpu_name, data_points in gpu_groups.items():
            if not data_points:
                continue
                
            gpu_utils = [d['gpu_util'] for d in data_points]
            mem_utils = [d['mem_util'] for d in data_points]
            temps = [d['temp'] for d in data_points]
            
            print(f"\n🖥️  {gpu_name}")
            print(f"   GPU Utilization: {min(gpu_utils):3}% - {max(gpu_utils):3}% (avg: {sum(gpu_utils)/len(gpu_utils):.1f}%)")
            print(f"   Memory Usage:    {min(mem_utils):3}% - {max(mem_utils):3}% (avg: {sum(mem_utils)/len(mem_utils):.1f}%)")
            print(f"   Temperature:     {min(temps):3}°C - {max(temps):3}°C (avg: {sum(temps)/len(temps):.1f}°C)")
            print(f"   Samples:         {len(data_points)}")
            
            # Check for good GPU utilization
            avg_gpu_util = sum(gpu_utils) / len(gpu_utils)
            if avg_gpu_util > 50:
                print("   ✅ Good GPU utilization detected!")
            elif avg_gpu_util > 20:
                print("   ⚠️  Moderate GPU utilization")
            else:
                print("   ❌ Low GPU utilization - check if GPU acceleration is working")

def main():
    """Main monitoring function"""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("GPU Monitor for Nostr Relay Benchmarks")
        print("Usage: python3 monitor_gpu.py [interval_seconds]")
        print("       python3 monitor_gpu.py --help")
        print("")
        print("Default interval: 1 second")
        print("Press Ctrl+C to stop monitoring")
        return
    
    interval = 1.0
    if len(sys.argv) > 1:
        try:
            interval = float(sys.argv[1])
        except ValueError:
            print("Invalid interval. Using default 1 second.")
    
    monitor = GPUMonitor()
    
    if not monitor.start_monitoring(interval):
        sys.exit(1)
    
    try:
        # Keep the main thread alive
        while monitor.monitoring:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping GPU monitoring...")
        monitor.stop_monitoring()
        monitor.print_summary()

if __name__ == "__main__":
    main() 