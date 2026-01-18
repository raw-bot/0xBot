/**
 * MCP Workflow: Fetch Market Data from OKX
 *
 * This workflow executes entirely within the MCP Gateway and demonstrates
 * how to use JavaScript to call multiple MCP tools in sequence without
 * context leakage. Results can be saved to files instead of returning to context.
 *
 * Execution: mcp-cli run workflows/fetch-market-data.mcp.js
 * Context Impact: ~0 tokens (all operations isolated in gateway)
 */

// ============================================================================
// MCP Tool Bindings (available within gateway)
// ============================================================================

const {
  fetch,           // HTTP requests (fetch MCP server)
  filesystem,      // File operations (filesystem MCP server)
  python,          // Python code execution
  postgres,        // Database operations
} = mcp_tools;

// ============================================================================
// Configuration
// ============================================================================

const CONFIG = {
  okx_api_url: "https://www.okx.com/api/v5",
  output_dir: "/app/.mcp/data",
  symbols: ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"],
  db_table: "market_snapshots",
  cache_ttl: 60, // seconds
};

// ============================================================================
// Main Workflow
// ============================================================================

async function main() {
  console.log("[WORKFLOW] Starting market data fetch workflow...");
  const timestamp = new Date().toISOString();

  try {
    // Step 1: Fetch market data from OKX API
    console.log("[STEP 1] Fetching market data from OKX...");
    const marketData = await fetchMarketData();

    // Step 2: Parse and validate data (done locally in workflow)
    console.log("[STEP 2] Validating market data...");
    const validatedData = validateMarketData(marketData);

    // Step 3: Calculate technical indicators using Python (isolated execution)
    console.log("[STEP 3] Calculating Trinity indicators...");
    const indicatorData = await calculateIndicators(validatedData);

    // Step 4: Store results in database (no context leakage)
    console.log("[STEP 4] Storing market data in database...");
    await storeInDatabase(indicatorData, timestamp);

    // Step 5: Save to file for audit trail
    console.log("[STEP 5] Saving results to file...");
    await saveToFile(indicatorData, timestamp);

    // Step 6: Return only summary (minimal context usage)
    const summary = generateSummary(indicatorData);
    console.log("[WORKFLOW] Market data fetch completed successfully");

    return {
      status: "success",
      timestamp,
      symbols_processed: CONFIG.symbols.length,
      data_points: indicatorData.length,
      output_file: `${CONFIG.output_dir}/market-data-${timestamp}.json`,
      summary
    };

  } catch (error) {
    console.error("[WORKFLOW] Error in market data fetch:", error);
    return {
      status: "error",
      error: error.message,
      timestamp
    };
  }
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Fetch market data from OKX API
 * Uses HTTP/fetch tool via MCP gateway
 */
async function fetchMarketData() {
  const data = [];

  for (const symbol of CONFIG.symbols) {
    try {
      const url = `${CONFIG.okx_api_url}/market/ticker?instId=${symbol}`;

      console.log(`  Fetching: ${symbol}`);
      const response = await fetch.get(url, {
        headers: {
          "Accept": "application/json",
        },
        timeout: 10000
      });

      if (response.status === 200) {
        const json = JSON.parse(response.body);
        if (json.data && json.data[0]) {
          data.push({
            symbol,
            last: parseFloat(json.data[0].last),
            bid: parseFloat(json.data[0].bidPx),
            ask: parseFloat(json.data[0].askPx),
            volume_24h: parseFloat(json.data[0].vol24h),
            timestamp: new Date().toISOString()
          });
        }
      }
    } catch (err) {
      console.warn(`  Failed to fetch ${symbol}: ${err.message}`);
    }
  }

  return data;
}

/**
 * Validate market data structure
 */
function validateMarketData(data) {
  return data.filter(item => {
    const isValid = item.last > 0 && item.bid > 0 && item.ask > 0;
    if (!isValid) {
      console.warn(`  Skipping invalid data for ${item.symbol}`);
    }
    return isValid;
  });
}

/**
 * Calculate Trinity indicators using isolated Python execution
 * Python script runs in MCP Python server, no context leakage
 */
async function calculateIndicators(marketData) {
  const pythonCode = `
import json
import sys

# Receive market data from stdin
market_data = json.loads('''${JSON.stringify(marketData)}''')

# Calculate simple indicators (Trinity framework simplified)
indicators = []
for item in market_data:
    symbol = item['symbol']
    price = item['last']

    # Simple calculations (in production, use full Trinity indicators)
    indicators.append({
        'symbol': symbol,
        'price': price,
        'bid': item['bid'],
        'ask': item['ask'],
        'spread_pct': ((item['ask'] - item['bid']) / price * 100),
        'volume_24h': item['volume_24h'],
        'timestamp': item['timestamp']
    })

print(json.dumps(indicators))
`;

  try {
    const result = await python.execute(pythonCode);
    return JSON.parse(result.stdout);
  } catch (error) {
    console.error("Python calculation failed:", error);
    return marketData; // Fallback to raw data
  }
}

/**
 * Store market data in PostgreSQL database
 * Data persists in database, not in context window
 */
async function storeInDatabase(data, timestamp) {
  const values = data.map(item => ({
    symbol: item.symbol,
    price: item.price,
    spread_pct: item.spread_pct,
    volume_24h: item.volume_24h,
    timestamp: timestamp,
    created_at: new Date().toISOString()
  }));

  try {
    // Use SQL insert statement
    const sql = `
      INSERT INTO ${CONFIG.db_table}
      (symbol, price, spread_pct, volume_24h, timestamp, created_at)
      VALUES ${values.map((_, i) => `($${i*5+1}, $${i*5+2}, $${i*5+3}, $${i*5+4}, $${i*5+5}, $${i*5+6})`).join(',')}
    `;

    const params = values.flatMap(v => [
      v.symbol, v.price, v.spread_pct, v.volume_24h, v.timestamp, v.created_at
    ]);

    await postgres.query(sql, params);
    console.log(`  Stored ${data.length} records in database`);
  } catch (error) {
    console.error("Database storage error:", error);
  }
}

/**
 * Save results to file for audit trail
 * Uses filesystem MCP server
 */
async function saveToFile(data, timestamp) {
  const filename = `${CONFIG.output_dir}/market-data-${timestamp.replace(/[:.]/g, '-')}.json`;

  const output = {
    workflow: "fetch-market-data",
    timestamp,
    data_count: data.length,
    symbols: CONFIG.symbols,
    data
  };

  try {
    await filesystem.write(filename, JSON.stringify(output, null, 2));
    console.log(`  Results saved to: ${filename}`);
  } catch (error) {
    console.error("File write error:", error);
  }
}

/**
 * Generate summary for minimal context return
 * Only returns aggregated metrics, not individual data points
 */
function generateSummary(data) {
  const prices = data.map(d => d.price);
  const avgPrice = prices.reduce((a, b) => a + b, 0) / prices.length;
  const maxPrice = Math.max(...prices);
  const minPrice = Math.min(...prices);

  return {
    data_points: data.length,
    avg_price: avgPrice.toFixed(2),
    price_range: `${minPrice.toFixed(2)} - ${maxPrice.toFixed(2)}`,
    symbols_processed: data.map(d => d.symbol).join(", ")
  };
}

// ============================================================================
// Execution
// ============================================================================

// Execute workflow and return results
main().then(result => {
  console.log("[RESULT]", JSON.stringify(result, null, 2));
  process.exit(result.status === "success" ? 0 : 1);
}).catch(error => {
  console.error("[FATAL]", error);
  process.exit(1);
});
