# Claude Code + Docker MCP Integration Guide

## Quick Start

### For macOS (using Claude Code CLI)

```bash
# 1. Ensure Docker is running
docker ps  # Should show running containers

# 2. Start Docker MCP Gateway from project root
cd /Users/cube/Documents/00-code/0xBot
docker mcp up

# 3. Configure Claude Code to use Docker MCP
# Add to ~/.claude/config.json or through Claude Code settings

# 4. Verify connection
docker mcp status

# 5. Start using Claude Code with Docker MCP
claude-code .
```

## Configuration

### Option 1: Global Claude Code Configuration

Edit `~/.claude/config.json`:

```json
{
  "mcp": {
    "servers": {
      "docker-mcp": {
        "enabled": true,
        "type": "stdio",
        "command": "docker",
        "args": ["mcp", "client"],
        "env": {
          "MCP_GATEWAY_URL": "http://localhost:3001",
          "MCP_DISCOVERY_ENABLED": "true"
        }
      }
    },
    "gateway": {
      "url": "http://localhost:3001",
      "timeout": 30000,
      "contextBudget": 2000,
      "toolFiltering": {
        "maxToolsPerRequest": 10,
        "relevanceThreshold": 0.7,
        "groupByCategory": true
      }
    }
  }
}
```

### Option 2: Project-Specific Configuration

Create `.mcp/claude-code-config.json`:

```json
{
  "version": "1.0",
  "gateway": {
    "host": "localhost",
    "port": 3001,
    "protocol": "http"
  },
  "projects": [
    {
      "path": "/Users/cube/Documents/00-code/0xBot",
      "name": "0xBot Trading System",
      "tools": {
        "enabled": [
          "filesystem",
          "python",
          "postgres",
          "fetch",
          "git"
        ],
        "disabled": [
          "bash"  // Disable for safety in production
        ]
      }
    }
  ],
  "workflows": {
    "autoRun": {
      "fetch-market-data": "0 */4 * * *",  // Every 4 hours
      "check-positions": "0 * * * *"        // Every hour
    }
  },
  "logging": {
    "level": "info",
    "file": ".mcp/logs/claude-code.log"
  }
}
```

## Using Docker MCP with Claude Code

### Example 1: Analyzing Trading Performance

**Claude Code Prompt:**
```
Analyze the trading performance of the bot over the last 7 days.
Look at:
1. Total trades executed
2. Win/loss ratio
3. Average profit per trade
4. Most profitable symbol
```

**What Happens Internally:**

1. Claude Code connects to Docker MCP gateway
2. Gateway receives request and routes to relevant tools:
   - `postgres.query` → Fetch trades from database
   - `python.execute` → Calculate statistics
   - `filesystem.write` → Save analysis report

3. Each tool executes in its isolated container:
   ```
   [PostgreSQL Container]
   SELECT * FROM trades WHERE created_at > NOW() - INTERVAL '7 days'

   [Python Container]
   import pandas as pd
   # Calculate metrics
   win_ratio = wins / total_trades
   # etc

   [Filesystem Container]
   Write report to /app/.mcp/data/analysis.json
   ```

4. Claude Code receives only the summary:
   ```json
   {
     "total_trades": 45,
     "win_ratio": 0.62,
     "avg_profit_per_trade": 150.25,
     "most_profitable_symbol": "BTC/USDT",
     "analysis_file": "/app/.mcp/data/analysis-2025-01-16.json"
   }
   ```

**Context Used:** ~200 tokens (vs 5,000+ without Docker MCP)

### Example 2: Debugging Market Data Issues

**Claude Code Prompt:**
```
The market data fetch workflow is failing for some symbols.
Can you:
1. Check what error we're getting
2. Test the OKX API connection
3. Verify the Trinity indicators are calculating correctly
```

**Workflow:**

```javascript
// Claude Code triggers this workflow
docker mcp run workflows/debug-market-data.mcp.js

// Inside container (no context leakage):
1. Read latest logs from /app/.mcp/logs/
2. Parse error messages
3. Test OKX API with fetch tool
4. Test Trinity calculation with Python
5. Write results to debug-report.json

// Claude Code receives:
{
  "status": "diagnosed",
  "issues": [
    "OKX API rate limit: 5 requests/second",
    "Trinity indicators: Memory issue with 250 candles"
  ],
  "recommendations": [
    "Add request throttling",
    "Reduce candle window to 200"
  ],
  "debug_file": "/app/.mcp/data/debug-2025-01-16.json"
}
```

### Example 3: Checking Bot Status

**Claude Code Prompt:**
```
What's the current status of the trading bot?
```

**Flow:**

```
Claude Code → Docker MCP Gateway
   ↓
Gateway routes to tools:
   [PostgreSQL] Get current positions
   [PostgreSQL] Get latest signals
   [Filesystem] Read recent logs
   [Python] Calculate P&L
   ↓
Summary returned to Claude Code:
{
  "bot_status": "active",
  "positions": 2,
  "pnl": "+$245.32",
  "last_signal": "BTC/USDT BUY (confidence: 78%)",
  "uptime": "2 hours 15 minutes"
}
```

