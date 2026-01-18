import { useCallback, useEffect, useState } from 'react';
import type { DashboardData, Period, SentimentData } from '../types/dashboard.js';

const API_BASE = '/api';

interface DashboardState {
  data: DashboardData | null;
  sentiment: SentimentData | null;
  loading: boolean;
  error: string | null;
}

export function useDashboard(period: Period = '24h') {
  const [state, setState] = useState<DashboardState>({
    data: null,
    sentiment: null,
    loading: true,
    error: null,
  });

  const fetchData = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      const [dashboardRes, sentimentRes] = await Promise.all([
        fetch(`${API_BASE}/dashboard?period=${period}`),
        fetch(`${API_BASE}/dashboard/sentiment`),
      ]);

      if (!dashboardRes.ok) {
        throw new Error(`Dashboard API error: ${dashboardRes.status}`);
      }

      const data: DashboardData = await dashboardRes.json();
      const sentiment: SentimentData | null = sentimentRes.ok ? await sentimentRes.json() : null;

      setState({ data, sentiment, loading: false, error: null });
    } catch (err) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: err instanceof Error ? err.message : 'Unknown error',
      }));
    }
  }, [period]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { ...state, refresh: fetchData };
}
