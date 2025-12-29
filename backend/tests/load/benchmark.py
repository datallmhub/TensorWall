#!/usr/bin/env python3
"""
Simple benchmark script for quick performance testing.

Usage: python tests/load/benchmark.py [--requests N] [--concurrent N]
"""

import asyncio
import aiohttp
import argparse
import time
import statistics
from dataclasses import dataclass
from typing import Optional


@dataclass
class BenchmarkResult:
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_time_seconds: float
    requests_per_second: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float


async def make_request(
    session: aiohttp.ClientSession, url: str, payload: dict, headers: dict
) -> tuple[bool, float, Optional[str]]:
    """Make a single request and return (success, latency_ms, error)."""
    start = time.perf_counter()
    try:
        async with session.post(url, json=payload, headers=headers) as resp:
            latency = (time.perf_counter() - start) * 1000
            if resp.status in (200, 429):  # Success or rate limited
                return True, latency, None
            else:
                text = await resp.text()
                return False, latency, f"Status {resp.status}: {text[:100]}"
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return False, latency, str(e)


async def run_benchmark(
    base_url: str,
    total_requests: int,
    concurrent: int,
    api_key: str,
) -> BenchmarkResult:
    """Run the benchmark."""
    url = f"{base_url}/v1/chat/completions"
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "model": "phi-2",
        "messages": [
            {"role": "user", "content": "Hello, benchmark test!"},
        ],
        "max_tokens": 20,
    }

    latencies = []
    successes = 0
    failures = 0
    errors = []

    print(f"\nRunning benchmark: {total_requests} requests, {concurrent} concurrent")
    print("-" * 50)

    connector = aiohttp.TCPConnector(limit=concurrent)
    timeout = aiohttp.ClientTimeout(total=30)

    start_time = time.perf_counter()

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(concurrent)

        async def bounded_request():
            async with semaphore:
                return await make_request(session, url, payload, headers)

        # Create all tasks
        tasks = [bounded_request() for _ in range(total_requests)]

        # Progress tracking
        completed = 0
        for coro in asyncio.as_completed(tasks):
            success, latency, error = await coro
            latencies.append(latency)
            if success:
                successes += 1
            else:
                failures += 1
                if error and len(errors) < 5:
                    errors.append(error)

            completed += 1
            if completed % 100 == 0 or completed == total_requests:
                print(
                    f"  Progress: {completed}/{total_requests} ({completed / total_requests * 100:.1f}%)"
                )

    total_time = time.perf_counter() - start_time
    rps = total_requests / total_time

    # Calculate percentiles
    sorted_latencies = sorted(latencies)
    p50_idx = int(len(sorted_latencies) * 0.50)
    p95_idx = int(len(sorted_latencies) * 0.95)
    p99_idx = int(len(sorted_latencies) * 0.99)

    result = BenchmarkResult(
        total_requests=total_requests,
        successful_requests=successes,
        failed_requests=failures,
        total_time_seconds=total_time,
        requests_per_second=rps,
        avg_latency_ms=statistics.mean(latencies),
        min_latency_ms=min(latencies),
        max_latency_ms=max(latencies),
        p50_latency_ms=sorted_latencies[p50_idx],
        p95_latency_ms=sorted_latencies[p95_idx],
        p99_latency_ms=sorted_latencies[p99_idx],
    )

    return result, errors


def print_results(result: BenchmarkResult, errors: list[str]):
    """Print benchmark results."""
    print("\n" + "=" * 50)
    print("BENCHMARK RESULTS")
    print("=" * 50)

    print("\n📊 Throughput:")
    print(f"   Total requests:     {result.total_requests}")
    print(
        f"   Successful:         {result.successful_requests} ({result.successful_requests / result.total_requests * 100:.1f}%)"
    )
    print(
        f"   Failed:             {result.failed_requests} ({result.failed_requests / result.total_requests * 100:.1f}%)"
    )
    print(f"   Total time:         {result.total_time_seconds:.2f}s")
    print(f"   Requests/second:    {result.requests_per_second:.2f}")

    print("\n⏱️  Latency (ms):")
    print(f"   Average:            {result.avg_latency_ms:.2f}")
    print(f"   Min:                {result.min_latency_ms:.2f}")
    print(f"   Max:                {result.max_latency_ms:.2f}")
    print(f"   P50 (median):       {result.p50_latency_ms:.2f}")
    print(f"   P95:                {result.p95_latency_ms:.2f}")
    print(f"   P99:                {result.p99_latency_ms:.2f}")

    if errors:
        print(f"\n❌ Sample errors ({len(errors)} shown):")
        for err in errors:
            print(f"   - {err}")

    # Performance grade
    print("\n🎯 Performance Grade:")
    if result.p95_latency_ms < 100 and result.requests_per_second > 100:
        print("   ⭐⭐⭐⭐⭐ EXCELLENT")
    elif result.p95_latency_ms < 200 and result.requests_per_second > 50:
        print("   ⭐⭐⭐⭐ GOOD")
    elif result.p95_latency_ms < 500 and result.requests_per_second > 20:
        print("   ⭐⭐⭐ ACCEPTABLE")
    elif result.p95_latency_ms < 1000:
        print("   ⭐⭐ NEEDS IMPROVEMENT")
    else:
        print("   ⭐ POOR")

    print("=" * 50)


async def main():
    parser = argparse.ArgumentParser(description="TensorWall Benchmark")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL")
    parser.add_argument("--requests", "-n", type=int, default=1000, help="Total requests")
    parser.add_argument("--concurrent", "-c", type=int, default=50, help="Concurrent requests")
    parser.add_argument("--api-key", default=None, help="API key (required)")
    args = parser.parse_args()

    print("🚀 TensorWall Benchmark Tool")
    print(f"   Target: {args.url}")
    print(f"   Requests: {args.requests}")
    print(f"   Concurrency: {args.concurrent}")

    result, errors = await run_benchmark(
        base_url=args.url,
        total_requests=args.requests,
        concurrent=args.concurrent,
        api_key=args.api_key,
    )

    print_results(result, errors)


if __name__ == "__main__":
    asyncio.run(main())
