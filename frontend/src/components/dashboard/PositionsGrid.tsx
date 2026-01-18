/**
 * Positions Grid - displays open positions as cards
 */
import type { DashboardPosition } from '../../types/dashboard';

interface PositionsGridProps {
  positions: DashboardPosition[];
}

function formatMoney(num: number, decimals = 2): string {
  const parts = num.toFixed(decimals).split('.');
  parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  return parts.join(',');
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
      {positions.map((p) => {
        const isProfit = p.unrealized_pnl >= 0;
        return (
          <div
            key={p.symbol}
            className="bg-white/95 rounded-2xl p-3 shadow-sm hover:shadow-md transition-shadow"
          >
            <div className="flex justify-between items-start">
              <div>
                <h4 className="font-semibold text-sm">
                  {p.symbol}
                  <span className="ml-2 text-[10px] font-semibold bg-yellow-200/60 px-1.5 py-0.5 rounded">
                    {p.leverage}x
                  </span>
                </h4>
                <span className="text-xs text-gray-400">
                  {p.side.toUpperCase()} · {formatMoney(p.quantity, 4)}
                </span>
              </div>
              <div className="text-right">
                <div className={`text-sm font-semibold ${isProfit ? 'text-green-600' : 'text-red-500'}`}>
                  {isProfit ? '+' : ''}${formatMoney(p.unrealized_pnl)}
                </div>
                <div className="text-[10px] text-gray-400">
                  {p.unrealized_pnl_pct >= 0 ? '+' : ''}{p.unrealized_pnl_pct.toFixed(2)}%
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
