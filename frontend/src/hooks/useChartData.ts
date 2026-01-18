import { useMemo } from 'react';
import type { EquitySnapshot, TradeHistoryItem } from '../types/dashboard.js';

export interface ChartDataPoint {
  name: string;
  equity: number;
  totalPnl: number;
  [key: string]: number | string;
}

export function useChartData(
  snapshots: EquitySnapshot[],
  trades: TradeHistoryItem[],
  initialCapital: number
): ChartDataPoint[] {
  return useMemo(() => {
    if (!snapshots.length) return [];

    const pnlByCrypto: Record<string, Map<number, number>> = {};
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
    }

    return snapshots.map((s) => {
      const ts = new Date(s.timestamp).getTime();
      const label = new Date(s.timestamp).toLocaleTimeString('fr-FR', {
        hour: '2-digit',
        minute: '2-digit',
      });

      const point: ChartDataPoint = {
        name: label,
        equity: s.equity - initialCapital,
        totalPnl: s.equity - initialCapital,
      };

      for (const [symbol, pnlMap] of Object.entries(pnlByCrypto)) {
        const key = symbol.replace('/', '_');
        let closestVal = 0;
        for (const [tradeTs, val] of pnlMap) {
          if (tradeTs <= ts) closestVal = val;
        }
        point[key] = closestVal;
      }

      return point;
    });
  }, [snapshots, trades, initialCapital]);
}
