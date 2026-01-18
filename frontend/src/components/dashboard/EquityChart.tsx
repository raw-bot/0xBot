import {
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { EquitySnapshot, TradeHistoryItem } from '../../types/dashboard.js';
import { useChartData } from '../../hooks/useChartData.js';
import { CRYPTO_COLORS } from '../../lib/constants.js';

interface EquityChartProps {
  snapshots: EquitySnapshot[];
  trades: TradeHistoryItem[];
  initialCapital: number;
}

export default function EquityChart({
  snapshots,
  trades,
  initialCapital,
}: EquityChartProps): JSX.Element {
  const chartData = useChartData(snapshots, trades, initialCapital);

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

        <Line
          type="monotone"
          dataKey="equity"
          stroke="#999"
          strokeWidth={1.5}
          strokeOpacity={0.8}
          dot={false}
          name="Equity"
        />

        <Line
          type="monotone"
          dataKey="totalPnl"
          stroke="#f5ff00"
          strokeWidth={3}
          strokeOpacity={1.0}
          dot={false}
          name="Total PnL"
        />

        {Object.entries(CRYPTO_COLORS).map(([symbol, color]) => (
          <Line
            key={symbol}
            type="monotone"
            dataKey={symbol.replace('/', '_')}
            stroke={color}
            strokeWidth={1.5}
            strokeOpacity={0.8}
            dot={false}
            name={symbol.split('/')[0]}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
