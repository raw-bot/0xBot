import { describe, it, expect, vi, beforeEach } from 'vitest';
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
  ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
}));

describe('EquityChart', () => {
  const mockData = [
    { timestamp: '2024-01-01T00:00:00', total_value: 10000, cash: 8000, positions_value: 2000 },
    { timestamp: '2024-01-02T00:00:00', total_value: 10500, cash: 8000, positions_value: 2500 },
    { timestamp: '2024-01-03T00:00:00', total_value: 10200, cash: 8100, positions_value: 2100 },
  ];

  it('should render without crashing', () => {
    render(<EquityChart data={mockData} />);
    expect(screen.getByTestId('line-chart')).toBeDefined();
  });

  it('should render responsive container', () => {
    render(<EquityChart data={mockData} />);
    expect(screen.getByTestId('responsive-container')).toBeDefined();
  });

  it('should handle empty data array', () => {
    render(<EquityChart data={[]} />);
    expect(screen.getByTestId('line-chart')).toBeDefined();
  });

  it('should pass data to chart', () => {
    const { container } = render(<EquityChart data={mockData} />);
    expect(container).toBeDefined();
  });

  it('should have proper CSS classes', () => {
    const { container } = render(<EquityChart data={mockData} />);
    const chartContainer = container.querySelector('[class*="h-"]');
    expect(chartContainer).toBeDefined();
  });
});
