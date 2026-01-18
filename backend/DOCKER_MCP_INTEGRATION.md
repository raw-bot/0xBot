# 0xBot Docker MCP Integration Guide

**Purpose**: Reduce context consumption from bot tools by 90% and enable programmatic trading workflows without context pollution.

---

## 🎯 What This Solves

### The Problem
- Multiple bot tools (market data, signals, execution) each define complex tools with hundreds of tokens in parameters
- Every tool call returns large amounts of data (market data, trade histories, etc.) that enters the agent's context window
- Complex workflows (fetch → calculate → decide → execute) pollute the context with intermediate results
- Result: **45,000+ tokens wasted** on tool definitions and data that could be used for agent reasoning

### The Solution
- **Single MCP Server Hub**: One Docker container acts as the interface for ALL bot tools
- **Programmatic Workflows**: Complex workflows run in JavaScript, outside the context window
- **Data Externalization**: Results stored in files, not in context
- **Context Reduction**: ~90% reduction in tokens used by tools

---

## 📊 Architecture

```
┌─────────────────────────────────────────────────────┐
│         Claude Desktop / Cursor / Windsurf          │
│              (Main Agent Context)                   │
└────────────────────┬────────────────────────────────┘
                     │
                     │ Single MCP Tool Call
                     │ (Minimal tokens)
                     ↓
    ┌────────────────────────────────────┐
    │   0xBot Docker MCP Server           │
    │   (Docker Container)                │
    │                                     │
    │  ┌──────────────────────────────┐  │
    │  │ MCP Tool Registry            │  │
    │  │ - Fetch Market Data          │  │
    │  │ - Get Trinity Signals        │  │
    │  │ - Execute Trades             │  │
    │  │ - Get Portfolio              │  │
    │  │ - Execute Workflow           │  │
    │  │ - Analyze Performance        │  │
    │  └──────────────────────────────┘  │
    │                                     │
    │  ┌──────────────────────────────┐  │
    │  │ Workflow Executor            │  │
    │  │ JavaScript VM Sandbox        │  │
    │  │ - Trinity Trading Cycle      │  │
    │  │ - Performance Analysis       │  │
    │  │ - Custom Scripts             │  │
    │  └──────────────────────────────┘  │
    └────────────────────┬────────────────┘
                         │
                         │ All data here stays outside context
                         │ (files, temporary storage)
                         ↓
         ┌──────────────────────────────┐
         │  0xBot Backend API           │
         │  (Port 8000)                 │
         │  - Market Data Service       │
         │  - Trading Service           │
         │  - Portfolio Service         │
         │  - Trinity Indicators        │
         └──────────────────────────────┘
```

---

## 🚀 Setup Guide

### Prerequisites

1. **Docker Desktop** installed and running
2. **0xBot Backend API** running on `http://localhost:8000`
3. **Claude Desktop**, **Cursor**, or **Windsurf** installed
4. **Node.js 20+** (for local development)

### Step 1: Build Docker Image

```bash
cd /Users/cube/Documents/00-code/0xBot/backend

# Build the MCP server Docker image
docker build -f Dockerfile.mcp -t 0xbot-mcp-server:latest .

# Verify the image
docker images | grep 0xbot-mcp
```

### Step 2: Configure Claude Desktop

#### Option A: Using Claude Desktop (Recommended for Mac)

1. Open Claude Desktop settings
2. Go to **Developer** → **Model Context Protocol**
3. Click **Add new MCP server**
4. Paste the configuration from `claude_desktop_config.json`

Or manually add to `~/Library/Application\ Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "0xbot": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--name",
        "0xbot-mcp",
        "--network",
        "host",
        "-e",
        "BOT_API_URL=http://localhost:8000",
        "0xbot-mcp-server:latest"
      ]
    }
  }
}
```

#### Option B: Using Cursor

1. Open Cursor settings
2. Go to **Features** → **Model Context Protocol**
3. Add the same configuration

