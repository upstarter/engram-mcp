# Installing ChainMind Dependencies

## Issue

ChainMind integration requires `aiofiles` which may not be installed in your engram-mcp environment.

## Quick Fix

Install the missing dependency:

```bash
cd /mnt/dev/ai/engram-mcp
pip install aiofiles
```

Or install all ChainMind optional dependencies:

```bash
pip install -e ".[chainmind]"
```

## Verification

After installing, verify the integration:

```bash
python3 verify_chainmind_integration.py
```

Expected: All tests pass ✅

## Optional Dependencies

The `chainmind` optional dependency group includes:
- `aiofiles>=23.0.0` - Required by ChainMind's io_manager

## Note

If ChainMind is not fully configured, engram-mcp will still work normally. The ChainMind tools will gracefully degrade and report "ChainMind helper not available" when used.
