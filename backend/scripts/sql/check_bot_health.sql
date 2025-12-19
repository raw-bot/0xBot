-- Script de diagnostic: Vérifier la cohérence du capital et des positions
-- À exécuter pour vérifier que tout est correct

\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo '🏦 ÉTAT DES BOTS ET POSITIONS'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo ''

-- 1. Vue d'ensemble des bots
\echo '📊 Vue d''ensemble des bots:'
SELECT 
    id,
    name,
    initial_capital as "Capital Initial",
    capital as "Capital Actuel",
    capital - initial_capital as "PnL",
    ROUND(((capital - initial_capital) / initial_capital * 100)::numeric, 2) as "Return %",
    status
FROM bots
ORDER BY created_at DESC;

\echo ''
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo ''

-- 2. Positions ouvertes par bot
\echo '📍 Positions ouvertes:'
SELECT 
    b.name as "Bot",
    p.symbol as "Symbole",
    p.side as "Direction",
    p.quantity as "Quantité",
    p.entry_price as "Prix Entrée",
    p.current_price as "Prix Actuel",
    (p.current_price * p.quantity) as "Valeur Position",
    CASE 
        WHEN p.side = 'long' THEN (p.current_price - p.entry_price) * p.quantity
        ELSE (p.entry_price - p.current_price) * p.quantity
    END as "PnL Non Réalisé",
    p.opened_at as "Ouvert Le"
FROM positions p
JOIN bots b ON p.bot_id = b.id
WHERE p.status = 'open'
ORDER BY p.opened_at DESC;

\echo ''
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo ''

-- 3. Derniers trades
\echo '💱 Derniers trades (5 plus récents):'
SELECT 
    b.name as "Bot",
    t.symbol as "Symbole",
    t.side as "Type",
    t.quantity as "Quantité",
    t.price as "Prix",
    t.realized_pnl as "PnL Réalisé",
    t.executed_at as "Exécuté Le"
FROM trades t
JOIN bots b ON t.bot_id = b.id
ORDER BY t.executed_at DESC
LIMIT 5;

\echo ''
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo ''

-- 4. Cohérence du portfolio
\echo '🧮 Vérification de cohérence par bot:'
WITH bot_stats AS (
    SELECT 
        b.id,
        b.name,
        b.initial_capital,
        b.capital,
        COALESCE(SUM(CASE WHEN p.status = 'open' THEN p.current_price * p.quantity ELSE 0 END), 0) as positions_value,
        COALESCE(SUM(CASE WHEN p.status = 'open' THEN 
            CASE 
                WHEN p.side = 'long' THEN (p.current_price - p.entry_price) * p.quantity
                ELSE (p.entry_price - p.current_price) * p.quantity
            END
        ELSE 0 END), 0) as unrealized_pnl,
        COALESCE(SUM(t.realized_pnl), 0) as realized_pnl
    FROM bots b
    LEFT JOIN positions p ON b.id = p.bot_id
    LEFT JOIN trades t ON b.id = t.bot_id
    GROUP BY b.id, b.name, b.initial_capital, b.capital
)
SELECT 
    name as "Bot",
    initial_capital as "Capital Initial",
    capital as "Cash Disponible",
    positions_value as "En Positions",
    (capital + positions_value) as "Valeur Totale",
    realized_pnl as "PnL Réalisé",
    unrealized_pnl as "PnL Non Réalisé",
    (realized_pnl + unrealized_pnl) as "PnL Total",
    ROUND((((capital + positions_value) - initial_capital) / initial_capital * 100)::numeric, 2) as "Return %"
FROM bot_stats
ORDER BY name;

\echo ''
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo '✅ Diagnostic terminé'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'