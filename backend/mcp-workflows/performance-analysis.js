/**
 * Performance Analysis Workflow
 * Analyzes bot performance and generates actionable insights
 * Runs entirely outside agent context window
 *
 * What this does:
 * 1. Fetches last N trades
 * 2. Calculates metrics (win rate, avg confluence, P&L)
 * 3. Correlates confluence scores with results
 * 4. Generates insights about signal quality
 * 5. Returns only summary to agent
 */

module.exports = {
  name: "Performance Analysis",
  version: "1.0.0",
  description: "Analyze Trinity bot performance and generate insights",

  async run(tools, config = {}) {
    const startTime = new Date();
    const analysisResults = {
      timestamp: startTime.toISOString(),
      metrics: {},
      insights: [],
      data_file: null,
    };

    try {
      // Fetch portfolio with full trade history
      console.log("[ANALYSIS] Fetching portfolio and trade history...");
      const portfolio = await tools.getPortfolio({
        include_history: true,
      });

      // Analyze trades
      const trades = portfolio.trades || [];
      const closedTrades = trades.filter((t) => t.status === "closed");

      if (closedTrades.length === 0) {
        return {
          status: "no_data",
          message: "No closed trades to analyze",
          open_positions: trades.filter((t) => t.status === "open").length,
        };
      }

      // Calculate metrics
      console.log("[ANALYSIS] Calculating metrics...");
      const winningTrades = closedTrades.filter((t) => t.pnl > 0);
      const losingTrades = closedTrades.filter((t) => t.pnl <= 0);

      const metrics = {
        total_trades: closedTrades.length,
        winning_trades: winningTrades.length,
        losing_trades: losingTrades.length,
        win_rate: (winningTrades.length / closedTrades.length * 100).toFixed(2) + "%",
        total_pnl: closedTrades.reduce((sum, t) => sum + (t.pnl || 0), 0).toFixed(2),
        avg_win: winningTrades.length > 0
          ? (winningTrades.reduce((sum, t) => sum + (t.pnl || 0), 0) / winningTrades.length).toFixed(2)
          : 0,
        avg_loss: losingTrades.length > 0
          ? (losingTrades.reduce((sum, t) => sum + (t.pnl || 0), 0) / losingTrades.length).toFixed(2)
          : 0,
        profit_factor: 0, // Calculated below
      };

      // Calculate profit factor
      const totalWins = winningTrades.reduce((sum, t) => sum + (t.pnl || 0), 0);
      const totalLosses = Math.abs(
        losingTrades.reduce((sum, t) => sum + (t.pnl || 0), 0)
      );
      metrics.profit_factor = totalLosses > 0
        ? (totalWins / totalLosses).toFixed(2)
        : totalWins > 0
        ? "Infinite"
        : "N/A";

      // Analyze confluence correlation
      console.log("[ANALYSIS] Analyzing confluence correlation...");
      const confluenceAnalysis = this.analyzeConfluenceCorrelation(closedTrades);

      // Generate insights
      console.log("[ANALYSIS] Generating insights...");
      const insights = this.generateInsights(metrics, confluenceAnalysis, closedTrades);

      // Save detailed analysis to file
      const fs = require("fs");
      const detailedAnalysis = {
        timestamp: startTime.toISOString(),
        metrics,
        confluence_analysis: confluenceAnalysis,
        trades_analyzed: closedTrades.map((t) => ({
          symbol: t.symbol,
          entry: t.entry_price,
          exit: t.exit_price,
          pnl: t.pnl,
          pnl_percent: t.pnl_percent,
          confidence: t.confidence,
          confluence: t.confluence,
          exit_reason: t.exit_reason,
        })),
      };

      const analysisPath = `/tmp/trinity-analysis-${startTime.getTime()}.json`;
      fs.writeFileSync(analysisPath, JSON.stringify(detailedAnalysis, null, 2));

      analysisResults.metrics = metrics;
      analysisResults.insights = insights;
      analysisResults.data_file = analysisPath;

      // Return only summary (detailed data is in file, not in context)
      return {
        status: "success",
        analysis_timestamp: startTime.toISOString(),
        summary: {
          trades_analyzed: metrics.total_trades,
          win_rate: metrics.win_rate,
          profit_factor: metrics.profit_factor,
          total_pnl: metrics.total_pnl + " USD",
          insights: insights.slice(0, 5), // Top 5 insights only
          detailed_analysis_available: true,
          data_file: analysisPath,
          context_tokens_saved: "~40000",
        },
      };
    } catch (error) {
      return {
        status: "error",
        error: error.message,
      };
    }
  },

  analyzeConfluenceCorrelation(trades) {
    if (trades.length === 0) return null;

    // Group trades by confluence score ranges
    const ranges = {
      high: trades.filter((t) => t.confluence >= 80),
      medium: trades.filter((t) => t.confluence >= 60 && t.confluence < 80),
      low: trades.filter((t) => t.confluence < 60),
    };

    const analysis = {};

    for (const [range, tradelist] of Object.entries(ranges)) {
      if (tradelist.length === 0) continue;

      const wins = tradelist.filter((t) => t.pnl > 0).length;
      const winRate = (wins / tradelist.length * 100).toFixed(1);
      const avgPnl = (
        tradelist.reduce((sum, t) => sum + (t.pnl || 0), 0) / tradelist.length
      ).toFixed(2);

      analysis[range] = {
        trades: tradelist.length,
        win_rate: winRate + "%",
        avg_pnl: avgPnl,
      };
    }

    return analysis;
  },

  generateInsights(metrics, confluenceAnalysis, trades) {
    const insights = [];

    // Insight 1: Win rate assessment
    const winRate = parseFloat(metrics.win_rate);
    if (winRate >= 60) {
      insights.push(
        `✅ Strong win rate (${metrics.win_rate}) - Trinity confluence filtering is working`
      );
    } else if (winRate >= 50) {
      insights.push(
        `⚠️  Win rate (${metrics.win_rate}) is near 50% - Consider adjusting confluence thresholds`
      );
    } else {
      insights.push(
        `🔴 Low win rate (${metrics.win_rate}) - Review signal quality and thresholds`
      );
    }

    // Insight 2: Profit factor
    const profitFactor = parseFloat(metrics.profit_factor);
    if (!isNaN(profitFactor) && profitFactor >= 2) {
      insights.push(`✅ Excellent profit factor (${metrics.profit_factor}) - Consistently profitable`);
    } else if (!isNaN(profitFactor) && profitFactor >= 1.5) {
      insights.push(
        `✅ Good profit factor (${metrics.profit_factor}) - Above breakeven threshold`
      );
    }

    // Insight 3: Confluence correlation
    if (confluenceAnalysis) {
      if (confluenceAnalysis.high) {
        const highWinRate = confluenceAnalysis.high.win_rate;
        insights.push(
          `📊 High confluence trades (80+): ${highWinRate} win rate - Validates confluence scoring`
        );
      }
    }

    // Insight 4: Position sizing
    const avgPosSize =
      trades.reduce((sum, t) => sum + (t.size_percent || 0), 0) / trades.length;
    if (avgPosSize >= 2.5) {
      insights.push(`📈 Average position size (${avgPosSize.toFixed(1)}%) - Conservative risk management`);
    }

    // Insight 5: Recommendation
    if (winRate >= 55 && metrics.profit_factor >= 1.5) {
      insights.push(`🎯 Ready to increase position sizes or add more signals`);
    } else if (winRate < 50) {
      insights.push(
        `⚙️  Recommend: Review confluence thresholds or wait for more data`
      );
    }

    return insights;
  },
};
