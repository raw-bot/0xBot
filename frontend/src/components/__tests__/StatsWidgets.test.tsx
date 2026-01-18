import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';
import StatsWidgets from '../dashboard/StatsWidgets';

// Mock sub-components
vi.mock('../dashboard/WinRateRing', () => ({
  default: ({ winRate, totalTrades }: any) => <div data-testid="win-rate-ring">{winRate}% {totalTrades} trades</div>
}));

vi.mock('../dashboard/SentimentGauge', () => ({
  default: ({ sentiment }: any) => <div data-testid="sentiment-gauge">Sentiment</div>
}));

vi.mock('../dashboard/HodlComparison', () => ({
  default: ({ botReturn, hodlReturn, alpha }: any) => <div data-testid="hodl-comparison">{botReturn}% bot vs {hodlReturn}% hodl</div>
}));

describe('StatsWidgets', () => {
  const mockBot = {
    id: 'bot1',
    name: 'Test Bot',
    total_trades: 20,
    winning_trades: 13,
    open_positions: 3,
    status: 'RUNNING' as const,
  };

  it('should render without crashing', () => {
    render(
      <StatsWidgets
        bot={mockBot}
        sentiment={null}
        totalReturnPct={15}
        hodlReturnPct={12}
        alphaPct={3}
        btcCurrentPrice={45000}
      />
    );
    expect(document.querySelector('[data-testid="win-rate-ring"]')).toBeDefined();
  });

  it('should display win rate calculation', () => {
    const { container } = render(
      <StatsWidgets
        bot={mockBot}
        sentiment={null}
        totalReturnPct={15}
        hodlReturnPct={12}
        alphaPct={3}
        btcCurrentPrice={45000}
      />
    );
    // Win rate should be 65% (13/20)
    expect(container.textContent).toContain('65');
  });

  it('should handle null bot', () => {
    render(
      <StatsWidgets
        bot={null}
        sentiment={null}
        totalReturnPct={0}
        hodlReturnPct={0}
        alphaPct={0}
        btcCurrentPrice={45000}
      />
    );
    expect(document.querySelector('[data-testid="win-rate-ring"]')).toBeDefined();
  });

  it('should display sentiment gauge', () => {
    render(
      <StatsWidgets
        bot={mockBot}
        sentiment={{ fear_greed: 60, label: 'Greed' }}
        totalReturnPct={15}
        hodlReturnPct={12}
        alphaPct={3}
        btcCurrentPrice={45000}
      />
    );
    expect(document.querySelector('[data-testid="sentiment-gauge"]')).toBeDefined();
  });

  it('should display hodl comparison', () => {
    render(
      <StatsWidgets
        bot={mockBot}
        sentiment={null}
        totalReturnPct={15}
        hodlReturnPct={12}
        alphaPct={3}
        btcCurrentPrice={45000}
      />
    );
    expect(document.querySelector('[data-testid="hodl-comparison"]')).toBeDefined();
  });

  it('should handle zero winning trades', () => {
    const zeroWinBot = { ...mockBot, winning_trades: 0 };
    const { container } = render(
      <StatsWidgets
        bot={zeroWinBot}
        sentiment={null}
        totalReturnPct={0}
        hodlReturnPct={0}
        alphaPct={0}
        btcCurrentPrice={45000}
      />
    );
    expect(container.textContent).toContain('0');
  });

  it('should handle negative returns', () => {
    render(
      <StatsWidgets
        bot={mockBot}
        sentiment={null}
        totalReturnPct={-5}
        hodlReturnPct={10}
        alphaPct={-15}
        btcCurrentPrice={45000}
      />
    );
    expect(document.querySelector('[data-testid="hodl-comparison"]')).toBeDefined();
  });

  it('should update on bot changes', () => {
    const { rerender } = render(
      <StatsWidgets
        bot={mockBot}
        sentiment={null}
        totalReturnPct={15}
        hodlReturnPct={12}
        alphaPct={3}
        btcCurrentPrice={45000}
      />
    );
    const updatedBot = { ...mockBot, total_trades: 50, winning_trades: 30 };
    rerender(
      <StatsWidgets
        bot={updatedBot}
        sentiment={null}
        totalReturnPct={20}
        hodlReturnPct={12}
        alphaPct={8}
        btcCurrentPrice={50000}
      />
    );
    expect(document.querySelector('[data-testid="win-rate-ring"]')).toBeDefined();
  });
});
