import CircularGauge from './CircularGauge.js';
import { CARD_STYLE } from '../../lib/constants.js';

interface WinRateRingProps {
  winRate: number;
  totalTrades: number;
}

export default function WinRateRing({ winRate, totalTrades }: WinRateRingProps): JSX.Element {
  return (
    <div className={`${CARD_STYLE} flex flex-col items-center`}>
      <div className="text-xs text-white/60 mb-2 self-start">daily</div>
      <CircularGauge value={winRate} radius={42} strokeWidth={10} color="#ff9d3d">
        <span className="text-2xl font-bold text-white">{Math.round(winRate)}</span>
        <span className="text-sm text-white">%</span>
      </CircularGauge>
      <div className="text-sm text-white/80 mt-2">win rate</div>
      <div className="border-t border-white/20 mt-3 pt-3 text-center w-full">
        <div className="text-lg font-semibold text-white">{totalTrades}</div>
        <div className="text-xs text-white/60">total trades</div>
      </div>
    </div>
  );
}
