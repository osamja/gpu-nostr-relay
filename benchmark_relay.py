#!/usr/bin/env python3
"""
Comprehensive benchmark suite for GPU-accelerated Nostr relay
Tests signature verification performance, event throughput, and concurrency
"""

import asyncio
import websockets
import json
import hashlib
import time
import secrets
import statistics
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple
import secp256k1
import aiohttp
import os
import sys

@dataclass
class BenchmarkResult:
    """Container for benchmark results"""
    test_name: str
    duration: float
    events_processed: int
    events_per_second: float
    success_rate: float
    latency_stats: Dict[str, float]  # min, max, mean, median, p95, p99
    additional_metrics: Dict[str, Any] = None

class NostrEventGenerator:
    """Generate valid Nostr events with real signatures for benchmarking"""
    
    def __init__(self):
        self.private_key = secp256k1.PrivateKey()
        # Nostr uses 32-byte x-coordinate from uncompressed key
        pubkey_full = self.private_key.pubkey.serialize(compressed=False)
        self.public_key = pubkey_full[1:33]  # Remove 0x04 prefix, take x-coordinate
        
    def create_event(self, content: str = None, kind: int = 1) -> Dict[str, Any]:
        """Create a valid Nostr event with proper signature"""
        if content is None:
            content = f"Benchmark event {secrets.token_hex(8)}"
            
        event = {
            "kind": kind,
            "created_at": int(time.time()),
            "tags": [],
            "content": content,
            "pubkey": self.public_key.hex(),
        }
        
        # Create the event hash
        event_str = json.dumps([
            0,
            event["pubkey"],
            event["created_at"],
            event["kind"],
            event["tags"],
            event["content"]
        ], separators=(',', ':'), ensure_ascii=False)
        
        event_hash = hashlib.sha256(event_str.encode()).digest()
        event["id"] = event_hash.hex()
        
        # Sign the event
        signature = self.private_key.ecdsa_sign(event_hash)
        # Use the simpler serialize_compact method
        event["sig"] = self.private_key.ecdsa_serialize_compact(signature).hex()
        
        return event

