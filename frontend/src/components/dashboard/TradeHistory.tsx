/**
 * Trade History Table with sorting
 */
import { useMemo, useState } from 'react';
import type { TradeHistoryItem } from '../../types/dashboard';

interface TradeHistoryProps {
  trades: TradeHistoryItem[];
}

type SortKey = 'timestamp' | 'symbol' | 'pnl' | 'fees';
type SortDir = 'asc' | 'desc';

function formatMoney(num: number, decimals = 2): string {
  const parts = num.toFixed(decimals).split('.');
  parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  return parts.join(',');
}

export default function TradeHistory({ trades }: TradeHistoryProps) {
  const [sortKey, setSortKey] = useState<SortKey>('timestamp');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  const sortedTrades = useMemo(() => {
    const sorted = [...trades].sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case 'timestamp':
          cmp = new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
          break;
        case 'symbol':
          cmp = a.symbol.localeCompare(b.symbol);
          break;
        case 'pnl':
          cmp = a.pnl - b.pnl;
          break;
        case 'fees':
          cmp = a.fees - b.fees;
          break;
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return sorted.slice(0, 30); // Show last 30
  }, [trades, sortKey, sortDir]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  if (!trades.length) {
    return (
      <div className="text-center text-gray-400 py-8">
        No trades yet
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-400 uppercase">
            <th className="p-2 cursor-pointer hover:text-gray-600" onClick={() => handleSort('symbol')}>
              Symbol {sortKey === 'symbol' && (sortDir === 'asc' ? '▲' : '▼')}
            </th>
            <th className="p-2">Side</th>
            <th className="p-2">Status</th>
            <th className="p-2">Size</th>
            <th className="p-2">Entry</th>
            <th className="p-2">Exit</th>
            <th className="p-2 cursor-pointer hover:text-gray-600" onClick={() => handleSort('fees')}>
              Fees {sortKey === 'fees' && (sortDir === 'asc' ? '▲' : '▼')}
            </th>
            <th className="p-2 cursor-pointer hover:text-gray-600" onClick={() => handleSort('pnl')}>
              PnL {sortKey === 'pnl' && (sortDir === 'asc' ? '▲' : '▼')}
            </th>
            <th className="p-2 cursor-pointer hover:text-gray-600" onClick={() => handleSort('timestamp')}>
              Time {sortKey === 'timestamp' && (sortDir === 'asc' ? '▲' : '▼')}
            </th>
          </tr>
        </thead>
        <tbody>
          {sortedTrades.map((t, i) => {
            const isEntry = t.pnl === 0;
            const isProfit = t.pnl > 0;
            const status = isEntry ? 'open' : isProfit ? 'profit' : 'loss';

            return (
              <tr
                key={`${t.timestamp}-${i}`}
                className={`border-b border-gray-100 hover:bg-gray-50 ${isProfit ? 'bg-yellow-50/50' : ''}`}
              >
                <td className="p-2 font-semibold">{t.symbol}</td>
                <td className="p-2">{t.side.toUpperCase()}</td>
                <td className="p-2">
                  <span
                    className={`px-2 py-1 rounded text-[10px] font-semibold ${
                      status === 'open'
                        ? 'bg-gray-200 text-gray-600'
                        : status === 'profit'
                        ? 'bg-yellow-300 text-gray-800'
                        : 'bg-red-100 text-red-600'
                    }`}
                  >
                    {status}
                  </span>
                </td>
                <td className="p-2">${formatMoney(t.margin)}</td>
                <td className="p-2">${formatMoney(t.entry_price)}</td>
                <td className="p-2">{t.exit_price ? `$${formatMoney(t.exit_price)}` : '-'}</td>
                <td className="p-2 text-red-500">-${formatMoney(t.fees)}</td>
                <td className={`p-2 font-semibold ${isProfit ? 'text-green-600' : t.pnl < 0 ? 'text-red-500' : ''}`}>
                  {t.pnl !== 0 ? `${t.pnl >= 0 ? '+' : ''}$${formatMoney(t.pnl)}` : '-'}
                </td>
                <td className="p-2 text-gray-400">
                  {new Date(t.timestamp).toLocaleString('fr-FR', {
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
