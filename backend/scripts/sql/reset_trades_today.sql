-- Reset daily trade counter
-- This script can be used to clean up incorrectly counted trades
-- Run this to recalculate trade counts with the new logic (only ENTRY trades)

-- WARNING: This will DELETE all trades from today with realized_pnl != 0 (exits)
-- This is useful after fixing the trade counting bug

BEGIN;

-- Option 1: Delete all EXIT trades from today (they shouldn't be counted)
-- Uncomment this if you want to clean up:
-- DELETE FROM trades 
-- WHERE executed_at >= CURRENT_DATE
--   AND realized_pnl != 0;

-- Option 2: Just view the current count
SELECT 
    bot_id,
    COUNT(*) as total_trades,
    COUNT(*) FILTER (WHERE realized_pnl = 0) as entry_trades,
    COUNT(*) FILTER (WHERE realized_pnl != 0) as exit_trades
FROM trades
WHERE executed_at >= CURRENT_DATE
GROUP BY bot_id;

-- To reset for a specific bot, use:
-- DELETE FROM trades 
-- WHERE bot_id = 'your-bot-id-here'
--   AND executed_at >= CURRENT_DATE
--   AND realized_pnl != 0;

COMMIT;