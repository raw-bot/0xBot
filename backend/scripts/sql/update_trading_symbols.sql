-- Script pour mettre à jour les symboles de trading d'un bot
-- Usage: docker exec -i trading_agent_postgres psql -U postgres -d trading_agent < backend/scripts/sql/update_trading_symbols.sql

-- Afficher la configuration actuelle
SELECT 
    id, 
    name, 
    trading_symbols as "Symboles Actuels"
FROM bots
WHERE status = 'active';

-- Mettre à jour les symboles (décommenter et modifier selon vos besoins)

-- Option 1: Top 10 Cryptos (Diversifié)
-- UPDATE bots 
-- SET trading_symbols = '["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT", "AVAX/USDT", "MATIC/USDT", "DOT/USDT", "LINK/USDT"]'::jsonb
-- WHERE status = 'active';

-- Option 2: Large Caps uniquement (Conservateur)
-- UPDATE bots 
-- SET trading_symbols = '["BTC/USDT", "ETH/USDT", "BNB/USDT"]'::jsonb
-- WHERE status = 'active';

-- Option 3: Altcoins (Agressif)
-- UPDATE bots 
-- SET trading_symbols = '["SOL/USDT", "AVAX/USDT", "MATIC/USDT", "DOT/USDT", "LINK/USDT", "UNI/USDT", "ATOM/USDT", "FTM/USDT", "ALGO/USDT", "NEAR/USDT"]'::jsonb
-- WHERE status = 'active';

-- Option 4: Top 20 Cryptos (Maximum diversification)
-- UPDATE bots 
-- SET trading_symbols = '["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT", "AVAX/USDT", "MATIC/USDT", "DOT/USDT", "LINK/USDT", "UNI/USDT", "ATOM/USDT", "FTM/USDT", "ALGO/USDT", "NEAR/USDT", "APT/USDT", "ARB/USDT", "OP/USDT", "SUI/USDT", "INJ/USDT"]'::jsonb
-- WHERE status = 'active';

-- Afficher la nouvelle configuration
SELECT 
    id, 
    name, 
    trading_symbols as "Nouveaux Symboles",
    jsonb_array_length(trading_symbols) as "Nombre de Symboles"
FROM bots
WHERE status = 'active';

-- Information
SELECT '✅ Symboles mis à jour. Relancez le bot avec ./dev.sh' as "Résultat";

