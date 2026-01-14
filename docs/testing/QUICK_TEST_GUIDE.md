# Quick Test Guide - ChainMind Integration

## 5-Minute Quick Test

### Step 1: Verify Setup

```bash
# Check ChainMind is accessible
cd /mnt/dev/ai/ai-platform/chainmind
ls -la .env  # Should exist with API keys

# Check engram-mcp dependencies
cd /mnt/dev/ai/engram-mcp
pip list | grep -E "aiofiles|sentence-transformers"
```

### Step 2: Run Quick Test Script

Create `test_quick.py`:

```python
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
```

**Run it**:
```bash
cd /mnt/dev/ai/engram-mcp
python test_quick.py
```

### Step 3: Test in Claude Code

**In Claude Code**, try these tools:

1. **Basic generation**:
   ```
   Use chainmind_generate with prompt: "Explain recursion"
   ```

2. **Check if it worked**:
   - Look for response
   - Check if provider is mentioned
   - Note the latency

3. **Test cache**:
   - Use same prompt twice
   - Second should be instant

## Testing During Work

### Monitor Logs

**Watch logs in real-time**:
```bash
# Terminal 1: Watch for ChainMind logs
tail -f /dev/stderr 2>&1 | grep -i chainmind

# Or check engram logs if they're written to file
tail -f ~/.engram/logs/*.log 2>/dev/null || echo "No log files found"
```

### Check Status

**Quick status check**:
```python
from engram.chainmind_helper import get_helper

helper = get_helper()
print("Available:", helper.is_available())
print("Usage status:", helper.get_usage_status())
print("Metrics:", helper.get_metrics())
```

### Test Fallback (Simulated)

**To test fallback without actually hitting limits**:

1. Temporarily remove/rename Anthropic API key
2. Make a request
3. Should automatically use fallback provider
4. Restore API key

**Or** use `prefer_claude=False` to test fallback directly:
```
Tool: chainmind_generate
Arguments:
  prompt: "test"
  prefer_claude: false
```

## Common Test Scenarios

### Scenario 1: Normal Usage
```
✅ Expected: Claude responds normally
✅ Check: Provider is "anthropic", no fallback
```

### Scenario 2: Cache Hit
```
✅ Expected: Second identical request is instant
✅ Check: from_cache: true, latency < 0.1s
```

### Scenario 3: Fallback
```
✅ Expected: Uses alternative provider when Claude unavailable
✅ Check: fallback_used: true, provider is not "anthropic"
```

### Scenario 4: Batch Processing
```
✅ Expected: Multiple prompts processed concurrently
✅ Check: All results returned, faster than individual calls
```

### Scenario 5: Error Handling
```
✅ Expected: Clear error messages with context
✅ Check: Error includes correlation_id, helpful message
```

## What to Look For

### ✅ Good Signs

- **Fast responses**: <2s average latency
- **High cache hit rate**: >30% for repeated work
- **Low fallback rate**: <10% (means Claude is working)
- **Clear logs**: Correlation IDs visible, errors explained

### ⚠️ Warning Signs

- **High fallback rate**: >50% → Claude hitting limits frequently
- **Low cache hit rate**: <10% → Prompts too varied
- **High error rate**: >5% → Check provider health
- **Slow responses**: >5s → Check network/provider status

## Quick Debugging

### Issue: "ChainMind not available"

```bash
# Check initialization
cd /mnt/dev/ai/engram-mcp
python -c "from engram.chainmind_helper import get_helper; h = get_helper(); print(h.get_usage_status())"
```

### Issue: Cache not working

```python
# Check cache
from engram.chainmind_helper import get_helper
h = get_helper()
print("Cache size:", len(h._response_cache))
print("Cache max:", h._cache_size)
```

### Issue: Fallback not working

```python
# Check provider health
from engram.chainmind_helper import get_helper
h = get_helper()
print("Provider health:", h._provider_health)
print("Fallback providers:", h._fallback_providers)
```

## Integration with Your Workflow

### Daily Usage

1. **Just use it**: Call `chainmind_generate` as normal
2. **Monitor occasionally**: Check metrics weekly
3. **Adjust config**: Tune based on your usage patterns

### When Claude Hits Limits

1. **Automatic**: System handles it for you
2. **Transparent**: Logs show what happened
3. **Seamless**: You get response without interruption

### Optimizing Performance

1. **Reuse prompts**: Similar prompts benefit from cache
2. **Batch when possible**: Use batch tool for multiple prompts
3. **Monitor metrics**: Adjust based on cache hit rates

## Next Steps

1. **Run quick test**: Verify everything works
2. **Use in daily work**: Just call the tools normally
3. **Monitor metrics**: Check performance periodically
4. **Adjust config**: Tune based on your needs

The integration is designed to "just work" - you don't need to think about it, but you can monitor and optimize if desired.
