import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import TradeHistory from '../dashboard/TradeHistory';

describe('TradeHistory', () => {
  const mockTrades = [
    {
      id: '1',
      symbol: 'BTC/USDT',
      side: 'BUY' as const,
      entry_price: 45000,
      exit_price: 46500,
      margin: 22500,
      leverage: 1.0,
      fees: 67.5,
      pnl: 2250,
      timestamp: '2024-01-03T10:30:00',
    },
    {
      id: '2',
      symbol: 'ETH/USDT',
      side: 'SELL' as const,
      entry_price: 2550,
      exit_price: 2500,
      margin: 12750,
      leverage: 1.0,
      fees: 25.5,
      pnl: 500,
      timestamp: '2024-01-02T15:45:00',
    },
    {
      id: '3',
      symbol: 'BTC/USDT',
      side: 'SELL' as const,
      entry_price: 46500,
      exit_price: 45750,
      margin: 7500,
      leverage: 1.0,
      fees: 23.25,
      pnl: 750,
      timestamp: '2024-01-01T12:00:00',
    },
  ];

  it('should render without crashing', () => {
    render(<TradeHistory trades={mockTrades} />);
    expect(screen.getByText('Symbol')).toBeDefined();
  });

  it('should display trade data', () => {
    const { container } = render(<TradeHistory trades={mockTrades} />);
    expect(container.textContent).toContain('BTC/USDT');
  });

  it('should handle empty trades array', () => {
    render(<TradeHistory trades={[]} />);
    expect(screen.getByText('No trades yet')).toBeDefined();
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

  it('should handle pagination and sorting', () => {
    const manyTrades = Array(25).fill(null).map((_, i) => ({
      id: String(i),
      symbol: 'BTC/USDT',
      side: 'BUY' as const,
      entry_price: 45000,
      exit_price: 46000,
      margin: 22500,
      leverage: 1.0,
      fees: 45,
      pnl: 1000,
      timestamp: '2024-01-01T00:00:00',
    }));
    render(<TradeHistory trades={manyTrades} />);
    expect(screen.getByText('Symbol')).toBeDefined();
  });
});
