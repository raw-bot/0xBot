-- 🔄 RESET BOT POUR TESTS
-- Ce script réinitialise le bot avec capital à $10,000 et compteur de trades à 0
-- Exécuter avec: sqlite3 backend/database.db < backend/scripts/sql/reset_bot_for_testing.sql

BEGIN TRANSACTION;

-- 📊 État AVANT modification
SELECT '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' as '';
SELECT '📊 ÉTAT AVANT MODIFICATION' as '';
SELECT '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' as '';
SELECT '';

-- Afficher état du bot
SELECT 
    '🤖 Bot:' as '',
    name as "Nom",
    status as "Statut",
    printf('$%,.2f', initial_capital) as "Capital Initial",
    printf('$%,.2f', capital) as "Capital Actuel",
    printf('$%,.2f', capital - initial_capital) as "PnL"
FROM bots
WHERE status = 'active';

SELECT '';

-- Afficher trades aujourd'hui
SELECT 
    '📈 Trades aujourd''hui:' as '',
    COUNT(*) FILTER (WHERE realized_pnl = 0) as "Entrées",
    COUNT(*) FILTER (WHERE realized_pnl != 0) as "Sorties",
    COUNT(*) as "Total"
FROM trades
WHERE executed_at >= date('now', 'start of day');

SELECT '';
SELECT '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' as '';
SELECT '';

-- 🔄 RÉINITIALISATION
SELECT '🔄 Réinitialisation en cours...' as '';
SELECT '';

-- 1. Mettre le capital à $10,000
UPDATE bots 
SET 
    capital = 10000.00,
    initial_capital = 10000.00,
    total_pnl = 0.00
WHERE status = 'active';

SELECT '✅ Capital réinitialisé à $10,000.00' as '';

-- 2. Supprimer tous les trades d'aujourd'hui (reset compteur)
DELETE FROM trades 
WHERE executed_at >= date('now', 'start of day');

SELECT '✅ Compteur de trades réinitialisé' as '';

-- 3. Fermer toutes les positions ouvertes (optionnel mais recommandé)
UPDATE positions
SET status = 'closed',
    closed_at = datetime('now')
WHERE status = 'open';

SELECT '✅ Toutes les positions fermées' as '';

SELECT '';
SELECT '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' as '';

-- ✅ État APRÈS modification
SELECT '';
SELECT '✅ ÉTAT APRÈS MODIFICATION' as '';
SELECT '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' as '';
SELECT '';

-- Afficher état du bot
SELECT 
    '🤖 Bot:' as '',
    name as "Nom",
    status as "Statut",
    printf('$%,.2f', initial_capital) as "Capital Initial",
    printf('$%,.2f', capital) as "Capital Actuel",
    printf('$%,.2f', capital - initial_capital) as "PnL"
FROM bots
WHERE status = 'active';

SELECT '';

-- Afficher trades aujourd'hui
SELECT 
    '📈 Trades aujourd''hui:' as '',
    COUNT(*) FILTER (WHERE realized_pnl = 0) as "Entrées",
    COUNT(*) FILTER (WHERE realized_pnl != 0) as "Sorties",
    COUNT(*) as "Total"
FROM trades
WHERE executed_at >= date('now', 'start of day');

SELECT '';

-- Afficher positions ouvertes
SELECT 
    '📍 Positions ouvertes:' as '',
    COUNT(*) as "Nombre"
FROM positions
WHERE status = 'open';

SELECT '';
SELECT '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' as '';
SELECT '🎉 Réinitialisation terminée ! Le bot est prêt pour les tests.' as '';
SELECT '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' as '';

COMMIT;

