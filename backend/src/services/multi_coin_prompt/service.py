"""
MultiCoinPromptService Facade - Coordinates prompt generation modules.
"""

from datetime import datetime
from typing import Any, Optional

from ..alpha_setup_generator import AlphaSetupGenerator
from ..fvg_detector_service import get_fvg_detector
from ..market_sentiment_service import MarketSentiment, get_sentiment_service
from ..narrative_analyzer import NarrativeAnalyzer
from ..pain_trade_analyzer import PainTradeAnalyzer
from .analysis_integrator import AnalysisIntegrator
from .market_formatter import MarketDataFormatter
from .prompt_builder import PromptBuilder


class MultiCoinPromptService:
    """Generates 0xBot-style multi-coin trading prompts with comprehensive analysis."""

    COIN_MAPPING = {
        "BTC/USDT": "Bitcoin",
        "ETH/USDT": "Ethereum",
        "SOL/USDT": "Solana",
        "BNB/USDT": "BNB",
        "XRP/USDT": "XRP",
    }

    def __init__(self, db: Any = None) -> None:
        """Initialize MultiCoinPromptService with all dependency modules."""
        self.db = db
        self.narrative_analyzer = NarrativeAnalyzer()  # type: ignore[no-untyped-call]
        self.pain_trade_analyzer = PainTradeAnalyzer()  # type: ignore[no-untyped-call]
        self.alpha_setup_generator = AlphaSetupGenerator()  # type: ignore[no-untyped-call]
        self.sentiment_service = get_sentiment_service()
        self.fvg_detector = get_fvg_detector()
        self.coin_mapping = self.COIN_MAPPING

        # Initialize new modular components
        self.prompt_builder = PromptBuilder()  # type: ignore[no-untyped-call]
        self.market_formatter = MarketDataFormatter()  # type: ignore[no-untyped-call]
        self.analysis_integrator = AnalysisIntegrator()

    def get_simple_decision(
        self, bot: Any, symbol: str, market_snapshot: Any, market_regime: Any, all_coins_data: Any, bot_positions: Any = None
    ) -> dict[str, Any]:
        """Compatibility wrapper for SimpleLLMPromptService interface."""
        all_coins_data = all_coins_data if isinstance(all_coins_data, dict) else {}
        prompt_data = self.get_multi_coin_decision(
            bot=bot, all_coins_data=all_coins_data, all_positions=bot_positions or []
        )
        return {
            "prompt": prompt_data["prompt"],
            "symbol": symbol,
            "timestamp": prompt_data.get("timestamp", ""),
        }

    def get_multi_coin_decision(
        self,
        bot: Any,
        all_coins_data: dict[str, dict[str, Any]],
        all_positions: list[Any],
        news_data: Optional[list[dict[str, Any]]] = None,
        portfolio_state: Optional[dict[str, Any]] = None,
        sentiment_data: Optional[MarketSentiment] = None,
    ) -> dict[str, Any]:
        """Generate comprehensive multi-coin prompt with all analysis sections."""
        all_positions = all_positions or []
        news_data = news_data or []
        symbols = list(all_coins_data.keys()) if all_coins_data else list(self.coin_mapping.keys())

        # Extract position symbols
        position_symbols = self.analysis_integrator.extract_position_symbols(all_positions)

        # Prepare price data for narrative analysis
        price_data = self.analysis_integrator.prepare_price_data(all_coins_data)

        # Analyze news vs reality
        analyzed_news = self.narrative_analyzer.analyze_news_vs_reality(
            news_items=news_data, price_data=price_data, symbols=symbols
        )

        # Perform analyses for each symbol
        squeeze_analyses, crowded_trades, alpha_setups = {}, {}, {}

        for symbol in symbols:
            if symbol not in all_coins_data:
                continue

            market_data = all_coins_data[symbol]
            news_for_symbol = analyzed_news.get(symbol, [])
            narrative_class = news_for_symbol[0].get("classification", "NEUTRAL") if news_for_symbol else "NEUTRAL"

            squeeze_analyses[symbol] = self._analyze_squeeze(symbol, market_data)
            crowded_trades[symbol] = self.pain_trade_analyzer.detect_crowded_trades(
                symbol=symbol,
                funding_rate=market_data.get("funding_rate", 0),
                price_change_24h=self._calc_price_change(market_data, "24h"),
                narrative_sentiment=self._get_primary_sentiment(news_for_symbol),
                volume_ratio=self._calc_volume_ratio(market_data),
            )
            alpha_setups[symbol] = self._generate_alpha_setup(symbol, market_data, narrative_class)

        # Get sentiment
        sentiment = sentiment_data or self.sentiment_service._cached_sentiment

        # Format analysis sections
        market_data_formatted = self.market_formatter.format_market_data(symbols, all_coins_data)
        news_analysis = self.narrative_analyzer.format_for_prompt(analyzed_news)
        pain_trades_analysis = self.pain_trade_analyzer.format_for_prompt(squeeze_analyses, crowded_trades)
        alpha_setups_analysis = self.alpha_setup_generator.format_for_prompt(alpha_setups)
        fvg_analysis = self.market_formatter.format_fvg_analysis(symbols, all_coins_data)
        positions_text = self.market_formatter.format_positions(all_positions)

        # Build complete prompt
        prompt = self.prompt_builder.build_prompt(
            symbols=symbols,
            market_data_formatted=market_data_formatted,
            news_analysis=news_analysis,
            pain_trades_analysis=pain_trades_analysis,
            alpha_setups_analysis=alpha_setups_analysis,
            fvg_analysis=fvg_analysis,
            portfolio_state=portfolio_state,
            positions_text=positions_text,
            sentiment=sentiment,
        )

        return {
            "prompt": prompt,
            "timestamp": datetime.utcnow().isoformat(),
            "symbols_count": len(symbols),
            "positions_count": len(all_positions),
            "has_news": len(news_data) > 0,
            "squeeze_detected": any(
                s.squeeze_type.value != "NO_SQUEEZE" for s in squeeze_analyses.values()
            ),
        }

    def _get_price_at_offset(self, market_data: dict[str, Any], offset: int) -> float:
        """Get price from series at offset candles back, or current price if unavailable."""
        current = market_data.get("current_price", 0)
        price_series = market_data.get("price_series", [])
        if len(price_series) > offset:
            val = price_series[-offset]
            if isinstance(val, (int, float)):
                return float(val)
        return float(current)

    def _get_price_range(self, market_data: dict[str, Any], lookback: int) -> tuple[float, float]:
        """Get (high, low) from recent price series."""
        current = market_data.get("current_price", 0)
        price_series = market_data.get("price_series", [])
        recent = price_series[-lookback:] if len(price_series) > lookback else price_series
        if not recent:
            return current, current
        return max(recent), min(recent)

    def _calc_price_change(self, market_data: dict[str, Any], period: str) -> float:
        """Calculate price change for a period."""
        current = market_data.get("current_price", 0)
        offsets = {"1h": 12, "4h": 48, "24h": 288}
        offset = offsets.get(period, 0)
        old_price = self._get_price_at_offset(market_data, offset) if offset else market_data.get("price_series", [current])[0]
        return ((current - old_price) / old_price * 100) if old_price > 0 else 0

    def _calc_volume_ratio(self, market_data: dict[str, Any]) -> float:
        """Calculate current volume vs average."""
        tech = market_data.get("technical_indicators", {}).get("1h", {})
        avg_vol = tech.get("avg_volume", 1)
        return tech.get("volume", 0) / avg_vol if avg_vol > 0 else 1.0

    def _get_primary_sentiment(self, news_list: list[dict[str, Any]]) -> str:
        """Get primary sentiment from news list."""
        return news_list[0].get("sentiment", "neutral") if news_list else "neutral"

    def _analyze_squeeze(self, symbol: str, market_data: dict[str, Any]) -> Any:
        """Analyze squeeze potential for a symbol."""
        current = market_data.get("current_price", 0)
        high_4h, low_4h = self._get_price_range(market_data, 48)
        oi_data = market_data.get("open_interest", {})

        return self.pain_trade_analyzer.analyze_squeeze_potential(
            symbol=symbol,
            funding_rate=market_data.get("funding_rate", 0),
            open_interest=oi_data.get("latest", 0),
            avg_open_interest=oi_data.get("average", 1),
            current_price=current,
            price_1h_ago=self._get_price_at_offset(market_data, 12),
            price_4h_ago=self._get_price_at_offset(market_data, 48),
            high_4h=high_4h,
            low_4h=low_4h,
        )

    def _generate_alpha_setup(
        self, symbol: str, market_data: dict[str, Any], narrative_class: str
    ) -> Any:
        """Generate alpha setup for a symbol."""
        current = market_data.get("current_price", 0)
        price_series = market_data.get("price_series", [])
        high_4h, low_4h = self._get_price_range(market_data, 48)
        high_24h = max(price_series) if price_series else current
        low_24h = min(price_series) if price_series else current
        tech_1h = market_data.get("technical_indicators", {}).get("1h", {})
        oi_data = market_data.get("open_interest", {})

        return self.alpha_setup_generator.generate_setup(
            symbol=symbol,
            current_price=current,
            price_1h_ago=self._get_price_at_offset(market_data, 12),
            price_4h_ago=self._get_price_at_offset(market_data, 48),
            price_24h_ago=price_series[0] if price_series else current,
            high_4h=high_4h,
            low_4h=low_4h,
            high_24h=high_24h,
            low_24h=low_24h,
            rsi_14=tech_1h.get("rsi14", 50),
            ema_20=tech_1h.get("ema20", current),
            ema_50=tech_1h.get("ema50", current),
            funding_rate=market_data.get("funding_rate", 0),
            open_interest=oi_data.get("latest", 0),
            avg_open_interest=oi_data.get("average", 1),
            volume_ratio=self._calc_volume_ratio(market_data),
            narrative_classification=narrative_class,
        )

    def parse_multi_coin_response(
        self, response_text: str, target_symbols: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """Parse LLM response for multi-coin decisions."""
        target_symbols = target_symbols or list(self.coin_mapping.keys())
        return self.analysis_integrator.parse_multi_coin_response(response_text, target_symbols)

    def get_decision_for_symbol(self, symbol: str, response_text: str) -> dict[str, Any]:
        """Extract decision for a specific symbol from LLM response."""
        return self.analysis_integrator.get_decision_for_symbol(symbol, response_text)

    def parse_simple_response(self, response_text: str, symbol: str, current_market_price: float = 0) -> dict[str, Any]:
        """Compatibility method for SimpleLLMPromptService interface."""
        return self.analysis_integrator.parse_simple_response(response_text, symbol, current_market_price)
