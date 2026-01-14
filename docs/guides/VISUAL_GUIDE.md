# Visual Guide: How ChainMind Integration Works

## Request Flow Diagram

```mermaid
sequenceDiagram
    participant Claude as Claude Code
    participant MCP as engram-mcp MCP Server
    participant Helper as ChainMindHelper
    participant Cache as Response Cache
    participant Router as ChainMind Router
    participant ClaudeAPI as Claude API
    participant OpenAI as OpenAI API
    participant Ollama as Ollama API

    Claude->>MCP: chainmind_generate("prompt")
    MCP->>Helper: generate(prompt, prefer_claude=True)

    Helper->>Helper: Generate correlation_id
    Helper->>Helper: Validate request limits
    Helper->>Cache: Check cache

    alt Cache Hit
        Cache-->>Helper: Return cached response
        Helper-->>MCP: Response (from_cache=true)
        MCP-->>Claude: Response
    else Cache Miss
        Helper->>Router: route(prompt, provider="anthropic")
        Router->>ClaudeAPI: API call

        alt Claude Success
            ClaudeAPI-->>Router: Response
            Router-->>Helper: Result
            Helper->>Cache: Store result
            Helper-->>MCP: Response (provider="anthropic")
            MCP-->>Claude: Response
        else Claude Usage Limit
            ClaudeAPI-->>Router: QuotaExceededError
            Router-->>Helper: Error
            Helper->>Helper: Classify error → "quota_exceeded"
            Helper->>Helper: Try fallback providers (parallel)

            par Parallel Fallback
                Helper->>OpenAI: Try OpenAI
                Helper->>Ollama: Try Ollama
            end

            alt OpenAI Success
                OpenAI-->>Helper: Response
                Helper->>Cache: Store result
                Helper-->>MCP: Response (provider="openai", fallback_used=true)
                MCP-->>Claude: Response [Used openai (fallback)]
            else Ollama Success
                Ollama-->>Helper: Response
                Helper->>Cache: Store result
                Helper-->>MCP: Response (provider="ollama", fallback_used=true)
                MCP-->>Claude: Response [Used ollama (fallback)]
            else All Failed
                Helper-->>MCP: Aggregated Error
                MCP-->>Claude: Error with details
            end
        end
    end
```

## Component Interaction

```mermaid
graph TB
    subgraph "engram-mcp"
        MCP[MCP Server]
        Helper[ChainMindHelper]
        PromptGen[PromptGenerator]
    end

    subgraph "ChainMind"
        Router[TwoTierRouter]
        Strategic[StrategicRouter]
        Tactical[TacticalRouter]
        Pool[ClientPool]
    end

    subgraph "Providers"
        Claude[Claude API]
        OpenAI[OpenAI API]
        Ollama[Ollama API]
    end

    MCP -->|"chainmind_generate"| Helper
    MCP -->|"chainmind_generate_prompt"| PromptGen
    Helper -->|"route()"| Router
    Router --> Strategic
    Router --> Tactical
    Tactical --> Pool
    Pool --> Claude
    Pool --> OpenAI
    Pool --> Ollama

    Helper -.->|"caches"| Cache[Response Cache]
    Helper -.->|"tracks"| Health[Provider Health]
    Helper -.->|"collects"| Metrics[Metrics]
```

## Error Detection Flow

```mermaid
flowchart TD
    Start[Error Occurs] --> CheckType{Is QuotaExceededError?}
    CheckType -->|Yes| Quota[Quota Exceeded]
    CheckType -->|No| CheckCode{Has CM-1801 Code?}
    CheckCode -->|Yes| Quota
    CheckCode -->|No| Classifier[Use ProviderErrorClassifier]
    Classifier --> Category{Category?}
    Category -->|quota_exceeded| Quota
    Category -->|rate_limit| RateLimit[Rate Limit - Retry]
    Category -->|authentication| Auth[Auth Error - Don't Retry]
    Category -->|timeout| Timeout[Timeout - Try Fallback]
    Category -->|unknown| Unknown[Unknown - Log & Re-raise]
    Quota --> Fallback[Trigger Parallel Fallback]
```

## Parallel Fallback Comparison

### Sequential (Old Way)
```
Time: 0s ────────────────────────────────────────────────> 9s
      │
      ├─ Try Claude (3s) ──X──> Fail
      │
      ├─ Try OpenAI (3s) ──X──> Fail
      │
      └─ Try Ollama (3s) ──✓──> Success

Total: 9 seconds
```

### Parallel (New Way)
```
Time: 0s ────────────────────────────────> 3s
      │
      ├─ Try Claude ──X──> Fail
      │
      ├─ Try OpenAI ──┐
      │                ├─> First Success Wins
      └─ Try Ollama ───┘

Total: 3 seconds (3x faster!)
```

## Benefits Visualization

### Cost Savings
```
Without Caching:
Request 1: $0.01 ──┐
Request 2: $0.01 ──┼─> Total: $0.05
Request 3: $0.01 ──┤
Request 4: $0.01 ──┤
Request 5: $0.01 ──┘

With Caching (50% hit rate):
Request 1: $0.01 ──┐
Request 2: $0.00 ──┼─> Total: $0.03
Request 3: $0.01 ──┤   Savings: 40%
Request 4: $0.00 ──┤
Request 5: $0.01 ──┘
```

### Reliability Improvement
```
Without Circuit Breaker:
Provider Fails → Try Again → Fail → Try Again → Fail → Try Again → Fail
(4 attempts, 12 seconds wasted)

With Circuit Breaker:
Provider Fails → Mark Unhealthy → Skip Immediately → Try Next Provider
(1 attempt, 3 seconds, instant skip)
```

## Testing Flow

```mermaid
flowchart TD
    Start[Start Testing] --> Setup[Verify Setup]
    Setup --> QuickTest[Run Quick Test]
    QuickTest --> Check{All Tests Pass?}
    Check -->|No| Debug[Debug Issues]
    Debug --> QuickTest
    Check -->|Yes| UseInWork[Use in Daily Work]
    UseInWork --> Monitor[Monitor Metrics]
    Monitor --> Optimize[Optimize Config]
    Optimize --> UseInWork
```

## Real-World Example

### Scenario: Daily Coding Session

**Morning** (9:00 AM):
```
You: "Write a function to parse JSON"
ChainMind: Uses Claude → Cached
Time: 1.2s
```

**Afternoon** (2:00 PM):
```
You: "Write a function to parse JSON" (same question)
ChainMind: Cache Hit!
Time: 0.01s (instant!)
```

**Evening** (8:00 PM):
```
You: "Write a function to parse JSON" (again)
ChainMind: Cache Hit!
Time: 0.01s
```

**Next Day** (9:00 AM):
```
You: "Write a function to parse JSON"
ChainMind: Claude hits usage limit
         → Automatically uses OpenAI
         → Returns response
         → You don't notice the switch!
Time: 2.5s (slightly slower, but works!)
```

**Benefits**:
- Day 1: 3 requests, 1 API call (2 cache hits)
- Day 2: Automatic fallback, no interruption
- Total savings: 66% fewer API calls, seamless experience
