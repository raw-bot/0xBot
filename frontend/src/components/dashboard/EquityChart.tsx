/**
 * Equity Chart component using Recharts
 * Displays PnL curves for each crypto + total
 */
import { useMemo } from 'react';
import {
    Line,
    LineChart,
    ReferenceLine,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from 'recharts';
import type { EquitySnapshot, TradeHistoryItem } from '../../types/dashboard';

interface EquityChartProps {
  snapshots: EquitySnapshot[];
  trades: TradeHistoryItem[];
  initialCapital: number;
}

const CRYPTO_COLORS: Record<string, string> = {
  'BTC/USDT': '#F7931A',
  'ETH/USDT': '#627EEA',
  'SOL/USDT': '#9945FF',
  'BNB/USDT': '#F0B90B',
  'XRP/USDT': '#5a5a5a',
};

export default function EquityChart({
  snapshots,
  trades,
  initialCapital,
}: EquityChartProps) {
  const chartData = useMemo(() => {
    if (!snapshots.length) return [];

    // Build cumulative PnL per crypto
    const pnlByCrypto: Record<string, Map<number, number>> = {};
    const globalPnl = new Map<number, number>();
    let globalRunning = 0;

    const closedTrades = trades
      .filter((t) => t.pnl !== 0)
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

    for (const t of closedTrades) {
      const ts = new Date(t.timestamp).getTime();
      if (!pnlByCrypto[t.symbol]) {
        pnlByCrypto[t.symbol] = new Map();
      }
      const prev = [...pnlByCrypto[t.symbol].values()].pop() || 0;
      pnlByCrypto[t.symbol].set(ts, prev + t.pnl);
      globalRunning += t.pnl;
      globalPnl.set(ts, globalRunning);
    }

    // Map snapshots to chart data points
    return snapshots.map((s) => {
      const ts = new Date(s.timestamp).getTime();
      const date = new Date(s.timestamp);
      const label = date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });

      const point: Record<string, number | string> = {
        name: label,
        equity: s.equity - initialCapital,
      };

      // Find closest PnL values
      for (const [symbol, pnlMap] of Object.entries(pnlByCrypto)) {
        const key = symbol.replace('/', '_');
        let closestVal = 0;
        for (const [tradeTs, val] of pnlMap) {
          if (tradeTs <= ts) closestVal = val;
        }
        point[key] = closestVal;
      }

      // Total PnL
      let totalPnl = 0;
      for (const [tradeTs, val] of globalPnl) {
        if (tradeTs <= ts) totalPnl = val;
      }
      point.totalPnl = totalPnl;

      return point;
    });
  }, [snapshots, trades, initialCapital]);

  if (!chartData.length) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        No equity data available
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <XAxis dataKey="name" tick={{ fontSize: 10 }} stroke="#999" />
        <YAxis
          tickFormatter={(v) => `${v >= 0 ? '+' : ''}$${v}`}
          tick={{ fontSize: 10 }}
          stroke="#999"
        />
        <Tooltip
          formatter={(value: number) => [`$${value.toFixed(2)}`, '']}
          labelStyle={{ color: '#333' }}
        />
        <ReferenceLine y={0} stroke="#666" strokeWidth={2} />

        {/* Equity line */}
        <Line
          type="monotone"
          dataKey="equity"
          stroke="#999"
          strokeWidth={1.5}
          dot={false}
          name="Equity"
        />

        {/* Total PnL (bold yellow) */}
        <Line
          type="monotone"
          dataKey="totalPnl"
          stroke="#f5ff00"
          strokeWidth={3}
          dot={false}
          name="Total PnL"
        />

        {/* Per-crypto lines */}
        {Object.entries(CRYPTO_COLORS).map(([symbol, color]) => (
          <Line
            key={symbol}
            type="monotone"
            dataKey={symbol.replace('/', '_')}
            stroke={color}
            strokeWidth={1.5}
            dot={false}
            name={symbol.split('/')[0]}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