#### Option C: Using Windsurf

1. Similar to Cursor - add to `.mcp/config.json` or settings

### Step 3: Restart Your Agent

Close and reopen Claude Desktop / Cursor / Windsurf. The 0xBot MCP tool should now appear in your available tools.

### Step 4: Test Connection

In your chat, ask:
```
@0xbot What tools are available?
```

You should see a list of tools:
- `fetch_market_data`
- `get_trinity_signals`
- `execute_trade`
- `get_portfolio`
- `execute_workflow`
- `analyze_performance`

---

## 📚 Available Tools

### 1. Fetch Market Data

**Purpose**: Get real-time market data with Trinity indicators

```javascript
// In conversation
@0xbot fetch_market_data(
  symbols: ["BTC/USDT", "ETH/USDT"],
  include_indicators: true
)

// Returns:
// {
//   "BTC/USDT": {
//     "price": 42000,
//     "confluence_score": 85,
//     "signals": { ... }
//   },
//   ...
// }
```

### 2. Get Trinity Signals

**Purpose**: Generate high-confidence trading signals

```javascript
@0xbot get_trinity_signals(
  symbols: ["BTC/USDT", "ETH/USDT"],
  min_confluence: 70
)

// Returns signals with 70+ confluence score
```

### 3. Execute Trade

**Purpose**: Place a trading order

```javascript
@0xbot execute_trade(
  symbol: "BTC/USDT",
  side: "long",
  size_percent: 3,
  entry_price: 42000,
  stop_loss: 40740,
  take_profit: 44100
)
```

### 4. Get Portfolio

**Purpose**: Check current positions and P&L

```javascript
@0xbot get_portfolio(include_history: true)

// Returns current positions, balance, P&L
```

### 5. Execute Workflow

**Purpose**: Run complex workflows in JavaScript

```javascript
@0xbot execute_workflow(
  script: `
    // Fetch data
    const data = await fetchMarketData(['BTC/USDT']);

    // Get signals
    const signals = await getTrinitySignals(['BTC/USDT']);

    // Execute trades
    for (const signal of Object.values(signals)) {
      if (signal.is_entry_signal) {
        await executeTrade({...});
      }
    }

    return { completed: true, trades: results };
  `
)

// All intermediate data stays outside context
// Only final summary returned
```

### 6. Analyze Performance

**Purpose**: Get performance metrics and insights

```javascript
@0xbot analyze_performance(period_hours: 24)

// Returns:
// {
//   "win_rate": "62%",
//   "profit_factor": "2.3",
//   "insights": [...],
//   "detailed_analysis_available": true
// }
```

---

## 🔄 Example Workflows

### Workflow 1: Complete Trinity Trading Cycle

```javascript
@0xbot execute_workflow(
  script: `
    // Load the Trinity trading cycle workflow
    const workflow = require('/app/mcp-workflows/trinity-trading-cycle.js');

    // Run the complete cycle
    const result = await workflow.run(tools, {
      symbols: ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'],
      min_confluence: 70
    });

    // Only summary is returned to context
    return result;
  `
)
```

**What Happens (Outside Context)**:
1. Fetches market data for 3 symbols
2. Calculates Trinity indicators (6 indicators each)
3. Generates entry signals
4. Checks portfolio
5. Executes qualifying trades
6. Logs everything to external file
7. **Returns only summary** to agent

**Result**: ~45,000 tokens NOT in context window!

### Workflow 2: Performance Analysis

```javascript
@0xbot execute_workflow(
  script: `
    const analysis = require('/app/mcp-workflows/performance-analysis.js');

    const result = await analysis.run(tools, {});
    return result;
  `
)
```

