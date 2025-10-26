-- Mettre à jour le capital du bot à 10000$
-- Exécuter avec: sqlite3 backend/database.db < backend/scripts/sql/update_bot_capital.sql

-- Afficher l'état actuel
SELECT '📊 État AVANT modification:' as status;
SELECT 
    id, 
    name, 
    status, 
    model_name, 
    initial_capital as "Capital Initial",
    capital as "Capital Actuel",
    (capital - initial_capital) as "PnL"
FROM bots;

-- Mettre à jour le capital et initial_capital à 10000$
UPDATE bots 
SET 
    capital = 10000.00,
    initial_capital = 10000.00
WHERE status = 'active';

-- Afficher l'état après
SELECT '✅ État APRÈS modification:' as status;
SELECT 
    id, 
    name, 
    status, 
    model_name, 
    initial_capital as "Capital Initial",
    capital as "Capital Actuel",
    (capital - initial_capital) as "PnL"
FROM bots;

