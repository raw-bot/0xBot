"""Trading memory service - learns from trade history."""

from decimal import Decimal
from typing import Any, Dict, List, Optional
from datetime import datetime
from uuid import UUID

from ..core.logger import get_logger
from ..core.memory.memory_manager import MemoryManager

logger = get_logger(__name__)


def get_trading_memory(db=None, bot_id=None):
    """Factory function to create TradingMemoryService instance.

    Args:
        db: Database session (not used currently, for compatibility)
        bot_id: Bot UUID

    Returns:
        TradingMemoryService instance
    """
    return TradingMemoryService(bot_id=bot_id)


class TradingMemoryService:
    """Service to memorize and recall trading patterns and profitable setups."""

    def __init__(self, bot_id: UUID):
        self.bot_id = bot_id
        self.memory = MemoryManager.get_provider()

    async def remember_profitable_setup(
        self,
        symbol: str,
        entry_pattern: Dict,
        pnl: Decimal,
        confidence: Decimal,
    ) -> bool:
        """Remember a profitable trading setup.

        Args:
            symbol: Trading pair (BTC, ETH, etc)
            entry_pattern: Pattern that led to profit (indicators, RSI, etc)
            pnl: Profit/loss amount
            confidence: Confidence level of the setup

        Returns:
            True if remembered
        """
        try:
            key = f"profitable_setup:{symbol}:{datetime.utcnow().isoformat()}"

            data = {
                "symbol": symbol,
                "pattern": entry_pattern,
                "pnl": float(pnl),
                "confidence": float(confidence),
                "timestamp": datetime.utcnow().isoformat(),
            }

            success = await MemoryManager.remember(
                key,
                data,
                metadata={"symbol": symbol, "profitable": pnl > 0},
            )

            if success:
                logger.info(f"[MEMORY] Remembered profitable setup for {symbol}: ${float(pnl):.2f}")

            return success

        except Exception as e:
            logger.error(f"[MEMORY] Error remembering setup: {e}")
            return False

    async def remember_losing_setup(
        self,
        symbol: str,
        entry_pattern: Dict,
        pnl: Decimal,
    ) -> bool:
        """Remember a losing trading setup to avoid it.

        Args:
            symbol: Trading pair
            entry_pattern: Pattern that led to loss
            pnl: Loss amount

        Returns:
            True if remembered
        """
        try:
            key = f"losing_setup:{symbol}:{datetime.utcnow().isoformat()}"

            data = {
                "symbol": symbol,
                "pattern": entry_pattern,
                "pnl": float(pnl),
                "timestamp": datetime.utcnow().isoformat(),
            }

            success = await MemoryManager.remember(
                key,
                data,
                metadata={"symbol": symbol, "avoid": True},
            )

            if success:
                logger.warning(f"[MEMORY] Remembered losing setup for {symbol}: ${float(pnl):.2f}")

            return success

        except Exception as e:
            logger.error(f"[MEMORY] Error remembering loss: {e}")
            return False

    async def remember_symbol_stats(self, symbol: str, stats: Dict) -> bool:
        """Remember aggregate stats for a symbol.

        Args:
            symbol: Trading pair
            stats: Win rate, avg profit, etc

        Returns:
            True if remembered
        """
        try:
            key = f"symbol_stats:{symbol}"

            success = await MemoryManager.remember(key, stats, metadata={"symbol": symbol})

            if success:
                logger.info(
                    f"[MEMORY] Updated stats for {symbol}: "
                    f"WR={stats.get('win_rate', 0):.1f}%, "
                    f"Profit=${stats.get('avg_profit', 0):.2f}"
                )

            return success

        except Exception as e:
            logger.error(f"[MEMORY] Error remembering stats: {e}")
            return False

    async def recall_symbol_stats(self, symbol: str) -> Optional[Dict]:
        """Recall stats for a symbol.

        Returns:
            Stats dict or None if not found
        """
        try:
            key = f"symbol_stats:{symbol}"
            stats = await MemoryManager.recall(key)

            if stats:
                logger.info(f"[MEMORY] Recalled stats for {symbol}")

            return stats

        except Exception as e:
            logger.error(f"[MEMORY] Error recalling stats: {e}")
            return None

    async def get_best_performing_setups(self, symbol: str, limit: int = 5) -> List[Dict]:
        """Get best performing setups for a symbol.

        Returns:
            List of profitable setup patterns
        """
        try:
            logger.debug(f"[MEMORY] Getting best setups for {symbol}")
            return []

        except Exception as e:
            logger.error(f"[MEMORY] Error getting best setups: {e}")
            return []

    async def get_avoiding_patterns(self, symbol: str) -> List[Dict]:
        """Get patterns to avoid for a symbol.

        Returns:
            List of losing patterns
        """
        try:
            logger.debug(f"[MEMORY] Getting patterns to avoid for {symbol}")
            return []

        except Exception as e:
            logger.error(f"[MEMORY] Error getting avoiding patterns: {e}")
            return []

    async def suggest_confidence_adjustment(self, symbol: str) -> float:
        """Suggest confidence adjustment based on memory.

        Returns:
            Adjustment factor (1.0 = no change, 0.8 = reduce confidence by 20%)
        """
        try:
            stats = await self.recall_symbol_stats(symbol)

            if not stats:
                return 1.0

            win_rate = stats.get("win_rate", 0.5)

            # Check highest win rates FIRST (most specific conditions first)
            if win_rate > 0.70:
                adjustment = 1.3  # High win rate - big confidence boost
                logger.info(f"[MEMORY] {symbol} very profitable (WR {win_rate*100:.0f}%) - boosting confidence by 30%")
            elif win_rate > 0.65:
                adjustment = 1.15  # Good win rate - moderate boost
                logger.info(f"[MEMORY] {symbol} profitable (WR {win_rate*100:.0f}%) - boosting confidence by 15%")
            elif win_rate < 0.45:
                adjustment = 0.7  # Low win rate - significant reduction
                logger.info(f"[MEMORY] {symbol} unprofitable (WR {win_rate*100:.0f}%) - reducing confidence by 30%")
            elif win_rate < 0.50:
                adjustment = 0.85  # Moderate low - slight reduction
            else:
                adjustment = 1.0  # Normal range - no adjustment

            return adjustment

        except Exception as e:
            logger.error(f"[MEMORY] Error suggesting confidence adjustment: {e}")
            return 1.0
