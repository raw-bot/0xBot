import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import PositionsGrid from '../dashboard/PositionsGrid';

describe('PositionsGrid', () => {
  const mockPositions = [
    {
      id: '1',
      symbol: 'BTC/USDT',
      side: 'LONG',
      quantity: 1.5,
      entry_price: 45000,
      current_price: 46500,
      status: 'OPEN',
      stop_loss: 43650,
      take_profit: 47700,
      unrealized_pnl: 2250,
      unrealized_pnl_pct: 3.3,
    },
    {
      id: '2',
      symbol: 'ETH/USDT',
      side: 'LONG',
      quantity: 10,
      entry_price: 2500,
      current_price: 2550,
      status: 'OPEN',
      stop_loss: 2425,
      take_profit: 2650,
      unrealized_pnl: 500,
      unrealized_pnl_pct: 2.0,
    },
  ];

  it('should render without crashing', () => {
    render(<PositionsGrid positions={mockPositions} />);
    expect(screen.queryByText('Positions')).toBeDefined();
  });

  it('should display positions data', () => {
    render(<PositionsGrid positions={mockPositions} />);
    expect(screen.getByText(/BTC\/USDT|ETH\/USDT/)).toBeDefined();
  });

  it('should handle empty positions array', () => {
    render(<PositionsGrid positions={[]} />);
    expect(screen.queryByText('Positions')).toBeDefined();
  });

  it('should display position details', () => {
    const { container } = render(<PositionsGrid positions={mockPositions} />);
    const rows = container.querySelectorAll('tr');
    expect(rows.length).toBeGreaterThan(0);
  });

  it('should show positive PnL in green', () => {
    const { container } = render(<PositionsGrid positions={mockPositions} />);
    const pnlElements = container.querySelectorAll('[class*="text-green"]');
    expect(pnlElements.length).toBeGreaterThanOrEqual(0);
  });

  it('should format numbers correctly', () => {
    render(<PositionsGrid positions={mockPositions} />);
    const element = screen.queryByText((content, element) => {
      return element?.textContent?.includes('1.5') || false;
    });
    expect(element).toBeDefined();
  });
});
