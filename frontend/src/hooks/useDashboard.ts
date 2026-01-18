/**
 * React hook for fetching dashboard data
 */
import { useCallback, useEffect, useState } from 'react';
import type { DashboardData, Period, SentimentData } from '../types/dashboard';

const API_BASE = '/api';

export function useDashboard(period: Period = '24h') {
  const [data, setData] = useState<DashboardData | null>(null);
  const [sentiment, setSentiment] = useState<SentimentData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [dashboardRes, sentimentRes] = await Promise.all([
        fetch(`${API_BASE}/dashboard?period=${period}`),
        fetch(`${API_BASE}/dashboard/sentiment`),
      ]);

      if (!dashboardRes.ok) {
        throw new Error(`Dashboard API error: ${dashboardRes.status}`);
      }

      const dashboardData: DashboardData = await dashboardRes.json();
      setData(dashboardData);

      if (sentimentRes.ok) {
        const sentimentData: SentimentData = await sentimentRes.json();
        setSentiment(sentimentData);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    data,
    sentiment,
    loading,
    error,
    refresh: fetchData,
  };
}
