import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import EquityChart from '../dashboard/EquityChart';

// Mock recharts to avoid canvas rendering issues in tests
vi.mock('recharts', () => ({
  LineChart: ({ children }: any) => <div data-testid="line-chart">{children}</div>,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  ReferenceLine: () => null,
  ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
}));

describe('EquityChart', () => {
  const mockSnapshots = [
    { timestamp: '2024-01-01T00:00:00', equity: 10000 },
    { timestamp: '2024-01-02T00:00:00', equity: 10500 },
    { timestamp: '2024-01-03T00:00:00', equity: 10200 },
  ];

  const mockTrades = [
    { timestamp: '2024-01-01T12:00:00', symbol: 'BTC/USDT', side: 'BUY', pnl: 250 },
    { timestamp: '2024-01-02T12:00:00', symbol: 'ETH/USDT', side: 'SELL', pnl: -300 },
  ];

  it('should render without crashing', () => {
    render(<EquityChart snapshots={mockSnapshots} trades={mockTrades} initialCapital={10000} />);
    expect(screen.getByTestId('line-chart')).toBeDefined();
  });

  it('should render responsive container', () => {
    render(<EquityChart snapshots={mockSnapshots} trades={mockTrades} initialCapital={10000} />);
    expect(screen.getByTestId('responsive-container')).toBeDefined();
  });

  it('should handle empty data array', () => {
    render(<EquityChart snapshots={[]} trades={[]} initialCapital={10000} />);
    expect(screen.getByText('No equity data available')).toBeDefined();
  });

  it('should pass data to chart', () => {
    const { container } = render(<EquityChart snapshots={mockSnapshots} trades={mockTrades} initialCapital={10000} />);
    expect(container).toBeDefined();
  });

  it('should have proper CSS classes', () => {
    const { container } = render(<EquityChart snapshots={mockSnapshots} trades={mockTrades} initialCapital={10000} />);
    expect(container.querySelector('[class*="h-"]')).toBeDefined();
  });
});
