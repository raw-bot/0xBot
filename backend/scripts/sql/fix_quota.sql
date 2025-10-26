-- Script simplifié pour mettre à jour le quota

UPDATE bots 
SET risk_params = '{"max_position_pct": 0.10, "max_drawdown_pct": 0.20, "max_trades_per_day": 50}'::jsonb
WHERE id = 'ed640bbf-289b-4352-ab1c-c0d8039d8e29';

-- Afficher tous les bots avec leur quota
SELECT 
    name, 
    status,
    capital,
    (risk_params->>'max_trades_per_day')::int as daily_limit
FROM bots;