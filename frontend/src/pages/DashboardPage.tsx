import { useState } from "react";
import EquityChart from "../components/dashboard/EquityChart";
import PaperTradingMetrics from "../components/dashboard/PaperTradingMetrics";
import PositionsGrid from "../components/dashboard/PositionsGrid";
import StatsWidgets from "../components/dashboard/StatsWidgets";
import TradeHistory from "../components/dashboard/TradeHistory";
import { useAuth } from "../contexts/AuthContext";
import { useDashboard } from "../hooks/useDashboard";

type Period = "1h" | "6h" | "12h" | "24h" | "7d" | "30d" | "all";

const PERIODS: { label: string; value: Period }[] = [
  { label: "1H", value: "1h" },
  { label: "6H", value: "6h" },
  { label: "12H", value: "12h" },
  { label: "24H", value: "24h" },
  { label: "7D", value: "7d" },
  { label: "30D", value: "30d" },
  { label: "ALL", value: "all" },
];

export default function DashboardPage() {
  const { user, logout } = useAuth();
  const [period, setPeriod] = useState<Period>("24h");
  const { data, loading, error, refresh } = useDashboard(period);

  // Debug: Log the state
  console.log(
    "DashboardPage - data:",
    data,
    "loading:",
    loading,
    "error:",
    error,
  );

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-red-600 mb-4">Error</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={refresh}
            className="px-4 py-2 bg-blue-600 text-white rounded-sm hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600">No data available</p>
          <button
            onClick={refresh}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-sm hover:bg-blue-700"
          >
            Refresh
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold">0xBot Dashboard</h1>
          <div className="flex items-center space-x-4">
            <div className="flex gap-2">
              {PERIODS.map((p) => (
                <button
                  key={p.value}
                  onClick={() => setPeriod(p.value)}
                  className={`px-3 py-1 text-sm font-semibold rounded-sm transition ${
                    period === p.value
                      ? "bg-blue-600 text-white"
                      : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
            <button
              onClick={refresh}
              disabled={loading}
              className="px-3 py-2 text-sm bg-gray-200 hover:bg-gray-300 rounded-sm disabled:opacity-50"
            >
              {loading ? "Refreshing..." : "Refresh"}
            </button>
            <span className="text-gray-600">{user?.email}</span>
            <button
              onClick={logout}
              className="px-4 py-2 text-sm text-red-600 hover:text-red-700"
            >
              Logout
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">
        {/* Paper Trading Metrics - Validation Panel */}
        <div className="bg-white rounded-sm p-6 shadow border-l-4 border-blue-500">
          <PaperTradingMetrics
            bot={data?.bot ?? null}
            trades={data?.trade_history ?? []}
          />
        </div>

        {/* Equity Chart */}
        <div className="bg-white rounded-sm p-6 shadow">
          <h2 className="text-xl font-bold mb-4">Equity Curve</h2>
          <div className="h-96">
            <EquityChart
              snapshots={data?.equity_snapshots ?? []}
              trades={data?.trade_history ?? []}
              initialCapital={data?.bot?.initial_capital ?? 10000}
            />
          </div>
        </div>

        {/* Stats Widgets */}
        {data && (
          <div className="bg-white rounded-sm p-6 shadow">
            <h2 className="text-xl font-bold mb-4">Statistics</h2>
            <StatsWidgets
              bot={data.bot ?? null}
              sentiment={null}
              totalReturnPct={data.total_return_pct ?? 0}
              hodlReturnPct={data.hodl_return_pct ?? 0}
              alphaPct={data.alpha_pct ?? 0}
              btcCurrentPrice={data.btc_current_price ?? 0}
            />
          </div>
        )}

        {/* Open Positions */}
        <div className="bg-white rounded-sm p-6 shadow">
          <h2 className="text-xl font-bold mb-4">Open Positions</h2>
          <PositionsGrid positions={data?.positions ?? []} />
        </div>

        {/* Trade History */}
        <div
          className="bg-white rounded-sm p-6 shadow"
          style={{ marginLeft: "45px" }}
        >
          <h2 className="text-xl font-bold mb-4">Trade History</h2>
          <TradeHistory trades={data?.trade_history ?? []} />
        </div>
      </div>
    </div>
  );
}
