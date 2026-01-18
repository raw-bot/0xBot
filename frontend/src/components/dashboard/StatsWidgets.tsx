import type { DashboardBot, SentimentData } from '../../types/dashboard.js';
import WinRateRing from './WinRateRing.js';
import SentimentGauge from './SentimentGauge.js';
import HodlComparison from './HodlComparison.js';

interface StatsWidgetsProps {
  bot: DashboardBot | null;
  sentiment: SentimentData | null;
  totalReturnPct: number;
  hodlReturnPct: number;
  alphaPct: number;
  btcCurrentPrice: number;
}

export default function StatsWidgets({
  bot,
  sentiment,
  totalReturnPct,
  hodlReturnPct,
  alphaPct,
  btcCurrentPrice,
}: StatsWidgetsProps): JSX.Element {
  const winRate = bot && bot.total_trades > 0
    ? (bot.winning_trades / bot.total_trades) * 100
    : 0;

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
