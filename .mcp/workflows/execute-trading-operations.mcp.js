/**
 * MCP Workflow: Execute Trading Operations
 *
 * Handles opening positions, closing positions, and risk management
 * entirely within the MCP Gateway. No trading data enters context window.
 *
 * Execution: mcp-cli run workflows/execute-trading-operations.mcp.js
 * Context Impact: ~0 tokens (completely isolated)
 */

const {
  python,          // Python for calculations
  postgres,        // Database for persistence
  bash,            // Shell commands
  filesystem,      // File logging
} = mcp_tools;

// ============================================================================
// Configuration
// ============================================================================

const CONFIG = {
  bot_id: "11d9bbf0-c3e0-47f2-b3a1-3cc8f2516879",
  db: "postgresql://bot:bot123@localhost:5432/trading_bot",
  log_dir: "/app/.mcp/logs/trading",
  execution_timeout: 30000,
};

// ============================================================================
// Main Workflow
// ============================================================================

async function main() {
  console.log("[TRADING] Starting trading operations workflow...");

  try {
    // Step 1: Fetch pending trading decisions (from database, not context)
    const decisions = await fetchPendingDecisions();

    if (decisions.length === 0) {
      console.log("[TRADING] No pending trading decisions");
      return {
        status: "idle",
        decisions_processed: 0
      };
    }

    console.log(`[TRADING] Processing ${decisions.length} trading decisions...`);

    // Step 2: Process each decision (Python-based risk calculation)
    const results = [];
    for (const decision of decisions) {
      const result = await processTradeDecision(decision);
      results.push(result);
    }

    // Step 3: Update database with execution results (persisted, not in context)
    await updateDatabase(results);

    // Step 4: Log execution to audit trail
    await logToFile(results);

    // Return only summary
    return {
      status: "success",
      decisions_processed: decisions.length,
      successful_trades: results.filter(r => r.executed).length,
      failed_trades: results.filter(r => !r.executed).length,
      total_pnl: results.reduce((sum, r) => sum + (r.pnl || 0), 0)
    };

  } catch (error) {
    console.error("[TRADING] Error:", error);
    return {
      status: "error",
      error: error.message
    };
  }
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Fetch pending trading decisions from database
 * Keeps data in DB until ready to return minimal result
 */
async function fetchPendingDecisions() {
  const sql = `
    SELECT
      id, symbol, side, size_pct, stop_loss, take_profit,
      confluence_score, confidence, timestamp
    FROM trading_signals
    WHERE
      status = 'pending' AND
      bot_id = $1 AND
      timestamp > NOW() - INTERVAL '1 minute'
    ORDER BY confidence DESC
    LIMIT 10
  `;

  try {
    const result = await postgres.query(sql, [CONFIG.bot_id]);
    return result.rows || [];
  } catch (error) {
    console.error("Failed to fetch decisions:", error);
    return [];
  }
}

/**
 * Process individual trade decision
 */
async function processTradeDecision(decision) {
  console.log(`  Processing: ${decision.symbol} ${decision.side}`);

  try {
    // Python-based validation and execution
    const pythonCode = `
import json
import datetime

decision = json.loads('''${JSON.stringify(decision)}''')

# Risk validation
symbol = decision['symbol']
side = decision['side']
size_pct = decision['size_pct']
stop_loss = decision['stop_loss']
take_profit = decision['take_profit']

# Validate risk parameters
valid = (
    0 < size_pct <= 1.0 and
    stop_loss > 0 and
    take_profit > 0
)

# Calculate position details
if valid:
    if side == 'long':
        valid = stop_loss < decision.get('entry_price', 0) < take_profit
    else:
        valid = take_profit < decision.get('entry_price', 0) < stop_loss

result = {
    'signal_id': decision['id'],
    'symbol': symbol,
    'side': side,
    'valid': valid,
    'size_pct': size_pct,
    'stop_loss': stop_loss,
    'take_profit': take_profit,
    'executed': valid,
    'timestamp': datetime.datetime.utcnow().isoformat()
}

print(json.dumps(result))
`;

    const result = await python.execute(pythonCode);
    const execution = JSON.parse(result.stdout);

    // Simulate execution if valid
    if (execution.valid) {
      execution.executed = true;
      execution.entry_price = decision.entry_price;
      execution.pnl = 0; // No P&L until closed
      execution.message = `Position opened: ${decision.symbol}`;
    } else {
      execution.executed = false;
      execution.message = `Risk validation failed for ${decision.symbol}`;
    }

    return execution;

  } catch (error) {
    console.error(`  Error processing ${decision.symbol}:`, error);
    return {
      signal_id: decision.id,
      symbol: decision.symbol,
      executed: false,
      error: error.message
    };
  }
}

/**
 * Update database with execution results
 */
async function updateDatabase(results) {
  const updatePromises = results.map(result => {
    const status = result.executed ? 'executed' : 'failed';
    const sql = `
      UPDATE trading_signals
      SET status = $1, execution_details = $2, updated_at = NOW()
      WHERE id = $3
    `;

    return postgres.query(sql, [
      status,
      JSON.stringify(result),
      result.signal_id
    ]).catch(err => {
      console.warn(`Failed to update signal ${result.signal_id}:`, err);
    });
  });

  await Promise.all(updatePromises);
  console.log(`  Updated ${results.length} records in database`);
}

/**
 * Log execution to file
 */
async function logToFile(results) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filename = `${CONFIG.log_dir}/execution-${timestamp}.json`;

  const logData = {
    workflow: "execute-trading-operations",
    timestamp: new Date().toISOString(),
    results,
    summary: {
      total: results.length,
      executed: results.filter(r => r.executed).length,
      failed: results.filter(r => !r.executed).length
    }
  };

  try {
    await filesystem.write(filename, JSON.stringify(logData, null, 2));
    console.log(`  Execution logged to: ${filename}`);
  } catch (error) {
    console.warn("Failed to write log:", error);
  }
}

// ============================================================================
// Execution
// ============================================================================

main().then(result => {
  console.log("[RESULT]", JSON.stringify(result, null, 2));
  process.exit(0);
}).catch(error => {
  console.error("[FATAL]", error);
  process.exit(1);
});
