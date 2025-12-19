-- Mettre à jour le quota de trades pour le bot de test

UPDATE bots 
SET risk_params = jsonb_set(
    risk_params, 
    '{max_trades_per_day}', 
    '50'
)
WHERE id = 'ed640bbf-289b-4352-ab1c-c0d8039d8e29';

-- Vérifier la mise à jour
SELECT id, name, risk_params->>'max_trades_per_day' as max_trades_per_day
FROM bots
WHERE id = 'ed640bbf-289b-4352-ab1c-c0d8039d8e29';