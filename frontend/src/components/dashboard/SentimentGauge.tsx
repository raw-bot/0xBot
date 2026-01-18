import type { SentimentData } from '../../types/dashboard.js';
import { formatSignedPercent } from '../../lib/format.js';
import { CARD_STYLE, getSentimentColor } from '../../lib/constants.js';
import CircularGauge from './CircularGauge.js';

interface SentimentGaugeProps {
  sentiment: SentimentData | null;
}

export default function SentimentGauge({ sentiment }: SentimentGaugeProps): JSX.Element {
  if (!sentiment?.available || !sentiment.fear_greed) {
    return (
      <div className={CARD_STYLE}>
        <div className="text-xs text-white/60">market sentiment</div>
        <div className="text-center text-white/50 py-4">Loading...</div>
      </div>
    );
  }

  const fg = sentiment.fear_greed;
  const timeStr = sentiment.timestamp?.split('T')[1]?.slice(0, 5) || '--';

  return (
    <div className={CARD_STYLE}>
      <div className="flex justify-between items-center mb-2">
        <span className="text-xs text-white/60">market sentiment</span>
        <span className="text-xs text-white/50">{timeStr}</span>
      </div>
      <div className="flex items-center gap-3">
        <CircularGauge
          value={fg.value}
          radius={28}
          strokeWidth={6}
          color={getSentimentColor(fg.value)}
        >
          <span className="text-lg font-bold text-white">{fg.value}</span>
        </CircularGauge>
        <div>
          <div className="font-semibold text-white">{fg.label}</div>
          <div className="text-xs text-white/60">
            Yesterday: {fg.yesterday} | Week: {fg.last_week}
          </div>
        </div>
      </div>
      {sentiment.global_market && (
        <div className="flex gap-3 pt-3 border-t border-white/20 mt-3 text-center">
          <div className="flex-1">
            <div className="text-sm font-semibold text-white">
              {sentiment.global_market.btc_dominance.toFixed(1)}%
            </div>
            <div className="text-[8px] text-white/60 uppercase">BTC Dom</div>
          </div>
          <div className="flex-1">
            <div className={`text-sm font-semibold ${sentiment.global_market.market_cap_change_24h >= 0 ? 'text-green-400' : 'text-red-300'}`}>
              {formatSignedPercent(sentiment.global_market.market_cap_change_24h)}
            </div>
            <div className="text-[8px] text-white/60 uppercase">24H</div>
          </div>
        </div>
      )}
    </div>
  );
}
