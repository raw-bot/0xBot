"""Test d'intégration pour le cycle de trading complet."""

import pytest
import asyncio
from decimal import Decimal
from unittest.mock import Mock, patch

from src.services.trading_engine_service import TradingEngine
from src.services.multi_coin_prompt_service import MultiCoinPromptService


class TestCompleteTradingCycle:
    """Tests d'intégration pour le cycle de trading complet."""
    
    @pytest.fixture
    def mock_bot(self):
        """Bot mock pour les tests."""
        bot = Mock()
        bot.id = "test-bot-id"
        bot.name = "Test Bot"
        bot.capital = Decimal("10000")
        bot.trading_symbols = ["BTC/USDT", "ETH/USDT"]
        return bot
    
    @pytest.fixture
    def mock_db(self):
        """Database mock pour les tests."""
        return Mock()
    
    @pytest.mark.asyncio
    async def test_trading_cycle_integration(self, mock_bot, mock_db):
        """Test d'intégration du cycle de trading complet."""
        # Arrange
        engine = TradingEngine(mock_bot, mock_db)
        
        # Act - Simuler un cycle de trading
        with patch.object(engine, '_trading_cycle') as mock_cycle:
            await engine.start()
            
            # Assert
            mock_cycle.assert_called()
    
    @pytest.mark.asyncio
    async def test_multi_coin_prompt_service(self, mock_bot):
        """Test du service de prompt multi-coins."""
        # Arrange
        service = MultiCoinPromptService()
        
        # Act
        result = service.get_multi_coin_decision(
            bot=mock_bot,
            market_data={},
            positions=[]
        )
        
        # Assert
        assert result is not None
        assert "prompt" in result