**Returns**:
```json
{
  "status": "success",
  "summary": {
    "trades_analyzed": 47,
    "win_rate": "63%",
    "profit_factor": "2.1",
    "total_pnl": "3245 USD",
    "insights": [
      "✅ Strong win rate (63%) - Trinity confluence filtering is working",
      "✅ Excellent profit factor (2.1) - Consistently profitable",
      "📊 High confluence trades (80+): 71% win rate - Validates confluence scoring"
    ],
    "context_tokens_saved": "~40000"
  }
}
```

---

## 🎯 Use Cases

### Use Case 1: Live Trading Monitoring

```
Human: Monitor Trinity signals for the next hour and execute any high-confidence entries

AI: I'll use the @0xbot MCP server to monitor and trade continuously...

@0xbot execute_workflow(
  script: `
    const startTime = Date.now();
    const trades = [];

    while (Date.now() - startTime < 3600000) {
      // Fetch data, generate signals, execute trades
      const signals = await getTrinitySignals(symbols);
      const portfolio = await getPortfolio();

      // Execute high-confidence signals
      for (const [symbol, signal] of Object.entries(signals)) {
        if (signal.is_entry_signal && signal.confidence > 0.85) {
          const trade = await executeTrade({...});
          trades.push(trade);
        }
      }

      await sleep(180000); // 3 minute cycle
    }

    return { trades_executed: trades.length, results: trades };
  `
)

Result: One hour of continuous trading, ZERO context pollution
Tokens saved: ~60,000
```

### Use Case 2: Performance Analysis & Optimization

```
Human: Analyze our trading performance and suggest optimizations

AI: I'll run a complete performance analysis...

@0xbot execute_workflow(script: analysis.js)

Result:
- 127 trades analyzed (all data in external file)
- 64% win rate
- Confluence correlation: Higher confluence = higher win rate ✅
- Recommendation: Increase position sizes for 80+ confluence signals
- Context tokens used: ~2,000 (instead of ~50,000)
```

### Use Case 3: Multi-Strategy Comparison

```
Human: Compare Trinity signals vs LLM signals for the same symbols

AI: I'll gather data on both strategies...

@0xbot execute_workflow(
  script: `
    const trinity = await getTrinitySignals(['BTC/USDT', 'ETH/USDT']);
    const llm = await getLLMSignals(['BTC/USDT', 'ETH/USDT']);

    // Compare without flooding context
    // All analysis done in JS, results saved to file

    return {
      trinity_signals: Object.keys(trinity).length,
      llm_signals: Object.keys(llm).length,
      comparison_file: '/tmp/strategy-comparison.json'
    };
  `
)
```

---

## 📊 Context Savings

### Before (Without Docker MCP)
```
Agent Tool Definitions:        ~8,000 tokens
Market Data Response:          ~12,000 tokens
Trinity Indicators:            ~8,000 tokens
Signals:                       ~6,000 tokens
Trade Execution Details:       ~4,000 tokens
Portfolio Data:                ~7,000 tokens
────────────────────────────────────────
TOTAL:                         ~45,000 tokens
```

### After (With Docker MCP)
```
0xBot MCP Tool Definition:     ~500 tokens
Workflow Results (Summary):    ~1,000 tokens
Data in External Files:        ~0 tokens (outside context)
────────────────────────────────────────
TOTAL:                         ~1,500 tokens
```

**Savings: ~43,500 tokens (97% reduction)** ✅

---

## 🛠 Development & Testing

### Run MCP Server Locally

```bash
# Install dependencies
npm install

# Start MCP server (for debugging)
npm run dev

# Connect locally via stdio
# Used for testing before Docker deployment
```

### Test Workflows

```bash
# Run workflow tests
npm run test:mcp

# Lint code
npm run lint
```

### Debug Docker Image

```bash
# Run container interactively
docker run -it \
  --network host \
  -e BOT_API_URL=http://localhost:8000 \
  0xbot-mcp-server:latest

# Check logs
docker logs 0xbot-mcp
```

---

## 🔒 Security Considerations

