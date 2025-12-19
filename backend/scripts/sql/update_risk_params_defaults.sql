-- OPTIONAL: Add stop loss and take profit percentages to all bots' risk_params
-- This is NOT required as the code uses fallback values (0.035 and 0.07)
-- This script is only for explicitly setting values in the database

UPDATE bots
SET risk_params = risk_params ||
    '{"stop_loss_pct": 0.035, "take_profit_pct": 0.07}'::jsonb
WHERE NOT (risk_params ? 'stop_loss_pct');

-- Verify the update
SELECT
    id,
    name,
    risk_params->>'stop_loss_pct' as stop_loss_pct,
    risk_params->>'take_profit_pct' as take_profit_pct
FROM bots;