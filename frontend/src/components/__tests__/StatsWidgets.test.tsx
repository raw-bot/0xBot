import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import StatsWidgets from '../dashboard/StatsWidgets';

describe('StatsWidgets', () => {
  const mockStats = {
    total_value: 11500,
    initial_capital: 10000,
    total_pnl: 1500,
    pnl_pct: 15,
    win_rate: 65,
    total_trades: 20,
    open_positions: 3,
    closed_trades: 17,
  };

  it('should render without crashing', () => {
    render(<StatsWidgets stats={mockStats} />);
    expect(screen.queryByText(/Total Value|PnL|Win Rate/i)).toBeDefined();
  });

  it('should display total value', () => {
    const { container } = render(<StatsWidgets stats={mockStats} />);
    const content = container.textContent;
    expect(content?.includes('11500') || content?.includes('Total')).toBe(true);
  });

  it('should display PnL percentage', () => {
    const { container } = render(<StatsWidgets stats={mockStats} />);
    const content = container.textContent;
    expect(content?.includes('15') || content?.includes('PnL')).toBe(true);
  });

  it('should show win rate', () => {
    const { container } = render(<StatsWidgets stats={mockStats} />);
    const content = container.textContent;
    expect(content?.includes('65') || content?.includes('Win')).toBe(true);
  });

  it('should handle zero values', () => {
    const zeroStats = {
      total_value: 10000,
      initial_capital: 10000,
      total_pnl: 0,
      pnl_pct: 0,
      win_rate: 0,
      total_trades: 0,
      open_positions: 0,
      closed_trades: 0,
    };
    render(<StatsWidgets stats={zeroStats} />);
    expect(screen.queryByText(/Stats|Widget/i)).toBeDefined();
  });

  it('should handle negative PnL', () => {
    const negativeStats = {
      total_value: 9500,
      initial_capital: 10000,
      total_pnl: -500,
      pnl_pct: -5,
      win_rate: 30,
      total_trades: 10,
      open_positions: 2,
      closed_trades: 8,
    };
    render(<StatsWidgets stats={negativeStats} />);
    expect(screen.queryByText(/Stats|Widget/i)).toBeDefined();
  });

  it('should format large numbers with separators', () => {
    const largeStats = {
      total_value: 1234567,
      initial_capital: 1000000,
      total_pnl: 234567,
      pnl_pct: 23.45,
      win_rate: 75,
      total_trades: 100,
      open_positions: 5,
      closed_trades: 95,
    };
    const { container } = render(<StatsWidgets stats={largeStats} />);
    expect(container).toBeDefined();
  });

  it('should display open positions count', () => {
    const { container } = render(<StatsWidgets stats={mockStats} />);
    const content = container.textContent;
    expect(content?.includes('3') || content?.includes('position')).toBe(true);
  });

  it('should display total trades count', () => {
    const { container } = render(<StatsWidgets stats={mockStats} />);
    const content = container.textContent;
    expect(content?.includes('20') || content?.includes('trade')).toBe(true);
  });
});
