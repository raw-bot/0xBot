import type { DashboardPosition } from '../../types/dashboard';
import { formatMoney, formatSignedMoney, formatSignedPercent } from '../../lib/format';

interface PositionsGridProps {
  positions: DashboardPosition[];
}

function PositionCard({ position }: { position: DashboardPosition }) {
  const isProfit = position.unrealized_pnl >= 0;
  const pnlColor = isProfit ? 'text-green-600' : 'text-red-500';

  return (
    <div className="bg-white/95 rounded-sm p-3 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex justify-between items-start">
        <div>
          <h4 className="font-semibold text-sm">
            {position.symbol}
            <span className="ml-2 text-[10px] font-semibold bg-yellow-200/60 px-1.5 py-0.5 rounded-sm">
              {position.leverage}x
            </span>
          </h4>
          <span className="text-xs text-gray-400">
            {position.side.toUpperCase()} · {formatMoney(position.quantity, 4)}
          </span>
        </div>
        <div className="text-right">
          <div className={`text-sm font-semibold ${pnlColor}`}>
            {formatSignedMoney(position.unrealized_pnl)}
          </div>
          <div className="text-[10px] text-gray-400">
            {formatSignedPercent(position.unrealized_pnl_pct)}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function PositionsGrid({ positions }: PositionsGridProps) {
  if (!positions.length) {
    return (
      <div className="text-center text-gray-400 py-8">
        No open positions
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-2">
      {positions.map((p) => (
        <PositionCard key={p.symbol} position={p} />
      ))}
    </div>
  );
}
