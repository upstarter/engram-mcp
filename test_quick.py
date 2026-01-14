#!/usr/bin/env python3
"""Quick test of ChainMind integration."""
import asyncio
import sys
import os

sys.path.insert(0, '/mnt/dev/ai/engram-mcp')

async def main():
    from engram.chainmind_helper import get_helper
    
    print("🔍 Testing ChainMind Integration\n")
    
    helper = get_helper()
    
    # 1. Check availability
    print("1. Checking availability...")
    available = helper.is_available()
    print(f"   ✓ ChainMind available: {available}\n")
    
    if not available:
        print("   ⚠️  ChainMind not available. Check setup.")
        return
    
    # 2. Health check
    print("2. Performing health check...")
    health = await helper.health_check()
    print(f"   ✓ Router initialized: {health['router_initialized']}")
    print(f"   ✓ Healthy: {health['healthy']}\n")
    
    # 3. Test generation
    print("3. Testing generation...")
    try:
        result = await helper.generate(
            "Say 'Hello, ChainMind!' in one sentence.",
            prefer_claude=True
        )
        print(f"   ✓ Success!")
        print(f"   Provider: {result['provider']}")
        print(f"   Response: {result['response'][:80]}...")
        print(f"   From cache: {result.get('from_cache', False)}")
        print(f"   Latency: {result.get('latency_seconds', 0):.2f}s\n")
    except Exception as e:
        print(f"   ✗ Error: {e}\n")
    
    # 4. Test caching
    print("4. Testing cache...")
    try:
        # First request
        result1 = await helper.generate("What is 2+2?", prefer_claude=True)
        cache_miss = result1.get('from_cache', False)
        
        # Second request (should hit cache)
        result2 = await helper.generate("What is 2+2?", prefer_claude=True)
        cache_hit = result2.get('from_cache', False)
        
        print(f"   First request (cache miss): {not cache_miss}")
        print(f"   Second request (cache hit): {cache_hit}")
        print(f"   ✓ Cache working: {cache_hit}\n")
    except Exception as e:
        print(f"   ✗ Error: {e}\n")
    
    # 5. Check metrics
    print("5. Metrics:")
    metrics = helper.get_metrics()
    print(f"   Total requests: {metrics['total_requests']}")
    print(f"   Cache hits: {metrics['cache_hits']}")
    print(f"   Cache misses: {metrics['cache_misses']}")
    if metrics['total_requests'] > 0:
        print(f"   Cache hit rate: {metrics['cache_hit_rate_percent']}%")
        print(f"   Avg latency: {metrics['average_latency_seconds']:.2f}s")
    print(f"   Provider usage: {metrics['provider_usage']}\n")
    
    print("✅ Quick test complete!")

if __name__ == "__main__":
    asyncio.run(main())
