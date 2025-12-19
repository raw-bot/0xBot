-- Configuration des Top 5 Cryptos pour le bot actif
-- Usage: docker exec -i trading_agent_postgres psql -U postgres -d trading_agent < backend/scripts/sql/set_top5_cryptos.sql

-- Afficher la configuration actuelle
SELECT 
    '📊 CONFIGURATION ACTUELLE' as "═══════════════════════════════════════════════";

SELECT 
    name as "Bot",
    trading_symbols as "Symboles"
FROM bots
WHERE status = 'active';

-- Mettre à jour avec les Top 5 cryptos
UPDATE bots 
SET trading_symbols = '[
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "BNB/USDT",
    "XRP/USDT"
]'::jsonb
WHERE status = 'active';

-- Afficher la nouvelle configuration
SELECT 
    '✅ NOUVELLE CONFIGURATION' as "═══════════════════════════════════════════════";

SELECT 
    name as "Bot",
    trading_symbols as "Symboles",
    jsonb_array_length(trading_symbols) as "Nombre"
FROM bots
WHERE status = 'active';

-- Détails
SELECT 
    '💡 INFO' as "═══════════════════════════════════════════════";

SELECT 
    '✅ Configuration mise à jour avec succès!' as "Résultat",
    'Relancez le bot avec ./dev.sh pour appliquer' as "Action";

-- Liste des cryptos
SELECT 
    '📋 CRYPTOS CONFIGURÉES' as "═══════════════════════════════════════════════";

SELECT 
    1 as "#",
    'BTC/USDT' as "Symbole",
    'Bitcoin' as "Nom"
UNION ALL
SELECT 2, 'ETH/USDT', 'Ethereum'
UNION ALL
SELECT 3, 'SOL/USDT', 'Solana'
UNION ALL
SELECT 4, 'BNB/USDT', 'Binance Coin'
UNION ALL
SELECT 5, 'XRP/USDT', 'Ripple';

