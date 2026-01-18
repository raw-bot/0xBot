import { useMemo, useState } from "react";
import { getTradeStatus } from "../../lib/constants.js";
import { formatMoney, formatSignedMoney } from "../../lib/format.js";
import type { TradeHistoryItem } from "../../types/dashboard.js";

interface TradeHistoryProps {
  trades: TradeHistoryItem[];
}

type SortKey = "timestamp" | "symbol" | "pnl" | "fees";
type SortDir = "asc" | "desc";

interface SortableHeaderProps {
  label: string;
  sortKey: SortKey;
  currentKey: SortKey;
  currentDir: SortDir;
  onSort: (key: SortKey) => void;
  align?: "left" | "right";
}

function SortableHeader({
  label,
  sortKey,
  currentKey,
  currentDir,
  onSort,
  align = "right",
}: SortableHeaderProps): JSX.Element {
  const isActive = currentKey === sortKey;
  const arrow = isActive ? (currentDir === "asc" ? " ASC" : " DESC") : "";

  if (align === "left") {
    return (
      <th
        className="py-3 px-2 cursor-pointer hover:text-gray-600 text-left"
        onClick={() => onSort(sortKey)}
      >
        {label}
        {arrow}
      </th>
    );
  }

  return (
    <th
      className="py-3 px-2 cursor-pointer hover:text-gray-600"
      onClick={() => onSort(sortKey)}
    >
      <div className="flex justify-end items-center gap-1">
        {label}
        {arrow}
      </div>
    </th>
  );
}

function TradeRow({
  trade,
  index,
}: {
  trade: TradeHistoryItem;
  index: number;
}): JSX.Element {
  const isProfit = trade.pnl > 0;
  const { status, className: statusClass } = getTradeStatus(trade.pnl);

  const formattedTime = new Date(trade.timestamp).toLocaleString("fr-FR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });

  let pnlColorClass = "";
  if (isProfit) {
    pnlColorClass = "text-green-600";
  } else if (trade.pnl < 0) {
    pnlColorClass = "text-red-500";
  }

  return (
    <tr
      key={`${trade.timestamp}-${index}`}
      className={`border-b border-gray-100 hover:bg-gray-50 ${
        isProfit ? "bg-yellow-50/50" : ""
      }`}
    >
      <td className="py-3 px-2 font-semibold text-left">{trade.symbol}</td>
      <td className="py-3 px-2 text-center">{trade.side.toUpperCase()}</td>
      <td className="py-3 px-2 text-center">
        <span
          className={`px-2 py-1 rounded-sm text-[10px] font-semibold ${statusClass}`}
        >
          {status}
        </span>
      </td>
      <td className="py-3 px-2">
        <div className="flex justify-end items-center gap-1">
          ${formatMoney(trade.margin)}
          <span className="text-[10px] text-gray-400 font-normal">
            {trade.leverage}x
          </span>
        </div>
      </td>
      <td className="py-3 px-2">
        <div className="flex justify-end">
          ${formatMoney(trade.entry_price)}
        </div>
      </td>
      <td className="py-3 px-2">
        <div className="flex justify-end">
          {trade.exit_price ? `$${formatMoney(trade.exit_price)}` : "-"}
        </div>
      </td>
      <td className="py-3 px-2 text-red-500">
        <div className="flex justify-end">-${formatMoney(trade.fees)}</div>
      </td>
      <td className={`py-3 px-2 font-semibold ${pnlColorClass}`}>
        <div className="flex justify-end">
          {trade.pnl !== 0 ? formatSignedMoney(trade.pnl) : "-"}
        </div>
      </td>
      <td className="py-3 px-2 text-gray-400">
        <div className="flex justify-end">{formattedTime}</div>
      </td>
    </tr>
  );
}

export default function TradeHistory({
  trades,
}: TradeHistoryProps): JSX.Element {
  const [sortKey, setSortKey] = useState<SortKey>("timestamp");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const sortedTrades = useMemo(() => {
    const sorted = [...trades].sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case "timestamp":
          cmp =
            new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
          break;
        case "symbol":
          cmp = a.symbol.localeCompare(b.symbol);
          break;
        case "pnl":
          cmp = a.pnl - b.pnl;
          break;
        case "fees":
          cmp = a.fees - b.fees;
          break;
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
    return sorted.slice(0, 30);
  }, [trades, sortKey, sortDir]);

  function handleSort(key: SortKey): void {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  if (!trades.length) {
    return <div className="text-center text-gray-400 py-8">No trades yet</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm table-fixed">
        <thead>
          <tr className="text-xs text-gray-400 uppercase border-b border-gray-100">
            <SortableHeader
              label="Symbol"
              sortKey="symbol"
              currentKey={sortKey}
              currentDir={sortDir}
              onSort={handleSort}
              align="left"
            />
            <th className="py-3 px-2 w-[8%] text-center">Side</th>
            <th className="py-3 px-2 w-[10%] text-center">Status</th>
            <th className="py-3 px-2 w-[10%]">
              <div className="flex justify-end">Size</div>
            </th>
            <th className="py-3 px-2 w-[10%]">
              <div className="flex justify-end">Entry</div>
            </th>
            <th className="py-3 px-2 w-[10%]">
              <div className="flex justify-end">Exit</div>
            </th>
            <SortableHeader
              label="Fees"
              sortKey="fees"
              currentKey={sortKey}
              currentDir={sortDir}
              onSort={handleSort}
            />
            <SortableHeader
              label="PnL"
              sortKey="pnl"
              currentKey={sortKey}
              currentDir={sortDir}
              onSort={handleSort}
            />
            <SortableHeader
              label="Time"
              sortKey="timestamp"
              currentKey={sortKey}
              currentDir={sortDir}
              onSort={handleSort}
            />
          </tr>
        </thead>
        <tbody>
          {sortedTrades.map((t, i) => (
            <TradeRow key={`${t.timestamp}-${i}`} trade={t} index={i} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
