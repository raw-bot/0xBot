/**
 * Stats Widgets: Win Rate Ring + Sentiment Gauge + HODL Comparison
 */
import type { DashboardBot, SentimentData } from '../../types/dashboard';

interface StatsWidgetsProps {
  bot: DashboardBot | null;
  sentiment: SentimentData | null;
  totalReturnPct: number;
  hodlReturnPct: number;
  alphaPct: number;
  btcCurrentPrice: number;
}

function WinRateRing({ winRate, totalTrades }: { winRate: number; totalTrades: number }) {
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (winRate / 100) * circumference;

  return (
    <div className="bg-gradient-to-b from-[#c8c6c0] to-[#bfbdb7] rounded-[30px] p-4 flex flex-col items-center">
      <div className="text-xs text-gray-500 mb-2 self-start">daily</div>
      <div className="relative w-24 h-24">
        <svg className="-rotate-90" width="100" height="100">
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="none"
            stroke="rgba(0,0,0,0.08)"
            strokeWidth="10"
          />
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="none"
            stroke="#f5ff00"
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-all duration-700"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-2xl font-bold">{Math.round(winRate)}</span>
          <span className="text-sm">%</span>
        </div>
      </div>
      <div className="text-sm text-gray-600 mt-2">win rate</div>
      <div className="border-t border-black/5 mt-3 pt-3 text-center w-full">
        <div className="text-lg font-semibold">{totalTrades}</div>
        <div className="text-xs text-gray-500">total trades</div>
      </div>
    </div>
  );
}

function SentimentGauge({ sentiment }: { sentiment: SentimentData | null }) {
  if (!sentiment?.available || !sentiment.fear_greed) {
    return (
      <div className="bg-gradient-to-b from-[#c8c6c0] to-[#bfbdb7] rounded-[30px] p-4">
        <div className="text-xs text-gray-500">market sentiment</div>
        <div className="text-center text-gray-400 py-4">Loading...</div>
      </div>
    );
  }

  const fg = sentiment.fear_greed;
  const value = fg.value;
  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;

  const getColorClass = (val: number) => {
    if (val <= 20) return 'stroke-green-500';
    if (val <= 40) return 'stroke-lime-500';
    if (val <= 60) return 'stroke-yellow-500';
    if (val <= 80) return 'stroke-orange-500';
    return 'stroke-red-500';
  };

  return (
    <div className="bg-gradient-to-b from-[#c8c6c0] to-[#bfbdb7] rounded-[30px] p-4">
      <div className="flex justify-between items-center mb-2">
        <span className="text-xs text-gray-500">market sentiment</span>
        <span className="text-xs text-gray-400">{sentiment.timestamp?.split('T')[1]?.slice(0, 5) || '--'}</span>
      </div>
      <div className="flex items-center gap-3">
        <div className="relative w-16 h-16">
          <svg className="-rotate-90" width="70" height="70" viewBox="0 0 70 70">
            <circle cx="35" cy="35" r={radius} fill="none" stroke="rgba(0,0,0,0.08)" strokeWidth="6" />
            <circle
              cx="35"
              cy="35"
              r={radius}
              fill="none"
              strokeWidth="6"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              className={`transition-all duration-700 ${getColorClass(value)}`}
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center text-lg font-bold">
            {value}
          </div>
        </div>
        <div>
          <div className="font-semibold">{fg.label}</div>
          <div className="text-xs text-gray-500">
            Yesterday: {fg.yesterday} | Week: {fg.last_week}
          </div>
        </div>
      </div>
      {sentiment.global_market && (
        <div className="flex gap-3 pt-3 border-t border-black/5 mt-3 text-center">
          <div className="flex-1">
            <div className="text-sm font-semibold">{sentiment.global_market.btc_dominance.toFixed(1)}%</div>
            <div className="text-[8px] text-gray-500 uppercase">BTC Dom</div>
          </div>
          <div className="flex-1">
            <div className={`text-sm font-semibold ${sentiment.global_market.market_cap_change_24h >= 0 ? 'text-green-600' : 'text-red-500'}`}>
              {sentiment.global_market.market_cap_change_24h >= 0 ? '+' : ''}{sentiment.global_market.market_cap_change_24h.toFixed(2)}%
            </div>
            <div className="text-[8px] text-gray-500 uppercase">24H</div>
          </div>
        </div>
      )}
    </div>
  );
}

function HodlComparison({
  botReturn,
  hodlReturn,
  alpha,
  btcPrice,
}: {
  botReturn: number;
  hodlReturn: number;
  alpha: number;
  btcPrice: number;
}) {
  return (
    <div className="bg-gradient-to-b from-[#c8c6c0] to-[#bfbdb7] rounded-[30px] p-4">
      <div className="flex justify-between items-center mb-2">
        <span className="text-xs text-gray-500">bot vs hodl btc</span>
        <span className="text-xs text-gray-400">${btcPrice.toLocaleString('fr-FR', { maximumFractionDigits: 0 })}</span>
      </div>
      <div className="space-y-2">
        <div className="flex justify-between">
          <span className="text-gray-600 text-sm">📈 Bot</span>
          <span className={`font-semibold ${botReturn >= 0 ? 'text-green-600' : 'text-red-500'}`}>
            {botReturn >= 0 ? '+' : ''}{botReturn.toFixed(2)}%
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600 text-sm">📊 HODL BTC</span>
          <span className="font-semibold text-[#F7931A]">
            {hodlReturn >= 0 ? '+' : ''}{hodlReturn.toFixed(2)}%
          </span>
        </div>
        <div className="border-t border-black/10 pt-2 flex justify-between">
          <span className="text-gray-600 text-sm">🎯 Alpha</span>
          <span className={`font-bold text-lg ${alpha >= 0 ? 'text-green-600' : 'text-red-500'}`}>
            {alpha >= 0 ? '+' : ''}{alpha.toFixed(2)}%
          </span>
        </div>
      </div>
    </div>
  );
}

export default function StatsWidgets({
  bot,
  sentiment,
  totalReturnPct,
  hodlReturnPct,
  alphaPct,
  btcCurrentPrice,
}: StatsWidgetsProps) {
  const winRate = bot && bot.total_trades > 0 ? (bot.winning_trades / bot.total_trades) * 100 : 0;

  return (
    <div className="flex flex-col gap-3">
      <WinRateRing winRate={winRate} totalTrades={bot?.total_trades ?? 0} />
      <SentimentGauge sentiment={sentiment} />
      <HodlComparison
        botReturn={totalReturnPct}
        hodlReturn={hodlReturnPct}
        alpha={alphaPct}
        btcPrice={btcCurrentPrice}
      />
    </div>
  );
}
