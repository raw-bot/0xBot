/**
 * Shared constants for the application
 */

export const CARD_STYLE = 'bg-gradient-to-b from-[#d45a2e] to-[#b84a1f] rounded-2xl p-lg text-white shadow-lg border border-white/10';

export const CRYPTO_COLORS: Record<string, string> = {
  'BTC/USDT': '#F7931A',
  'ETH/USDT': '#627EEA',
  'SOL/USDT': '#9945FF',
  'BNB/USDT': '#F0B90B',
  'XRP/USDT': '#5a5a5a',
};

export const SENTIMENT_THRESHOLDS = {
  EXTREME_FEAR: 20,
  FEAR: 40,
  NEUTRAL: 60,
  GREED: 80,
} as const;

export const SENTIMENT_COLORS = {
  EXTREME_FEAR: '#22c55e',
  FEAR: '#84cc16',
  NEUTRAL: '#eab308',
  GREED: '#f97316',
  EXTREME_GREED: '#ef4444',
} as const;

export function getSentimentColor(value: number): string {
  if (value <= SENTIMENT_THRESHOLDS.EXTREME_FEAR) return SENTIMENT_COLORS.EXTREME_FEAR;
  if (value <= SENTIMENT_THRESHOLDS.FEAR) return SENTIMENT_COLORS.FEAR;
  if (value <= SENTIMENT_THRESHOLDS.NEUTRAL) return SENTIMENT_COLORS.NEUTRAL;
  if (value <= SENTIMENT_THRESHOLDS.GREED) return SENTIMENT_COLORS.GREED;
  return SENTIMENT_COLORS.EXTREME_GREED;
}

export const TRADE_STATUS = {
  OPEN: { label: 'open', className: 'bg-gray-200 text-gray-600' },
  PROFIT: { label: 'profit', className: 'bg-yellow-300 text-gray-800' },
  LOSS: { label: 'loss', className: 'bg-red-100 text-red-600' },
} as const;

export function getTradeStatus(pnl: number): { status: string; className: string } {
  if (pnl === 0) return { status: TRADE_STATUS.OPEN.label, className: TRADE_STATUS.OPEN.className };
  if (pnl > 0) return { status: TRADE_STATUS.PROFIT.label, className: TRADE_STATUS.PROFIT.className };
  return { status: TRADE_STATUS.LOSS.label, className: TRADE_STATUS.LOSS.className };
}