class RelayBenchmark:
    """Main benchmark class"""
    
    def __init__(self, relay_url: str = "ws://localhost:6969"):
        self.relay_url = relay_url
        self.event_generator = NostrEventGenerator()
        self.results: List[BenchmarkResult] = []
        
    async def _measure_latencies(self, operation_func, iterations: int) -> Tuple[List[float], int]:
        """Measure latencies for a given operation"""
        latencies = []
        successes = 0
        
        for _ in range(iterations):
            start_time = time.perf_counter()
            try:
                success = await operation_func()
                latency = (time.perf_counter() - start_time) * 1000  # Convert to ms
                latencies.append(latency)
                if success:
                    successes += 1
            except Exception as e:
                print(f"Operation failed: {e}")
                
        return latencies, successes
    
    def _calculate_latency_stats(self, latencies: List[float]) -> Dict[str, float]:
        """Calculate latency statistics"""
        if not latencies:
            return {"min": 0, "max": 0, "mean": 0, "median": 0, "p95": 0, "p99": 0}
            
        sorted_latencies = sorted(latencies)
        return {
            "min": min(latencies),
            "max": max(latencies),
            "mean": statistics.mean(latencies),
            "median": statistics.median(latencies),
            "p95": sorted_latencies[int(0.95 * len(sorted_latencies))],
            "p99": sorted_latencies[int(0.99 * len(sorted_latencies))]
        }

    async def benchmark_signature_verification_throughput(self, batch_sizes: List[int] = [1, 10, 50, 100, 500, 1000]) -> None:
        """Benchmark signature verification throughput with different batch sizes"""
        print("🔄 Benchmarking signature verification throughput...")
        
        for batch_size in batch_sizes:
            print(f"  Testing batch size: {batch_size}")
            
            # Generate events in advance
            events = [self.event_generator.create_event() for _ in range(batch_size)]
            
            async def submit_batch():
                try:
                    async with websockets.connect(self.relay_url) as websocket:
                        start_time = time.perf_counter()
                        
                        # Submit all events
                        for event in events:
                            await websocket.send(json.dumps(["EVENT", event]))
                        
                        # Wait for all responses
                        responses = []
                        for _ in range(batch_size):
                            try:
                                response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                                responses.append(json.loads(response))
                            except asyncio.TimeoutError:
                                break
                        
                        end_time = time.perf_counter()
                        
                        # Count successful verifications
                        accepted = sum(1 for resp in responses if len(resp) >= 3 and resp[2])
                        return end_time - start_time, accepted, len(responses)
                        
                except Exception as e:
                    print(f"Batch submission failed: {e}")
                    return None, 0, 0
            
            duration, accepted, total_responses = await submit_batch()
            
            if duration is not None:
                events_per_second = batch_size / duration if duration > 0 else 0
                success_rate = accepted / batch_size if batch_size > 0 else 0
                
                result = BenchmarkResult(
                    test_name=f"Signature Verification (batch_size={batch_size})",
                    duration=duration,
                    events_processed=batch_size,
                    events_per_second=events_per_second,
                    success_rate=success_rate,
                    latency_stats={"batch_latency_ms": duration * 1000},
                    additional_metrics={
                        "batch_size": batch_size,
                        "accepted_events": accepted,
                        "total_responses": total_responses
                    }
                )
                
                self.results.append(result)
                print(f"    ✅ {events_per_second:.1f} events/sec, {success_rate:.1%} success rate")
            else:
                print(f"    ❌ Batch failed")

    async def benchmark_concurrent_connections(self, num_connections: int = 100, events_per_connection: int = 10) -> None:
        """Benchmark handling of concurrent WebSocket connections"""
        print(f"🔄 Benchmarking {num_connections} concurrent connections...")
        
        async def single_connection_workload(connection_id: int):
            """Workload for a single connection"""
            try:
                async with websockets.connect(self.relay_url) as websocket:
                    events_sent = 0
                    events_accepted = 0
                    
                    for i in range(events_per_connection):
                        event = self.event_generator.create_event(
                            content=f"Connection {connection_id}, Event {i}"
                        )
                        
                        await websocket.send(json.dumps(["EVENT", event]))
                        events_sent += 1
                        
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                            resp_data = json.loads(response)
                            if len(resp_data) >= 3 and resp_data[2]:
                                events_accepted += 1
                        except asyncio.TimeoutError:
                            break
                    
                    return events_sent, events_accepted
                    
            except Exception as e:
                print(f"Connection {connection_id} failed: {e}")
                return 0, 0
        
        start_time = time.perf_counter()
        
        # Run all connections concurrently
        tasks = [single_connection_workload(i) for i in range(num_connections)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        # Aggregate results
        total_sent = 0
        total_accepted = 0
        successful_connections = 0
        
        for result in results:
            if isinstance(result, tuple):
                sent, accepted = result
                total_sent += sent
                total_accepted += accepted
                if sent > 0:
                    successful_connections += 1
        
        events_per_second = total_sent / duration if duration > 0 else 0
        success_rate = total_accepted / total_sent if total_sent > 0 else 0
        
        benchmark_result = BenchmarkResult(
            test_name=f"Concurrent Connections ({num_connections} connections)",
            duration=duration,
            events_processed=total_sent,
            events_per_second=events_per_second,
            success_rate=success_rate,
            latency_stats={"total_duration_s": duration},
            additional_metrics={
                "num_connections": num_connections,
                "events_per_connection": events_per_connection,
                "successful_connections": successful_connections,
                "total_accepted": total_accepted
            }
        )
        
        self.results.append(benchmark_result)
        print(f"    ✅ {successful_connections}/{num_connections} connections successful")
        print(f"    ✅ {events_per_second:.1f} events/sec total throughput")

    async def benchmark_event_query_performance(self, num_events_to_insert: int = 1000, query_variations: int = 10) -> None:
        """Benchmark event query performance after inserting many events"""
        print(f"🔄 Benchmarking query performance with {num_events_to_insert} events...")
        
        # First, populate the relay with events
        print("  Populating relay with test events...")
        async with websockets.connect(self.relay_url) as websocket:
            for i in range(num_events_to_insert):
                event = self.event_generator.create_event(
                    content=f"Query benchmark event {i}",
                    kind=1
                )
                await websocket.send(json.dumps(["EVENT", event]))
                
                # Don't wait for response to speed up insertion
                if i % 100 == 0:
                    print(f"    Inserted {i} events...")
        
        print("  Testing query performance...")
        
        async def single_query_test():
            """Perform a single query and measure performance"""
            try:
                async with websockets.connect(self.relay_url) as websocket:
                    # Random query filter
                    filter_obj = {
                        "kinds": [1],
                        "limit": 50,
                        "since": int(time.time()) - 3600  # Last hour
                    }
                    
                    start_time = time.perf_counter()
                    await websocket.send(json.dumps(["REQ", f"bench-{secrets.token_hex(4)}", filter_obj]))
                    
                    event_count = 0
                    try:
                        while True:
                            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                            resp_data = json.loads(response)
                            
                            if resp_data[0] == "EVENT":
                                event_count += 1
                            elif resp_data[0] == "EOSE":  # End of stored events
                                break
                    except asyncio.TimeoutError:
                        pass
                    
                    end_time = time.perf_counter()
                    return end_time - start_time, event_count
                    
            except Exception as e:
                print(f"Query failed: {e}")
                return 0, 0
        
        # Measure query latencies
        latencies, successes = await self._measure_latencies(
            lambda: single_query_test(),
            query_variations
        )
        
        if latencies:
            avg_latency = statistics.mean(latencies)
            latency_stats = self._calculate_latency_stats([l * 1000 for l in latencies])  # Convert to ms
            
            result = BenchmarkResult(
                test_name="Event Query Performance",
                duration=sum(latencies),
                events_processed=num_events_to_insert,
                events_per_second=0,  # Not applicable for queries
                success_rate=successes / query_variations,
                latency_stats=latency_stats,
                additional_metrics={
                    "num_queries": query_variations,
                    "events_in_db": num_events_to_insert
                }
            )
            
            self.results.append(result)
            print(f"    ✅ Average query latency: {avg_latency*1000:.1f}ms")

    async def benchmark_sustained_load(self, duration_seconds: int = 60, events_per_second_target: int = 100) -> None:
        """Benchmark sustained load over time"""
        print(f"🔄 Benchmarking sustained load for {duration_seconds}s at {events_per_second_target} events/sec...")
        
        event_interval = 1.0 / events_per_second_target
        start_time = time.perf_counter()
        events_sent = 0
        events_accepted = 0
        
        async with websockets.connect(self.relay_url) as websocket:
            while time.perf_counter() - start_time < duration_seconds:
                event = self.event_generator.create_event(
                    content=f"Sustained load event {events_sent}"
                )
                
                await websocket.send(json.dumps(["EVENT", event]))
                events_sent += 1
                
                # Check for response (non-blocking)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=0.001)
                    resp_data = json.loads(response)
                    if len(resp_data) >= 3 and resp_data[2]:
                        events_accepted += 1
                except asyncio.TimeoutError:
                    pass
                
                # Rate limiting
                await asyncio.sleep(event_interval)
                
                if events_sent % 100 == 0:
                    elapsed = time.perf_counter() - start_time
                    current_rate = events_sent / elapsed
                    print(f"    {events_sent} events sent, current rate: {current_rate:.1f}/sec")
        
        total_duration = time.perf_counter() - start_time
        actual_rate = events_sent / total_duration
        success_rate = events_accepted / events_sent if events_sent > 0 else 0
        
        result = BenchmarkResult(
            test_name="Sustained Load Test",
            duration=total_duration,
            events_processed=events_sent,
            events_per_second=actual_rate,
            success_rate=success_rate,
            latency_stats={"target_rate": events_per_second_target, "actual_rate": actual_rate},
            additional_metrics={
                "target_duration": duration_seconds,
                "events_accepted": events_accepted
            }
        )
        
        self.results.append(result)
        print(f"    ✅ Achieved {actual_rate:.1f} events/sec (target: {events_per_second_target})")

    def print_results_summary(self):
        """Print a comprehensive summary of all benchmark results"""
        print("\n" + "=" * 80)
        print("🏆 BENCHMARK RESULTS SUMMARY")
        print("=" * 80)
        
        for result in self.results:
            print(f"\n📊 {result.test_name}")
            print("-" * len(result.test_name))
            print(f"Duration: {result.duration:.2f}s")
            print(f"Events Processed: {result.events_processed:,}")
            if result.events_per_second > 0:
                print(f"Throughput: {result.events_per_second:.1f} events/sec")
            print(f"Success Rate: {result.success_rate:.1%}")
            
            if result.latency_stats:
                print("Latency Stats:")
                for key, value in result.latency_stats.items():
                    if 'ms' in key or key in ['min', 'max', 'mean', 'median', 'p95', 'p99']:
                        print(f"  {key}: {value:.2f}ms")
                    else:
                        print(f"  {key}: {value}")
            
            if result.additional_metrics:
                print("Additional Metrics:")
                for key, value in result.additional_metrics.items():
                    print(f"  {key}: {value}")
        
        # Overall summary
        throughput_results = [r for r in self.results if r.events_per_second > 0]
        if throughput_results:
            max_throughput = max(r.events_per_second for r in throughput_results)
            avg_success_rate = statistics.mean(r.success_rate for r in self.results)
            
            print(f"\n🎯 OVERALL PERFORMANCE")
            print(f"Peak Throughput: {max_throughput:.1f} events/sec")
            print(f"Average Success Rate: {avg_success_rate:.1%}")

    async def run_full_benchmark_suite(self):
        """Run the complete benchmark suite"""
        print("🚀 Starting GPU Nostr Relay Benchmark Suite")
        print("=" * 80)
        
        # Check if relay is accessible
        try:
            async with websockets.connect(self.relay_url, ping_timeout=5) as websocket:
                print(f"✅ Relay connection successful at {self.relay_url}")
        except Exception as e:
            print(f"❌ Cannot connect to relay at {self.relay_url}: {e}")
            return
        
        # Run benchmarks
        await self.benchmark_signature_verification_throughput()
        await self.benchmark_concurrent_connections(num_connections=50, events_per_connection=5)
        await self.benchmark_concurrent_connections(num_connections=100, events_per_connection=10)
        await self.benchmark_event_query_performance(num_events_to_insert=500)
        await self.benchmark_sustained_load(duration_seconds=30, events_per_second_target=50)
        await self.benchmark_sustained_load(duration_seconds=30, events_per_second_target=100)
        
        # Print results
        self.print_results_summary()

async def main():
    """Main benchmark entry point"""
    relay_url = os.environ.get("RELAY_URL", "ws://localhost:6969")
    
    print(f"GPU Nostr Relay Benchmark Suite")
    print(f"Target Relay: {relay_url}")
    print("=" * 50)
    
    benchmark = RelayBenchmark(relay_url)
    await benchmark.run_full_benchmark_suite()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Benchmark interrupted by user")
    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        sys.exit(1) 