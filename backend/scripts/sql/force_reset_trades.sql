-- Force reset daily trade counter for ALL bots (not just active ones)
-- This will delete all entry trades from today

-- First, let's see current status
SELECT 
    b.id,
    b.name,
    b.status,
    COUNT(t.id) FILTER (WHERE t.realized_pnl = 0) as entry_trades_today,
    COUNT(t.id) FILTER (WHERE t.realized_pnl != 0) as exit_trades_today,
    COUNT(t.id) as total_trades_today
FROM bots b
LEFT JOIN trades t ON t.bot_id = b.id 
    AND t.executed_at >= CURRENT_DATE
GROUP BY b.id, b.name, b.status;

-- Now delete all entry trades from today (realized_pnl = 0)
DELETE FROM trades 
WHERE executed_at >= CURRENT_DATE
  AND realized_pnl = 0;

-- Verify the reset
SELECT 
    b.id,
    b.name,
    b.status,
    COUNT(t.id) FILTER (WHERE t.realized_pnl = 0) as entry_trades_today,
    COUNT(t.id) as total_trades_today
FROM bots b
LEFT JOIN trades t ON t.bot_id = b.id 
    AND t.executed_at >= CURRENT_DATE
GROUP BY b.id, b.name, b.status;