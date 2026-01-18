import { formatSignedPercent } from '../../lib/format.js';
import { CARD_STYLE } from '../../lib/constants.js';

interface ComparisonRowProps {
  label: string;
  icon: string;
  value: number;
  colorClass: string;
  isBold?: boolean;
}

function ComparisonRow({ label, icon, value, colorClass, isBold }: ComparisonRowProps): JSX.Element {
  return (
    <div className="flex justify-between">
      <span className="text-white/70 text-sm">{icon} {label}</span>
      <span className={`${isBold ? 'font-bold text-lg' : 'font-semibold'} ${colorClass}`}>
        {formatSignedPercent(value)}
      </span>
    </div>
  );
}

interface HodlComparisonProps {
  botReturn: number;
  hodlReturn: number;
  alpha: number;
  btcPrice: number;
}

export default function HodlComparison({
  botReturn,
  hodlReturn,
  alpha,
  btcPrice,
}: HodlComparisonProps): JSX.Element {
  return (
    <div className={CARD_STYLE}>
      <div className="flex justify-between items-center mb-2">
        <span className="text-xs text-white/60">bot vs hodl btc</span>
        <span className="text-xs text-white/50">
          ${btcPrice.toLocaleString('fr-FR', { maximumFractionDigits: 0 })}
        </span>
      </div>
      <div className="space-y-2">
        <div className={botReturn >= 0 ? 'bg-orange-500/20 rounded-sm px-2 py-1' : ''}>
          <ComparisonRow
            label="Bot"
            icon=""
            value={botReturn}
            colorClass={botReturn >= 0 ? 'text-orange-300' : 'text-red-300'}
          />
        </div>
        <div className="bg-orange-500/20 rounded-sm px-2 py-1">
          <ComparisonRow
            label="HODL BTC"
            icon=""
            value={hodlReturn}
            colorClass="text-orange-300"
          />
        </div>
        <div className="border-t border-white/20 pt-2">
          <div className={alpha >= 0 ? 'bg-orange-500/20 rounded-sm px-2 py-1' : ''}>
            <ComparisonRow
              label="Alpha"
              icon=""
              value={alpha}
              colorClass={alpha >= 0 ? 'text-orange-300' : 'text-red-300'}
              isBold
            />
          </div>
        </div>
      </div>
    </div>
  );
}
