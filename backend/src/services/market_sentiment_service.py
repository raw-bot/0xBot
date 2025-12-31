"""
Market Sentiment Service - External API Integration for Enhanced LLM Decisions

Aggregates sentiment indicators from free public APIs:
1. Fear & Greed Index (alternative.me) - No API key required
2. Global Market Data (CoinGecko) - No API key required

These indicators help the LLM make better-informed trading decisions by understanding
the overall market sentiment and structure.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


class MarketPhase(Enum):
    """Market phase classification based on sentiment indicators."""

    EXTREME_FEAR = "EXTREME_FEAR"  # F&G < 20 - Capitulation, potential bottom
    FEAR = "FEAR"  # F&G 20-40 - Bearish sentiment
    NEUTRAL = "NEUTRAL"  # F&G 40-60 - No clear direction
    GREED = "GREED"  # F&G 60-80 - Bullish but caution
    EXTREME_GREED = "EXTREME_GREED"  # F&G > 80 - Overheated, potential top


@dataclass
class FearGreedData:
    """Fear & Greed Index data."""

    value: int  # 0-100
    label: str  # "Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"
    yesterday_value: Optional[int]
    last_week_value: Optional[int]
    trend: str  # "increasing", "decreasing", "stable"
    timestamp: datetime


@dataclass
class GlobalMarketData:
    """Global crypto market data from CoinGecko."""

    total_market_cap_usd: float
    market_cap_change_24h: float  # % change
    btc_dominance: float  # % of total market cap
    eth_dominance: float
    total_volume_24h: float
    active_cryptocurrencies: int
    trending_coins: List[str]  # Top trending coin symbols


@dataclass
class MarketSentiment:
    """Complete market sentiment analysis."""

    fear_greed: FearGreedData
    global_market: GlobalMarketData
    market_phase: MarketPhase
    llm_guidance: str  # Human-readable guidance for LLM
    fetched_at: datetime


class MarketSentimentService:
    """
    Service to fetch and aggregate market sentiment from external APIs.

    All APIs used are FREE and do not require API keys:
    - alternative.me Fear & Greed Index
    - CoinGecko Global Market Data

    Includes caching to respect rate limits.
    """

    FEAR_GREED_URL = "https://api.alternative.me/fng/"
    COINGECKO_GLOBAL_URL = "https://api.coingecko.com/api/v3/global"
    COINGECKO_TRENDING_URL = "https://api.coingecko.com/api/v3/search/trending"

    def __init__(self, cache_ttl: int = 300):
        """
        Initialize the service.

        Args:
            cache_ttl: Cache time-to-live in seconds (default: 5 minutes)
        """
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Dict] = {}
        self._last_fetch: Optional[datetime] = None
        self._cached_sentiment: Optional[MarketSentiment] = None

    async def get_market_sentiment(self) -> Optional[MarketSentiment]:
        """
        Get comprehensive market sentiment.

        Returns cached data if still valid, otherwise fetches fresh data.

        Returns:
            MarketSentiment object or None if fetch fails
        """
        # Check cache
        if self._cached_sentiment and self._last_fetch:
            age = (datetime.utcnow() - self._last_fetch).total_seconds()
            if age < self.cache_ttl:
                return self._cached_sentiment

        # Fetch fresh data
        try:
            # Fetch in parallel for speed
            fear_greed_task = self._fetch_fear_greed()
            global_market_task = self._fetch_global_market()
            trending_task = self._fetch_trending()

            fear_greed, global_market, trending = await asyncio.gather(
                fear_greed_task, global_market_task, trending_task, return_exceptions=True
            )

            # Handle potential exceptions
            if isinstance(fear_greed, Exception):
                logger.warning(f"Failed to fetch Fear & Greed: {fear_greed}")
                fear_greed = self._get_default_fear_greed()

            if isinstance(global_market, Exception):
                logger.warning(f"Failed to fetch global market: {global_market}")
                global_market = self._get_default_global_market()

            if isinstance(trending, Exception):
                logger.warning(f"Failed to fetch trending: {trending}")
                trending = []

            # Add trending to global market data
            global_market.trending_coins = trending

            # Determine market phase
            market_phase = self._determine_market_phase(fear_greed, global_market)

            # Generate LLM guidance
            llm_guidance = self._generate_llm_guidance(fear_greed, global_market, market_phase)

            # Create sentiment object
            sentiment = MarketSentiment(
                fear_greed=fear_greed,
                global_market=global_market,
                market_phase=market_phase,
                llm_guidance=llm_guidance,
                fetched_at=datetime.utcnow(),
            )

            # Update cache
            self._cached_sentiment = sentiment
            self._last_fetch = datetime.utcnow()

            logger.info(
                f"📊 Market Sentiment: F&G={fear_greed.value} ({fear_greed.label}), "
                f"BTC Dom={global_market.btc_dominance:.1f}%, Phase={market_phase.value}"
            )

            return sentiment

        except Exception as e:
            logger.error(f"❌ Error fetching market sentiment: {e}")
            return self._cached_sentiment  # Return stale cache if available

    async def _fetch_fear_greed(self) -> FearGreedData:
        """Fetch Fear & Greed Index from alternative.me."""
        timeout = aiohttp.ClientTimeout(total=5)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Fetch current + history (limit=7 for weekly data)
            params = {"limit": 7}
            async with session.get(self.FEAR_GREED_URL, params=params) as response:
                if response.status != 200:
                    raise Exception(f"Fear & Greed API returned {response.status}")

                data = await response.json()

                if "data" not in data or not data["data"]:
                    raise Exception("Invalid Fear & Greed response")

                entries = data["data"]
                current = entries[0]
                yesterday = entries[1] if len(entries) > 1 else None
                last_week = entries[6] if len(entries) > 6 else None

                current_value = int(current["value"])
                yesterday_value = int(yesterday["value"]) if yesterday else None
                last_week_value = int(last_week["value"]) if last_week else None

                # Determine trend
                if yesterday_value:
                    if current_value > yesterday_value + 5:
                        trend = "increasing"
                    elif current_value < yesterday_value - 5:
                        trend = "decreasing"
                    else:
                        trend = "stable"
                else:
                    trend = "unknown"

                return FearGreedData(
                    value=current_value,
                    label=current["value_classification"],
                    yesterday_value=yesterday_value,
                    last_week_value=last_week_value,
                    trend=trend,
                    timestamp=datetime.fromtimestamp(int(current["timestamp"])),
                )

    async def _fetch_global_market(self) -> GlobalMarketData:
        """Fetch global market data from CoinGecko."""
        timeout = aiohttp.ClientTimeout(total=5)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(self.COINGECKO_GLOBAL_URL) as response:
                if response.status != 200:
                    raise Exception(f"CoinGecko API returned {response.status}")

                data = await response.json()

                if "data" not in data:
                    raise Exception("Invalid CoinGecko response")

                global_data = data["data"]

                return GlobalMarketData(
                    total_market_cap_usd=global_data.get("total_market_cap", {}).get("usd", 0),
                    market_cap_change_24h=global_data.get(
                        "market_cap_change_percentage_24h_usd", 0
                    ),
                    btc_dominance=global_data.get("market_cap_percentage", {}).get("btc", 0),
                    eth_dominance=global_data.get("market_cap_percentage", {}).get("eth", 0),
                    total_volume_24h=global_data.get("total_volume", {}).get("usd", 0),
                    active_cryptocurrencies=global_data.get("active_cryptocurrencies", 0),
                    trending_coins=[],  # Will be filled by _fetch_trending
                )

    async def _fetch_trending(self) -> List[str]:
        """Fetch trending coins from CoinGecko."""
        timeout = aiohttp.ClientTimeout(total=5)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(self.COINGECKO_TRENDING_URL) as response:
                if response.status != 200:
                    return []

                data = await response.json()

                # Extract top 5 trending coin symbols
                trending = []
                for coin in data.get("coins", [])[:5]:
                    item = coin.get("item", {})
                    symbol = item.get("symbol", "").upper()
                    if symbol:
                        trending.append(symbol)

                return trending

    def _determine_market_phase(
        self, fear_greed: FearGreedData, global_market: GlobalMarketData
    ) -> MarketPhase:
        """Determine overall market phase from indicators."""
        fg_value = fear_greed.value

        if fg_value < 20:
            return MarketPhase.EXTREME_FEAR
        elif fg_value < 40:
            return MarketPhase.FEAR
        elif fg_value < 60:
            return MarketPhase.NEUTRAL
        elif fg_value < 80:
            return MarketPhase.GREED
        else:
            return MarketPhase.EXTREME_GREED

    def _generate_llm_guidance(
        self, fear_greed: FearGreedData, global_market: GlobalMarketData, market_phase: MarketPhase
    ) -> str:
        """Generate actionable guidance for the LLM based on sentiment."""
        guidance_parts = []

        # Fear & Greed guidance
        if market_phase == MarketPhase.EXTREME_FEAR:
            guidance_parts.append(
                "🟢 EXTREME FEAR detected - Historically a good buying opportunity. "
                "Look for high-conviction LONG entries with tight stops."
            )
        elif market_phase == MarketPhase.FEAR:
            guidance_parts.append(
                "🟡 FEAR in market - Be selective with entries. "
                "Wait for clear setups with good R:R."
            )
        elif market_phase == MarketPhase.NEUTRAL:
            guidance_parts.append(
                "⚪ NEUTRAL sentiment - Trade based on technicals and setups. "
                "No strong directional bias from sentiment."
            )
        elif market_phase == MarketPhase.GREED:
            guidance_parts.append(
                "🟠 GREED detected - Market may be overextended. "
                "Favor taking profits on existing longs. Be cautious with new entries."
            )
        else:  # EXTREME_GREED
            guidance_parts.append(
                "🔴 EXTREME GREED - High probability of correction. "
                "AVOID aggressive LONG entries. Consider reducing exposure or taking profits."
            )

        # BTC Dominance guidance
        if global_market.btc_dominance > 55:
            guidance_parts.append(
                f"📊 BTC Dominance HIGH ({global_market.btc_dominance:.1f}%) - "
                "Alts may underperform. Favor BTC over alts."
            )
        elif global_market.btc_dominance < 45:
            guidance_parts.append(
                f"📊 BTC Dominance LOW ({global_market.btc_dominance:.1f}%) - "
                "Alt season potential. Consider quality alts."
            )

        # Market cap trend
        if global_market.market_cap_change_24h > 3:
            guidance_parts.append(
                f"📈 Strong inflows (+{global_market.market_cap_change_24h:.1f}% MCap 24h) - "
                "Momentum is bullish."
            )
        elif global_market.market_cap_change_24h < -3:
            guidance_parts.append(
                f"📉 Capital outflows ({global_market.market_cap_change_24h:.1f}% MCap 24h) - "
                "Risk-off mode. Be defensive."
            )

        # Trending coins (meme coins = risk-on)
        meme_coins = {"PEPE", "DOGE", "SHIB", "WIF", "BONK", "FLOKI", "MEME"}
        trending_memes = [c for c in global_market.trending_coins if c in meme_coins]
        if len(trending_memes) >= 2:
            guidance_parts.append(
                f"🎰 Meme coins trending ({', '.join(trending_memes)}) - "
                "Risk-on mode active. Retail is speculating."
            )

        return " | ".join(guidance_parts)

    def _get_default_fear_greed(self) -> FearGreedData:
        """Return default Fear & Greed data when API fails."""
        return FearGreedData(
            value=50,
            label="Neutral",
            yesterday_value=None,
            last_week_value=None,
            trend="unknown",
            timestamp=datetime.utcnow(),
        )

    def _get_default_global_market(self) -> GlobalMarketData:
        """Return default global market data when API fails."""
        return GlobalMarketData(
            total_market_cap_usd=0,
            market_cap_change_24h=0,
            btc_dominance=50,
            eth_dominance=15,
            total_volume_24h=0,
            active_cryptocurrencies=0,
            trending_coins=[],
        )

    def format_for_prompt(self, sentiment: Optional[MarketSentiment] = None) -> str:
        """
        Format sentiment data for inclusion in LLM prompt.

        Args:
            sentiment: MarketSentiment object (uses cached if None)

        Returns:
            Formatted string for prompt
        """
        if sentiment is None:
            sentiment = self._cached_sentiment

        if sentiment is None:
            return "## 0. MARKET SENTIMENT CONTEXT\n\n*Sentiment data unavailable*\n"

        fg = sentiment.fear_greed
        gm = sentiment.global_market

        # Trend arrow
        if fg.trend == "increasing":
            trend_arrow = "⬆️"
        elif fg.trend == "decreasing":
            trend_arrow = "⬇️"
        else:
            trend_arrow = "➡️"

        # Historical comparison
        history_str = ""
        if fg.yesterday_value is not None:
            history_str += f" (Yesterday: {fg.yesterday_value}"
            if fg.last_week_value is not None:
                history_str += f", Last Week: {fg.last_week_value}"
            history_str += ")"

        # Format market cap in trillions/billions
        if gm.total_market_cap_usd >= 1e12:
            mcap_str = f"${gm.total_market_cap_usd / 1e12:.2f}T"
        else:
            mcap_str = f"${gm.total_market_cap_usd / 1e9:.0f}B"

        lines = [
            "## 0. MARKET SENTIMENT CONTEXT",
            "",
            "### Fear & Greed Index",
            f"- **Current**: {fg.value} ({fg.label}) {trend_arrow}{history_str}",
            f"- **Market Phase**: {sentiment.market_phase.value.replace('_', ' ')}",
            "",
            "### Global Market Structure",
            f"- **Total Market Cap**: {mcap_str} ({gm.market_cap_change_24h:+.1f}% 24h)",
            f"- **BTC Dominance**: {gm.btc_dominance:.1f}% | **ETH Dominance**: {gm.eth_dominance:.1f}%",
        ]

        if gm.trending_coins:
            lines.append(f"- **Trending**: {', '.join(gm.trending_coins[:5])}")

        lines.extend(["", "### 🎯 LLM Guidance", sentiment.llm_guidance, ""])

        return "\n".join(lines)


# Singleton instance for easy access
_sentiment_service: Optional[MarketSentimentService] = None


def get_sentiment_service() -> MarketSentimentService:
    """Get or create the singleton MarketSentimentService instance."""
    global _sentiment_service
    if _sentiment_service is None:
        _sentiment_service = MarketSentimentService()
    return _sentiment_service