## Tool Reference for Claude Code

### Database Access (PostgreSQL)

```
When Claude Code needs database information:

User: "Show me all open positions"
↓
Claude Code: @db query "SELECT * FROM positions WHERE status='OPEN'"
↓
Docker MCP: Executes in PostgreSQL container, returns summary
↓
Claude Code: Shows results without context bloat
```

### File Operations (Filesystem)

```
When Claude Code needs file information:

User: "Check the latest bot logs"
↓
Claude Code: @fs read "latest: /app/.mcp/logs/bot*.log"
↓
Docker MCP: Reads file in container, returns summary
↓
Claude Code: Shows key log entries
```

### Code Execution (Python)

```
When Claude Code needs calculations:

User: "Calculate the sharpe ratio of recent trades"
↓
Claude Code: @py exec "calculate_sharpe_ratio.py"
↓
Docker MCP: Runs Python in isolated container
↓
Claude Code: Gets numerical result
```

### API Calls (Fetch)

```
When Claude Code needs external data:

User: "Check current BTC price"
↓
Claude Code: @fetch get "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin"
↓
Docker MCP: Makes request in container
↓
Claude Code: Gets JSON response summary
```

## Workflow Commands

Use these commands when working with Claude Code:

```bash
# List available workflows
docker mcp workflows list

# Run a workflow manually
docker mcp run workflows/fetch-market-data.mcp.js

# View workflow results
docker mcp results --latest

# Schedule a workflow
docker mcp schedule workflows/daily-report.mcp.js "0 18 * * *"

# Cancel a running workflow
docker mcp cancel <workflow-id>

# View workflow logs
docker mcp logs --workflow <name>
```

## Best Practices for Claude Code + Docker MCP

### ✅ Do's

1. **Use workflows for complex operations**
   ```
   "Can you fetch market data, calculate indicators, and save to DB?"
   → Use: docker mcp run workflows/fetch-market-data.mcp.js
   ```

2. **Reference saved files instead of large datasets**
   ```
   ✓ "Check /app/.mcp/data/analysis.json for details"
   ✗ "Here's 10,000 lines of trading data: [all data]"
   ```

3. **Let workflows handle data processing**
   ```
   ✓ "Run the Trinity signal calculation workflow"
   ✗ "Here's 500 candles, calculate RSI, ADX, etc. for each"
   ```

4. **Ask for summaries, not raw data**
   ```
   ✓ "What's the average daily P&L?"
   ✗ "List all trades with full details"
   ```

### ❌ Don'ts

1. **Don't ask for enormous datasets directly**
   ```
   ✗ "Fetch all 10,000 trades and analyze them"
   → Instead: "Run analysis workflow, tell me the summary"
   ```

2. **Don't use bash for sensitive operations**
   ```
   ✗ @bash exec "rm -rf /app"
   ✓ Use Python/Filesystem tools for safe operations
   ```

3. **Don't bypass Docker MCP with direct file access**
   ```
   ✗ cat /app/secrets.env | grep API_KEY
   ✓ Use @db or @py to access configuration
   ```

4. **Don't execute long-running tasks interactively**
   ```
   ✗ @py exec "process_5_years_of_data()"
   ✓ Use: docker mcp run workflows/historical-analysis.mcp.js
   ```

## Performance Metrics

Monitor how Docker MCP improves efficiency:

```bash
# View context savings
docker mcp metrics --metric context_usage

# Output:
Context Budget: 2,000 tokens
Daily Operations: 24
Context Per Operation: 83 tokens
Total Used: 1,984 tokens (99.2% efficient)

Savings vs Direct MCP: 18,016 tokens
Improvement: 90%+ context reduction
```

## Troubleshooting

### Issue: "Tool not available"

```bash
# Check if tool's container is running
docker mcp status

# Restart the tool
docker mcp restart postgres

# Verify tool is in enabled list
docker mcp tools available
```

### Issue: "Workflow timeout"

```bash
# Increase timeout in config
docker mcp config set --timeout 60000  # 60 seconds

# Or run with explicit timeout
docker mcp run workflows/fetch-market-data.mcp.js --timeout 120000
```

### Issue: "Context still too high"

```bash
# Profile context usage
docker mcp profile --duration 3600

# Identify high-context operations
docker mcp logs --filter "context_usage > 500"

# Optimize by batching or file storage
```

## Next Steps

1. Start Docker MCP: `docker mcp up`
2. Configure Claude Code with `.mcp/claude-code-config.json`
3. Test with a simple query: "What's the bot status?"
4. Run a workflow: `docker mcp run workflows/fetch-market-data.mcp.js`
5. Monitor context savings: `docker mcp metrics`
6. Integrate into your regular workflow

With Docker MCP enabled, Claude Code will automatically:
- Route large operations to isolated containers
- Keep context consumption minimal
- Execute workflows without context leakage
- Return only summaries to the context window

This makes working with the 0xBot project dramatically more efficient!
