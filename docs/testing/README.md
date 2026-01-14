# Testing Guide

## Quick Test

```bash
cd /mnt/dev/ai/engram-mcp
pytest tests/ -v
```

## Test Categories

- **Unit Tests**: Component-level testing
- **Integration Tests**: Component interaction
- **End-to-End Tests**: Complete workflows
- **Trace Tests**: Request flow tracing

## Request Tracing

Use `trace_request_flow.py` to trace requests:

```bash
cd /mnt/dev/ai/engram-mcp
TRACE_EXECUTE=true python trace_request_flow.py
```

## Test Files

- `test_chainmind_helper_comprehensive.py` - Helper tests
- `test_prompt_generator_comprehensive.py` - Prompt generator tests
- `test_mcp_integration_comprehensive.py` - MCP integration tests
- `test_e2e_comprehensive.py` - End-to-end tests

## See Also

- [Testing While Working](./TESTING_WHILE_WORKING.md) - Development testing
- [Trace Usage](./TRACE_USAGE.md) - Request tracing guide
- [Quick Test Guide](./QUICK_TEST_GUIDE.md) - Quick testing

