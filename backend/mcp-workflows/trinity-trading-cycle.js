/**
 * Trinity Trading Cycle Workflow
 * Complete trading cycle in a single JavaScript script
 * This workflow runs entirely outside the agent's context window
 *
 * Benefits:
 * - No context pollution (market data, indicators, signals never enter agent context)
 * - Sequential execution (fetch → calculate → decide → execute)
 * - Results stored in external file, not in context
 * - Agent only receives final summary
 *
 * Usage:
 * const workflow = require('./trinity-trading-cycle.js');
 * await workflow.run(mcpTools);
 */

module.exports = {
  name: "Trinity Trading Cycle",
  version: "1.0.0",
  description: "Complete Trinity indicator trading cycle workflow",

  async run(tools, config = {}) {
    const startTime = new Date();
    const results = {
      timestamp: startTime.toISOString(),
      stages: [],
      trades: [],
      errors: [],
    };

    try {
      // Stage 1: Fetch Market Data
      console.log("[WORKFLOW] Stage 1: Fetching market data...");
      const symbols = config.symbols || [
        "BTC/USDT",
        "ETH/USDT",
        "SOL/USDT",
        "BNB/USDT",
        "XRP/USDT",
      ];

      const marketData = await tools.fetchMarketData({
        symbols,
        include_indicators: true,
      });

      results.stages.push({
        name: "Fetch Market Data",
        status: "success",
        symbols_fetched: Object.keys(marketData).length,
        timestamp: new Date().toISOString(),
      });

      // Stage 2: Generate Trinity Signals
      console.log("[WORKFLOW] Stage 2: Generating Trinity signals...");
      const signals = await tools.getTrinitySignals({
        symbols,
        min_confluence: config.min_confluence || 60,
      });

      const entrySignals = Object.entries(signals)
        .filter(([_, signal]) => signal.is_entry_signal)
        .map(([symbol, signal]) => ({
          symbol,
          confidence: signal.confidence,
          confluence_score: signal.confluence_score,
          signals_met: signal.signals_met,
        }));

      results.stages.push({
        name: "Generate Trinity Signals",
        status: "success",
        signals_generated: entrySignals.length,
        signals: entrySignals,
        timestamp: new Date().toISOString(),
      });

      // Stage 3: Check Portfolio
      console.log("[WORKFLOW] Stage 3: Checking portfolio...");
      const portfolio = await tools.getPortfolio({
        include_history: false,
      });

      results.stages.push({
        name: "Check Portfolio",
        status: "success",
        positions_open: portfolio.positions.length,
        available_capital: portfolio.available_capital,
        timestamp: new Date().toISOString(),
      });

      // Stage 4: Execute Entry Signals
      if (entrySignals.length > 0 && portfolio.available_capital > 0) {
        console.log("[WORKFLOW] Stage 4: Executing entry signals...");

        for (const signal of entrySignals) {
          try {
            // Get current price from market data
            const currentPrice = marketData[signal.symbol]?.price;
            if (!currentPrice) continue;

            // Determine position size based on confidence
            let sizePercent = 1.0;
            if (signal.confidence >= 0.8) sizePercent = 3.0;
            else if (signal.confidence >= 0.6) sizePercent = 2.0;

            // Calculate stop loss and take profit
            const stopLoss = currentPrice * 0.97; // 3% below entry
            const takeProfit = currentPrice * 1.05; // 5% above entry (roughly 1.67:1 reward/risk)

            const trade = await tools.executeTrade({
              symbol: signal.symbol,
              side: "long",
              size_percent: sizePercent,
              entry_price: currentPrice,
              stop_loss: stopLoss,
              take_profit: takeProfit,
            });

            results.trades.push({
              symbol: signal.symbol,
              status: "executed",
              confidence: signal.confidence,
              confluence: signal.confluence_score,
              entry_price: currentPrice,
              size_percent: sizePercent,
              stop_loss: stopLoss,
              take_profit: takeProfit,
              trade_id: trade.id,
              timestamp: new Date().toISOString(),
            });
          } catch (error) {
            results.errors.push({
              symbol: signal.symbol,
              error: error.message,
              stage: "trade_execution",
            });
          }
        }

        results.stages.push({
          name: "Execute Entry Signals",
          status: results.trades.length > 0 ? "success" : "no_trades",
          trades_executed: results.trades.length,
          timestamp: new Date().toISOString(),
        });
      }

      // Stage 5: Log Results
      console.log("[WORKFLOW] Stage 5: Logging results...");
      const logPath = `/tmp/trinity-workflow-${startTime.getTime()}.json`;
      const fs = require("fs");
      fs.writeFileSync(logPath, JSON.stringify(results, null, 2));

      results.stages.push({
        name: "Log Results",
        status: "success",
        log_file: logPath,
        timestamp: new Date().toISOString(),
      });

      // Stage 6: Generate Summary (Only this enters agent context)
      console.log("[WORKFLOW] Stage 6: Generating summary...");
      const summary = {
        timestamp: startTime.toISOString(),
        cycle_duration_ms: new Date() - startTime,
        signals_found: entrySignals.length,
        trades_executed: results.trades.length,
        average_confluence:
          entrySignals.length > 0
            ? (
                entrySignals.reduce((sum, s) => sum + s.confluence_score, 0) /
                entrySignals.length
              ).toFixed(0)
            : 0,
        average_confidence:
          entrySignals.length > 0
            ? (
                entrySignals.reduce((sum, s) => sum + s.confidence, 0) /
                entrySignals.length * 100
              ).toFixed(0) + "%"
            : "N/A",
        log_file: logPath,
        full_results_available: true,
        data_outside_context: true,
        context_tokens_saved: "~45000", // Estimated tokens not in context
      };

      results.stages.push({
        name: "Generate Summary",
        status: "success",
        summary,
        timestamp: new Date().toISOString(),
      });

      return summary;
    } catch (error) {
      results.errors.push({
        error: error.message,
        stage: "unknown",
      });

      return {
        status: "error",
        error: error.message,
        partial_results: results,
      };
    }
  },
};
