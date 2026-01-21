import type { DashboardBot, TradeHistoryItem } from "../../types/dashboard.js";

interface PaperTradingMetricsProps {
  bot: DashboardBot | null;
  trades: TradeHistoryItem[];
}

export default function PaperTradingMetrics({
  bot,
  trades,
}: PaperTradingMetricsProps) {
  // Calculate metrics from trades
  const totalTrades = trades.length;
  const winningTrades = trades.filter((t) => t.pnl > 0).length;
  const losingTrades = trades.filter((t) => t.pnl < 0).length;
  const winRate = totalTrades > 0 ? (winningTrades / totalTrades) * 100 : 0;

  const grossProfit = trades
    .filter((t) => t.pnl > 0)
    .reduce((sum, t) => sum + t.pnl, 0);
  const grossLoss = Math.abs(
    trades.filter((t) => t.pnl < 0).reduce((sum, t) => sum + t.pnl, 0),
  );
  const netPnL = grossProfit - grossLoss;
  const profitFactor =
    grossLoss > 0 ? grossProfit / grossLoss : grossProfit > 0 ? Infinity : 0;

  const avgWin = winningTrades > 0 ? grossProfit / winningTrades : 0;
  const avgLoss = losingTrades > 0 ? grossLoss / losingTrades : 0;

  // Drawdown calculation
  let peak = bot?.initial_capital ?? 10000;
  let maxDrawdown = 0;
  let equity = peak;
  trades.forEach((t) => {
    equity += t.pnl;
    if (equity > peak) peak = equity;
    const drawdown = ((peak - equity) / peak) * 100;
    if (drawdown > maxDrawdown) maxDrawdown = drawdown;
  });

  // Status colors
  const getWinRateColor = (rate: number) => {
    if (rate >= 65) return "text-green-500";
    if (rate >= 55) return "text-yellow-500";
    return "text-red-500";
  };

  const getProfitFactorColor = (pf: number) => {
    if (pf >= 1.8) return "text-green-500";
    if (pf >= 1.5) return "text-yellow-500";
    return "text-red-500";
  };

  const getDrawdownColor = (dd: number) => {
    if (dd <= 25) return "text-green-500";
    if (dd <= 30) return "text-yellow-500";
    return "text-red-500";
  };

  const getStatusBadge = () => {
    if (winRate >= 65 && profitFactor >= 1.8 && maxDrawdown <= 25) {
      return { text: "GO LIVE", color: "bg-green-500" };
    }
    if (winRate >= 55 && profitFactor >= 1.5 && maxDrawdown <= 30) {
      return { text: "CONTINUE", color: "bg-yellow-500" };
    }
    return { text: "REVIEW", color: "bg-red-500" };
  };

  const status = getStatusBadge();

  return (
    <div className="space-y-4">
      {/* Header with status */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-700">
          Paper Trading Validation
        </h3>
        <span
          className={`${status.color} text-white text-xs font-bold px-3 py-1 rounded-full`}
        >
          {status.text}
        </span>
      </div>

      {/* Primary Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          label="Win Rate"
          value={`${winRate.toFixed(1)}%`}
          target="65-75%"
          colorClass={getWinRateColor(winRate)}
        />
        <MetricCard
          label="Profit Factor"
          value={profitFactor === Infinity ? "∞" : profitFactor.toFixed(2)}
          target=">1.8"
          colorClass={getProfitFactorColor(profitFactor)}
        />
        <MetricCard
          label="Max Drawdown"
          value={`${maxDrawdown.toFixed(1)}%`}
          target="<25%"
          colorClass={getDrawdownColor(maxDrawdown)}
        />
        <MetricCard
          label="Net P&L"
          value={`$${netPnL.toFixed(2)}`}
          target="+$"
          colorClass={netPnL >= 0 ? "text-green-500" : "text-red-500"}
        />
      </div>

      {/* Secondary Metrics */}
      <div className="grid grid-cols-3 md:grid-cols-6 gap-3 text-sm">
        <MiniMetric label="Total Trades" value={totalTrades.toString()} />
        <MiniMetric
          label="Wins"
          value={winningTrades.toString()}
          color="text-green-600"
        />
        <MiniMetric
          label="Losses"
          value={losingTrades.toString()}
          color="text-red-600"
        />
        <MiniMetric
          label="Avg Win"
          value={`$${avgWin.toFixed(2)}`}
          color="text-green-600"
        />
        <MiniMetric
          label="Avg Loss"
          value={`$${avgLoss.toFixed(2)}`}
          color="text-red-600"
        />
        <MiniMetric
          label="Gross Profit"
          value={`$${grossProfit.toFixed(2)}`}
          color="text-green-600"
        />
      </div>

      {/* Targets Reference */}
      <div className="text-xs text-gray-400 border-t pt-2">
        Targets: Win Rate 65-75% • Profit Factor &gt;1.8 • Drawdown &lt;25% •
        Sharpe &gt;1.2
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  target,
  colorClass,
}: {
  label: string;
  value: string;
  target: string;
  colorClass: string;
}) {
  return (
    <div className="bg-gray-50 rounded-lg p-3 text-center">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className={`text-2xl font-bold ${colorClass}`}>{value}</div>
      <div className="text-xs text-gray-400">Target: {target}</div>
    </div>
  );
}

function MiniMetric({
  label,
  value,
  color = "text-gray-700",
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div className="text-center">
      <div className="text-xs text-gray-500">{label}</div>
      <div className={`font-semibold ${color}`}>{value}</div>
    </div>
  );
}
