"""Service de mémoire de trading pour enrichir le contexte LLM"""
from datetime import datetime, timedelta
from typing import Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging

from ..models.bot import Bot
from ..models.trade import Trade
from ..models.position import Position
from ..models.llm_decision import LLMDecision

logger = logging.getLogger(__name__)


class TradingMemoryService:
    """
    Service qui maintient le contexte de session de trading
    Fournit des données enrichies pour les prompts LLM
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._session_start = datetime.now()
        self._invocation_count = 0
        
    def increment_invocation(self):
        """Incrémenter le compteur d'invocations LLM"""
        self._invocation_count += 1
        
    def get_session_context(self, bot: Bot) -> Dict:
        """
        Contexte de la session en cours
        - Durée de la session
        - Nombre d'invocations LLM
        - Timestamp actuel
        """
        session_minutes = int((datetime.now() - self._session_start).total_seconds() / 60)
        return {
            "session_minutes": session_minutes,
            "total_invocations": self._invocation_count,
            "current_time": datetime.now().isoformat()
        }
    
    def get_portfolio_context(self, bot: Bot, open_positions: List = None) -> Dict:
        """
        Contexte du portfolio
        - Capital initial vs actuel
        - Cash disponible
        - Capital investi
        - Performance (PnL, return %)
        
        Args:
            bot: Bot instance
            open_positions: List of open positions (passed to avoid async query issues)
        """
        # Calculate invested capital from open positions
        if open_positions is None:
            open_positions = []
        
        invested = sum(
            float(pos.entry_price * pos.quantity)
            for pos in open_positions
            if pos.status == "open"
        )
        
        # Available cash = total capital - invested in positions
        current_capital = float(bot.capital)
        available_cash = current_capital - invested
        
        # Calculate percentages
        return_pct = ((current_capital - float(bot.initial_capital)) / float(bot.initial_capital)) * 100
        cash_pct = (available_cash / current_capital) * 100 if current_capital > 0 else 0
        invested_pct = (invested / current_capital) * 100 if current_capital > 0 else 0
        
        return {
            "initial_capital": float(bot.initial_capital),
            "current_equity": current_capital,
            "available_cash": available_cash,
            "cash_pct": cash_pct,
            "invested": invested,
            "invested_pct": invested_pct,
            "return_pct": return_pct,
            "pnl": current_capital - float(bot.initial_capital)
        }
    
    def get_positions_context(self, bot: Bot, open_positions: List = None) -> List[Dict]:
        """
        Contexte des positions ouvertes
        - Détails de chaque position
        - PnL par position
        - Stop loss / Take profit
        
        Args:
            bot: Bot instance
            open_positions: List of open positions (passed to avoid async query issues)
        """
        if open_positions is None:
            open_positions = []
        
        # Filter only open positions
        open_positions = [pos for pos in open_positions if pos.status == "open"]
        
        positions_data = []
        for position in open_positions:
            
            # Calculate PnL
            if position.side == "long":
                pnl = (position.current_price - position.entry_price) * position.quantity
            else:
                pnl = (position.entry_price - position.current_price) * position.quantity
            
            pnl_pct = (pnl / (position.entry_price * position.quantity)) * 100 if position.quantity > 0 else 0
            
            positions_data.append({
                "symbol": position.symbol,
                "side": position.side.upper(),
                "size": float(position.quantity),  # Use quantity, display as size
                "entry_price": float(position.entry_price),
                "current_price": float(position.current_price),
                "pnl": float(pnl),
                "pnl_pct": float(pnl_pct),
                "stop_loss": float(position.stop_loss) if position.stop_loss else None,
                "take_profit": float(position.take_profit) if position.take_profit else None,
                "notional_usd": float(position.entry_price * position.quantity)
            })
        
        return positions_data
    
    def get_trades_today_context(self, bot: Bot) -> Dict:
        """
        Contexte des trades du jour
        - Nombre de trades exécutés
        - Win rate
        - Meilleur/pire trade
        
        Note: Simplified version to avoid async DB queries
        TODO: Pass trades as parameter like positions
        """
        # For now, return default values to avoid async DB issues
        # The bot has risk_params with max_trades_per_day
        return {
            "trades_today": 0,  # TODO: Pass from trading engine
            "max_trades_per_day": bot.risk_params.get("max_trades_per_day", 10),
            "win_rate": 0.0,  # TODO: Calculate from passed trades
            "total_closed_trades": 0,
            "winning_trades": 0,
            "best_trade": None,
            "worst_trade": None
        }
    
    def get_sharpe_ratio(self, bot: Bot, period_days: int = 7) -> float:
        """
        Calculer le Sharpe Ratio sur une période donnée
        Mesure le ratio rendement/risque
        
        Note: Simplified version to avoid async DB queries
        TODO: Calculate from passed trades data
        """
        # For now, return 0.0 to avoid async DB issues
        # TODO: Pass trades data and calculate properly
        return 0.0
    
    def get_full_context(self, bot: Bot, open_positions: List = None) -> Dict:
        """
        Obtenir le contexte complet pour enrichir les prompts LLM
        Appelé à chaque décision de trading
        
        Args:
            bot: Bot instance
            open_positions: List of open positions (passed to avoid async query issues)
        """
        self.increment_invocation()
        
        return {
            "session": self.get_session_context(bot),
            "portfolio": self.get_portfolio_context(bot, open_positions),
            "positions": self.get_positions_context(bot, open_positions),
            "trades_today": self.get_trades_today_context(bot),
            "sharpe_ratio": self.get_sharpe_ratio(bot)
        }


# Global instances cache (one per bot)
_memory_instances: Dict[str, TradingMemoryService] = {}


def get_trading_memory(db: Session, bot_id: str) -> TradingMemoryService:
    """
    Factory function pour obtenir l'instance de TradingMemoryService pour un bot
    Maintient une instance par bot pour conserver l'état de session
    """
    if bot_id not in _memory_instances:
        _memory_instances[bot_id] = TradingMemoryService(db)
    return _memory_instances[bot_id]

