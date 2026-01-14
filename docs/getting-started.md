# Getting Started with Engram

> Give Claude a memory in under 5 minutes

---

## Prerequisites

- **Python 3.10+**
- **Claude Code** (or any MCP-compatible client)
- ~200MB disk space (for embedding model + data)

---

## Installation

### Option 1: pip (Recommended)

```bash
pip install engram-mcp
```

### Option 2: From Source

```bash
git clone https://github.com/creator-ai-studio/engram-mcp.git
cd engram-mcp
pip install -e .
```

### Option 3: With GPU Support

```bash
# If you have an NVIDIA GPU and want faster embeddings
pip install engram-mcp[gpu]
```

---

## Configure Claude Code

### 1. Find your settings file

| OS | Path |
|----|------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Linux | `~/.config/claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

For Claude Code CLI, use `~/.claude/settings.json`.

### 2. Add Engram as an MCP server

```json
{
  "mcpServers": {
    "engram": {
      "command": "python",
      "args": ["-m", "engram.server"]
    }
  }
}
```

### 3. Restart Claude

Close and reopen Claude Code (or Claude Desktop) to load the new MCP server.

---

## Verify Installation

In Claude, try:

```
Use engram_remember to store: "This is a test memory"
```

You should see a confirmation that the memory was stored.

Then try:

```
Use engram_recall to search for: "test"
```

You should see your test memory returned.

---

## Your First Memories

### Store a Preference

```
Use engram_remember to store my preference:
"I prefer TypeScript over JavaScript for new projects"
Set importance to 0.8
```

### Store a Fact

```
Use engram_remember to store this fact:
"The project uses PostgreSQL 15 with the pgvector extension"
```

### Store a Solution

```
Use engram_remember to store this solution:
"Fixed CUDA out of memory by setting PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512"
Set memory_type to "solution"
```

---

## Searching Memories

### Basic Search

```
Use engram_recall to find memories about "database setup"
```

### Project-Filtered Search

```
Use engram_recall to find memories about "configuration" in project "hallo2"
```

### Get Context for Current Task

```
Use engram_context to get relevant memories for "setting up GPU acceleration"
```

---

## Common Workflows

### Starting a New Session

At the start of each session, get relevant context:

```
Use engram_context to recall relevant memories for this project
```

### Recording a Decision

When you make an important decision:

```
Use engram_remember to store this decision:
"Decided to use SQLite instead of PostgreSQL for the MVP"
Set memory_type to "decision"
Set importance to 0.9
```

### After Solving a Problem

When you fix something tricky:

```
Use engram_remember to store this solution:
"PyTorch not detecting GPU - fixed by installing nightly with cu128"
Set memory_type to "solution"
```

---

## Project Detection

Engram automatically detects your project from the current directory:

| Working Directory | Detected Project |
|-------------------|------------------|
| `/mnt/dev/ai/hallo2/src` | `hallo2` |
| `/home/user/projects/myapp/lib` | `myapp` |
| `~/work/client-project/api` | `client-project` |

Memories are automatically tagged with the detected project, and project memories are prioritized in search results.

---

## Data Location

All Engram data is stored locally:

```
~/.engram/
├── config.yaml           # Your configuration
├── data/
│   ├── episodic.db       # SQLite database
│   ├── chromadb/         # Vector embeddings
│   └── graph.json        # Knowledge graph (future)
└── logs/
    └── engram.log        # Debug logs
```

### Backup Your Memories

```bash
# Simple backup
cp -r ~/.engram ~/.engram-backup-$(date +%Y%m%d)

# Or just the database
cp ~/.engram/data/episodic.db ~/my-memories-backup.db
```

---

## Configuration

Create `~/.engram/config.yaml` to customize:

```yaml
# Data storage location
data_dir: ~/.engram/data

# Logging
log_level: INFO  # DEBUG for troubleshooting

# Embedding model
embedding:
  model: all-MiniLM-L6-v2
  device: auto  # auto, cuda, cpu

# Search defaults
retrieval:
  default_limit: 10
  recency_weight: 0.3  # How much to favor recent memories

# Project detection patterns
projects:
  patterns:
    - "/mnt/dev/ai/(?P<project>[^/]+)"
    - "~/projects/(?P<project>[^/]+)"
    - "~/work/(?P<project>[^/]+)"
```

---

## Troubleshooting

### "MCP server not found"

1. Check your settings file path
2. Verify Python is in your PATH
3. Try running manually: `python -m engram.server`

### "Embedding model download failed"

The model (~90MB) downloads on first use. If it fails:

```bash
# Manual download
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

### "CUDA out of memory"

Engram uses GPU for embeddings if available. To force CPU:

```yaml
# ~/.engram/config.yaml
embedding:
  device: cpu
```

### "Memories not persisting"

Check write permissions:

```bash
ls -la ~/.engram/data/
```

Should show `episodic.db` and `chromadb/` directory.

### View Debug Logs

```bash
tail -f ~/.engram/logs/engram.log
```

---

## Next Steps

1. **Use it naturally** for a week
2. **Store important context** as you work
3. **Search before re-explaining** things
4. **Give feedback** on what works / doesn't

Read more:
- [MVP Limitations](MVP.md) - What's not included yet
- [Architecture](architecture.md) - Technical deep dive
- [Contributing](../CONTRIBUTING.md) - Help improve Engram

---

## Quick Reference

| Task | Command |
|------|---------|
| Store memory | `engram_remember content="..." memory_type="fact"` |
| Search | `engram_recall query="..."` |
| Get context | `engram_context query="..."` |
| Filter by project | `engram_recall query="..." project="myproject"` |

---

*Questions? Issues? [Open a GitHub issue](https://github.com/creator-ai-studio/engram-mcp/issues)*
