export interface DashboardBot {
  id: string;
  name: string;
  status: string;
  capital: number;
  initial_capital: number;
  total_trades: number;
  winning_trades: number;
}

export interface DashboardPosition {
  symbol: string;
  side: string;
  quantity: number;
  entry_price: number;
  current_price: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  leverage: number;
}

export interface EquitySnapshot {
  timestamp: string;
  equity: number;
}

export interface TradeHistoryItem {
  timestamp: string;
  symbol: string;
  side: string;
  pnl: number;
  cumulative_pnl: number;
  entry_price: number;
  exit_price: number;
  quantity: number;
  size: number;
  margin: number;
  leverage: number;
  fees: number;
}

export interface DashboardData {
  bot: DashboardBot | null;
  positions: DashboardPosition[];
  equity_snapshots: EquitySnapshot[];
  trade_history: TradeHistoryItem[];
  current_equity: number;
  total_return_pct: number;
  total_unrealized_pnl: number;
  btc_start_price: number;
  btc_current_price: number;
  hodl_return_pct: number;
  alpha_pct: number;
}

export interface SentimentData {
  available: boolean;
  error?: string;
  fear_greed?: {
    value: number;
    label: string;
    yesterday: number;
    last_week: number;
    trend: string;
  };
  global_market?: {
    total_market_cap: number;
    market_cap_change_24h: number;
    btc_dominance: number;
    eth_dominance: number;
    trending_coins: string[];
  };
  market_phase?: string;
  llm_guidance?: string;
  timestamp?: string;
}

export type Period = '1h' | '6h' | '12h' | '24h' | '7d' | '30d' | 'all';
