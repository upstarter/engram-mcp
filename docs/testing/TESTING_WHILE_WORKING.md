# Testing ChainMind Integration While Working

## Quick Start: 2-Minute Test

### Step 1: Run Quick Test

```bash
cd /mnt/dev/ai/engram-mcp
python test_quick.py
```

**Expected Output**:
```
🔍 Testing ChainMind Integration

1. Checking availability...
   ✓ ChainMind available: True

2. Performing health check...
   ✓ Router initialized: True
   ✓ Healthy: True

3. Testing generation...
   ✓ Success!
   Provider: anthropic
   Response: Hello, ChainMind!...
   From cache: False
   Latency: 1.23s

4. Testing cache...
   First request (cache miss): True
   Second request (cache hit): True
   ✓ Cache working: True

5. Metrics:
   Total requests: 3
   Cache hits: 1
   Cache misses: 2
   Cache hit rate: 33.33%
   Avg latency: 0.82s
   Provider usage: {'anthropic': 2}

✅ Quick test complete!
```

### Step 2: Test in Claude Code

**In Claude Code**, try this:

```
Use the chainmind_generate tool with:
- prompt: "Write a Python function to calculate factorial"
- prefer_claude: true
```

**What to look for**:
- Response comes back
- Check the metadata footer (should show provider and latency)
- Try the same prompt again - should be instant (cache hit)

## Daily Usage Testing

### While You Work

**Just use it normally** - the integration is transparent:

1. **Ask Claude questions** using `chainmind_generate`
2. **Repeat similar questions** - notice they're faster (cache)
3. **Check metrics occasionally** - see your usage patterns

### Monitor Performance

**Create a simple monitor script** (`monitor.py`):

```python
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
```

**Run it**:
```bash
cd /mnt/dev/ai/engram-mcp
python monitor.py
```

## Testing Specific Features

### Test 1: Cache Functionality

**In Claude Code**:
1. Call `chainmind_generate` with: `"What is Python?"`
2. Note the latency (e.g., 1.5s)
3. Call again with the exact same prompt
4. Should be instant (<0.1s) and show `from_cache: true`

**Verify**:
```python
from engram.chainmind_helper import get_helper
h = get_helper()
m = h.get_metrics()
print(f"Cache hit rate: {m['cache_hit_rate_percent']}%")
```

### Test 2: Fallback Mechanism

**Option A: Simulate (Safe)**:
```python
# Test fallback without actually hitting limits
from engram.chainmind_helper import get_helper
import asyncio

async def test_fallback():
    helper = get_helper()
    # Force fallback by not preferring Claude
    result = await helper.generate(
        "test prompt",
        prefer_claude=False  # Will use ChainMind's routing
    )
    print(f"Provider used: {result['provider']}")

asyncio.run(test_fallback())
```

**Option B: Real Test (Requires hitting limit)**:
- Wait until Claude hits usage limit naturally
- Make a request
- Should automatically use fallback provider
- Check logs for fallback messages

### Test 3: Batch Processing

**In Claude Code**:
```
Tool: chainmind_generate_batch
Arguments:
  prompts: [
    "What is Python?",
    "What is JavaScript?",
    "What is Rust?"
  ]
```

**What to observe**:
- All prompts processed
- Results returned together
- Faster than 3 individual calls

### Test 4: Error Handling

**Test validation errors**:
```
Tool: chainmind_generate
Arguments:
  prompt: ""  # Empty prompt
```

**Expected**: Clear error message about empty prompt

**Test token limits** (if configured):
```python
# If you set max_tokens_per_request in config
from engram.chainmind_helper import get_helper
helper = get_helper()
helper._max_tokens_per_request = 100  # Small limit

# This should fail validation
try:
    await helper.generate("x" * 10000, max_tokens=1000)
except ValueError as e:
    print(f"Caught limit error: {e}")
```

### Test 5: Health Tracking

**Check provider health**:
```python
from engram.chainmind_helper import get_helper
helper = get_helper()

# Check health status
print("Provider health:", helper._provider_health)

# Simulate failures
helper._update_provider_health("anthropic", False)
helper._update_provider_health("anthropic", False)
helper._update_provider_health("anthropic", False)

# Should be unhealthy now
print("Anthropic healthy:", helper._check_provider_health("anthropic"))
# Should be False

# Success should recover
helper._update_provider_health("anthropic", True)
print("Anthropic healthy:", helper._check_provider_health("anthropic"))
# Should be True
```

## Integration Testing

### Full Workflow Test

**Simulate a real work session**:

