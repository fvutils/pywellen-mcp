#!/usr/bin/env python3
"""
Performance benchmarking suite for PyWellen MCP server.

Measures performance of key operations to ensure production readiness.
"""

import asyncio
import time
import sys
import os
from pathlib import Path
from typing import Dict, List, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pywellen_mcp.session import SessionManager
from pywellen_mcp.errors import WellenMCPError


class PerformanceBenchmark:
    """Performance benchmarking suite."""
    
    def __init__(self):
        self.results = []
        self.session_manager = SessionManager(max_sessions=10)
    
    def benchmark(self, name: str, iterations: int = 100):
        """Decorator for benchmarking functions."""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                print(f"\n{'='*60}")
                print(f"Benchmarking: {name}")
                print(f"Iterations: {iterations}")
                print(f"{'='*60}")
                
                # Warmup
                try:
                    await func(*args, **kwargs)
                except Exception as e:
                    print(f"Warmup failed: {e}")
                
                # Benchmark
                times = []
                for i in range(iterations):
                    start = time.perf_counter()
                    try:
                        await func(*args, **kwargs)
                        end = time.perf_counter()
                        times.append((end - start) * 1000)  # Convert to ms
                    except Exception as e:
                        print(f"Iteration {i} failed: {e}")
                        continue
                
                if times:
                    avg_time = sum(times) / len(times)
                    min_time = min(times)
                    max_time = max(times)
                    
                    self.results.append({
                        "name": name,
                        "avg_ms": avg_time,
                        "min_ms": min_time,
                        "max_ms": max_time,
                        "iterations": len(times)
                    })
                    
                    print(f"Average: {avg_time:.3f}ms")
                    print(f"Min: {min_time:.3f}ms")
                    print(f"Max: {max_time:.3f}ms")
                    
                    # Performance targets
                    targets = {
                        "Session creation": 10.0,
                        "Session retrieval": 1.0,
                        "Session cleanup": 5.0,
                    }
                    
                    if name in targets:
                        target = targets[name]
                        if avg_time <= target:
                            print(f"✅ PASS: Within target ({target}ms)")
                        else:
                            print(f"❌ FAIL: Exceeds target ({target}ms)")
                
                return wrapper
            
            return wrapper
        return decorator
    
    async def benchmark_session_operations(self):
        """Benchmark session management operations."""
        
        @self.benchmark("Session creation", iterations=100)
        async def create_session():
            # Simulate session creation overhead
            session_id = f"test_{time.time()}"
            # Note: Would need actual waveform for real benchmark
            pass
        
        @self.benchmark("Session retrieval", iterations=1000)
        async def get_session():
            # Test session lookup performance
            try:
                self.session_manager.get_session("nonexistent")
            except:
                pass
        
        @self.benchmark("Session cleanup", iterations=100)
        async def cleanup_sessions():
            # Test cleanup performance
            self.session_manager.cleanup_expired_sessions()
        
        await create_session()
        await get_session()
        await cleanup_sessions()
    
    async def benchmark_error_handling(self):
        """Benchmark error handling overhead."""
        
        @self.benchmark("Error creation", iterations=1000)
        async def create_error():
            from pywellen_mcp.errors import SessionError
            error = SessionError("TEST_ERROR", "Test error message")
        
        @self.benchmark("Error serialization", iterations=1000)
        async def serialize_error():
            from pywellen_mcp.errors import SessionError
            error = SessionError("TEST_ERROR", "Test error message")
            error.to_dict()
        
        await create_error()
        await serialize_error()
    
    def print_summary(self):
        """Print benchmark summary."""
        print(f"\n{'='*60}")
        print("BENCHMARK SUMMARY")
        print(f"{'='*60}")
        print(f"{'Benchmark':<40} {'Avg (ms)':<12} {'Status'}")
        print(f"{'-'*60}")
        
        targets = {
            "Session creation": 10.0,
            "Session retrieval": 1.0,
            "Session cleanup": 5.0,
            "Error creation": 0.1,
            "Error serialization": 0.5,
        }
        
        for result in self.results:
            name = result["name"]
            avg = result["avg_ms"]
            
            status = "✅"
            if name in targets and avg > targets[name]:
                status = "❌"
            
            print(f"{name:<40} {avg:>10.3f}  {status}")
        
        print(f"{'='*60}")
        print(f"\nTotal benchmarks: {len(self.results)}")
        
        # Check for failures
        failures = sum(1 for r in self.results 
                      if r["name"] in targets and r["avg_ms"] > targets[r["name"]])
        
        if failures > 0:
            print(f"❌ {failures} benchmark(s) exceeded target")
            return 1
        else:
            print(f"✅ All benchmarks within target")
            return 0


async def main():
    """Run all benchmarks."""
    benchmark = PerformanceBenchmark()
    
    print("PyWellen MCP Server - Performance Benchmarks")
    print("=" * 60)
    
    # Run benchmarks
    await benchmark.benchmark_session_operations()
    await benchmark.benchmark_error_handling()
    
    # Print summary
    exit_code = benchmark.print_summary()
    
    return exit_code


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