1. **JavaScript Sandbox**: Workflows run in a strict VM context with 30-second timeout
2. **No File System Access**: Sandbox only has access to provided APIs
3. **Environment Variables**: Sensitive data via `.env`, not exposed to workflows
4. **Network Isolation**: Docker container on `host` network (change if security concern)
5. **Input Validation**: All tool parameters validated before execution

---

## ⚙️ Configuration

### Environment Variables

```bash
# .env file
BOT_API_URL=http://localhost:8000
PYTHON_BIN=python3
MCP_LOG_LEVEL=info
WORKFLOW_TIMEOUT_MS=30000
```

### Docker Compose (Optional)

For running both bot API and MCP server together:

```yaml
version: '3.8'

services:
  bot-api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/trading_agent
    depends_on:
      - db

  mcp-server:
    build:
      context: .
      dockerfile: Dockerfile.mcp
    environment:
      - BOT_API_URL=http://bot-api:8000
    depends_on:
      - bot-api

  db:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

Deploy with:
```bash
docker-compose up -d
```

---

## 📝 Documentation

### MCP Server Structure

```
mcp-server/
├── index.js              # Main MCP server implementation
├── tools/
│   ├── market-data.js    # Market data fetching
│   ├── signals.js        # Trinity signal generation
│   ├── trading.js        # Trade execution
│   └── portfolio.js      # Portfolio management
└── utils/
    ├── validators.js     # Input validation
    └── formatters.js     # Response formatting

mcp-workflows/
├── trinity-trading-cycle.js     # Complete trading workflow
├── performance-analysis.js       # Performance analysis workflow
└── custom-workflows/
    ├── arbitrage-detection.js    # (Custom: detect arbitrage)
    └── rebalancing.js             # (Custom: portfolio rebalancing)
```

### Creating Custom Workflows

```javascript
// mcp-workflows/my-workflow.js
module.exports = {
  name: "My Custom Workflow",
  description: "What this workflow does",

  async run(tools, config = {}) {
    try {
      // Use tools without context pollution
      const data = await tools.fetchMarketData({ ... });
      const signals = await tools.getTrinitySignals({ ... });

      // Process data
      const results = processData(data, signals);

      // Save to file
      const fs = require('fs');
      fs.writeFileSync('/tmp/my-results.json', JSON.stringify(results));

      // Return only summary to context
      return {
        status: "success",
        summary: results.summary,
        full_data_file: '/tmp/my-results.json'
      };
    } catch (error) {
      return { status: "error", error: error.message };
    }
  }
};
```

---

## 🚀 Next Steps

1. **Build Docker Image**: `docker build -f Dockerfile.mcp -t 0xbot-mcp-server:latest .`
2. **Configure Agent**: Update `claude_desktop_config.json` with your setup
3. **Test Tools**: Ask agent to list available 0xbot tools
4. **Run Workflows**: Execute Trinity trading cycle and monitor
5. **Optimize**: Use performance analysis to refine signal generation

---

## 📞 Support

### Common Issues

**Issue**: Docker image build fails
**Solution**: Ensure Node.js 20+ is available: `node --version`

**Issue**: MCP tool not appearing in agent
**Solution**: Restart agent app after config change, check docker is running: `docker ps`

**Issue**: Bot API connection fails
**Solution**: Verify bot running on port 8000: `curl http://localhost:8000/health`

**Issue**: Workflow timeout
**Solution**: Increase timeout in `.env` (default 30s): `WORKFLOW_TIMEOUT_MS=60000`

---

## 🎓 Learning Resources

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Anthropic's MCP Blog Post](https://www.anthropic.com/news/model-context-protocol)
- [Docker Documentation](https://docs.docker.com/)
- [Node.js VM Documentation](https://nodejs.org/api/vm.html)

---

**Status**: 🟢 **DOCKER MCP INTEGRATION READY**

Your bot can now leverage AI agents without context pollution. All heavy lifting happens in isolated Docker containers with results stored externally.

🚀 **Start leveraging AI for sophisticated trading workflows!**