```python
#!/usr/bin/env python3
"""Simulate real work session."""
import asyncio
import sys
import os
sys.path.insert(0, '/mnt/dev/ai/engram-mcp')

from engram.chainmind_helper import get_helper

async def work_session():
    helper = get_helper()

    # Common questions you might ask
    prompts = [
        "Write a Python function to reverse a string",
        "Write a Python function to reverse a string",  # Duplicate
        "Explain recursion",
        "What is a decorator in Python?",
        "Write a Python function to reverse a string",  # Duplicate again
    ]

    print("🔄 Simulating work session...\n")

    for i, prompt in enumerate(prompts, 1):
        print(f"Request {i}: {prompt[:50]}...")
        try:
            result = await helper.generate(prompt, prefer_claude=True)
            cache_status = "✅ CACHED" if result.get('from_cache') else "🔄 NEW"
            print(f"  {cache_status} | Provider: {result['provider']} | Latency: {result.get('latency_seconds', 0):.2f}s")
        except Exception as e:
            print(f"  ❌ Error: {e}")
        print()

    # Show final metrics
    metrics = helper.get_metrics()
    print("📊 Session Summary:")
    print(f"  Total requests: {metrics['total_requests']}")
    print(f"  Cache hits: {metrics['cache_hits']}")
    print(f"  Cache hit rate: {metrics['cache_hit_rate_percent']}%")
    print(f"  Avg latency: {metrics['average_latency_seconds']:.2f}s")

asyncio.run(work_session())
```

## Continuous Monitoring

### Watch Logs

**Terminal 1** - Watch for ChainMind activity:
```bash
# If running MCP server, logs go to stderr
# Look for correlation IDs and provider info
```

### Check Metrics Periodically

**Add to your workflow**:
```bash
# Quick metrics check
cd /mnt/dev/ai/engram-mcp && python monitor.py
```

### Alert on Issues

**Create alert script** (`check_health.py`):

```python
#!/usr/bin/env python3
"""Check ChainMind health and alert on issues."""
import sys
import os
import asyncio
sys.path.insert(0, '/mnt/dev/ai/engram-mcp')

async def check_health():
    from engram.chainmind_helper import get_helper

    helper = get_helper()

    # Check availability
    if not helper.is_available():
        print("⚠️  ChainMind not available!")
        return

    # Health check
    health = await helper.health_check()
    if not health['healthy']:
        print(f"⚠️  ChainMind unhealthy: {health.get('test_error', 'Unknown')}")
        return

    # Check metrics
    metrics = helper.get_metrics()

    # Alert on high fallback rate
    if metrics['total_requests'] > 10:
        fallback_rate = metrics['fallback_requests'] / metrics['total_requests']
        if fallback_rate > 0.5:
            print(f"⚠️  High fallback rate: {fallback_rate*100:.1f}%")

    # Alert on low cache hit rate
    if metrics['cache_hit_rate_percent'] < 10 and metrics['total_requests'] > 20:
        print(f"⚠️  Low cache hit rate: {metrics['cache_hit_rate_percent']}%")

    # Alert on high error rate
    error_rate = metrics['failed_requests'] / metrics['total_requests'] if metrics['total_requests'] > 0 else 0
    if error_rate > 0.1:
        print(f"⚠️  High error rate: {error_rate*100:.1f}%")

    print("✅ All checks passed")

asyncio.run(check_health())
```

## Testing Checklist

### Initial Setup
- [ ] ChainMind path correct
- [ ] API keys configured
- [ ] Dependencies installed
- [ ] Quick test passes

### Basic Functionality
- [ ] Can generate responses
- [ ] Cache works (repeat prompts are instant)
- [ ] Metrics are collected
- [ ] Logs include correlation IDs

### Error Handling
- [ ] Validation errors are clear
- [ ] Empty prompts are rejected
- [ ] Token limits are enforced (if configured)
- [ ] Errors include helpful context

### Fallback
- [ ] Fallback providers configured
- [ ] Health tracking works
- [ ] Parallel fallback is faster
- [ ] Error aggregation works

### Performance
- [ ] Cache hit rate >30% for repeated work
- [ ] Average latency <2s
- [ ] Batch processing works
- [ ] Concurrent requests handled

## Troubleshooting Guide

### Issue: "ChainMind not available"

**Check**:
```bash
# 1. Verify ChainMind path
ls -la /mnt/dev/ai/ai-platform/chainmind

# 2. Check API keys
cat /mnt/dev/ai/ai-platform/chainmind/.env | grep API_KEY

# 3. Check initialization
cd /mnt/dev/ai/engram-mcp
python -c "from engram.chainmind_helper import get_helper; h = get_helper(); print(h.get_usage_status())"
```

### Issue: Cache not working

**Check**:
```python
from engram.chainmind_helper import get_helper
h = get_helper()
print("Cache size:", len(h._response_cache))
print("Cache max:", h._cache_size)
print("Metrics:", h.get_metrics()['cache_hit_rate_percent'])
```

**Fix**: Ensure prompts are identical (including parameters)

### Issue: Fallback not working

**Check**:
```python
from engram.chainmind_helper import get_helper
h = get_helper()
print("Fallback providers:", h._fallback_providers)
print("Provider health:", h._provider_health)
```

**Fix**: Verify fallback providers have valid API keys

## Best Practices for Testing

1. **Start Simple**: Test basic generation first
2. **Test Cache**: Verify caching works with repeated prompts
3. **Monitor Metrics**: Check performance regularly
4. **Test Errors**: Verify error handling works
5. **Test Fallback**: Ensure fallback works when needed

## Summary

The integration is designed to work transparently - you can just use it and it works. But you can also:

- **Monitor**: Check metrics to see performance
- **Test**: Run tests to verify functionality
- **Debug**: Use correlation IDs to trace issues
- **Optimize**: Adjust config based on usage patterns

The system provides full visibility while remaining easy to use.
