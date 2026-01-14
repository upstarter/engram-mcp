#!/usr/bin/env python3
"""Monitor ChainMind metrics."""
import sys
import os
sys.path.insert(0, '/mnt/dev/ai/engram-mcp')

from engram.chainmind_helper import get_helper

helper = get_helper()
metrics = helper.get_metrics()

print("📊 ChainMind Metrics")
print("=" * 50)
print(f"Total Requests:     {metrics['total_requests']}")
print(f"Successful:         {metrics['successful_requests']}")
print(f"Failed:             {metrics['failed_requests']}")
print(f"Cache Hits:         {metrics['cache_hits']}")
print(f"Cache Misses:       {metrics['cache_misses']}")
print(f"Cache Hit Rate:     {metrics['cache_hit_rate_percent']}%")
print(f"Avg Latency:        {metrics['average_latency_seconds']:.2f}s")
print(f"Fallback Requests:  {metrics['fallback_requests']}")
print("\nProvider Usage:")
for provider, count in metrics['provider_usage'].items():
    print(f"  {provider}: {count}")

if metrics['error_counts']:
    print("\nErrors:")
    for error_type, count in metrics['error_counts'].items():
        print(f"  {error_type}: {count}")

if metrics.get('connection_pool', {}).get('available'):
    pool = metrics['connection_pool']
    print(f"\nConnection Pool:")
    print(f"  Total Clients: {pool.get('total_clients', 0)}")
    print(f"  Active: {pool.get('active_clients', 0)}")
