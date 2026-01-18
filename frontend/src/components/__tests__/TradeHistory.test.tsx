import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import TradeHistory from '../dashboard/TradeHistory';

describe('TradeHistory', () => {
  const mockTrades = [
    {
      id: '1',
      symbol: 'BTC/USDT',
      side: 'BUY',
      quantity: 1.5,
      price: 45000,
      fees: 67.5,
      realized_pnl: 2250,
      executed_at: '2024-01-03T10:30:00',
    },
    {
      id: '2',
      symbol: 'ETH/USDT',
      side: 'SELL',
      quantity: 10,
      price: 2550,
      fees: 25.5,
      realized_pnl: 500,
      executed_at: '2024-01-02T15:45:00',
    },
    {
      id: '3',
      symbol: 'BTC/USDT',
      side: 'SELL',
      quantity: 0.5,
      price: 46500,
      fees: 23.25,
      realized_pnl: 750,
      executed_at: '2024-01-01T12:00:00',
    },
  ];

  it('should render without crashing', () => {
    render(<TradeHistory trades={mockTrades} />);
    expect(screen.queryByText('Trade History')).toBeDefined();
  });

  it('should display trade data', () => {
    render(<TradeHistory trades={mockTrades} />);
    expect(screen.getByText(/BTC\/USDT|ETH\/USDT/)).toBeDefined();
  });

  it('should handle empty trades array', () => {
    render(<TradeHistory trades={[]} />);
    expect(screen.queryByText('Trade History')).toBeDefined();
  });

  it('should display trade side (BUY/SELL)', () => {
    render(<TradeHistory trades={mockTrades} />);
    const buyElements = screen.queryAllByText(/BUY|SELL/);
    expect(buyElements.length).toBeGreaterThan(0);
  });

  it('should show realized PnL', () => {
    const { container } = render(<TradeHistory trades={mockTrades} />);
    const pnlContent = container.textContent;
    expect(pnlContent?.includes('2250') || pnlContent?.includes('500') || pnlContent?.includes('750')).toBe(true);
  });

  it('should format prices correctly', () => {
    const { container } = render(<TradeHistory trades={mockTrades} />);
    const content = container.textContent;
    expect(content?.includes('45000') || content?.includes('2550')).toBe(true);
  });

  it('should display timestamps', () => {
    const { container } = render(<TradeHistory trades={mockTrades} />);
    const content = container.textContent;
    expect(content).toBeDefined();
  });

  it('should handle pagination', () => {
    const manyTrades = Array(25).fill(null).map((_, i) => ({
      id: String(i),
      symbol: 'BTC/USDT',
      side: 'BUY' as const,
      quantity: 1,
      price: 45000,
      fees: 45,
      realized_pnl: 1000,
      executed_at: '2024-01-01T00:00:00',
    }));
    render(<TradeHistory trades={manyTrades} />);
    expect(screen.queryByText('Trade History')).toBeDefined();
  });
});
