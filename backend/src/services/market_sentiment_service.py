"""Market Sentiment Service - Aggregates sentiment from alternative.me and CoinGecko APIs."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

# Shared timeout for all API requests
API_TIMEOUT = aiohttp.ClientTimeout(total=5)


class MarketPhase(Enum):
    """Market phase classification based on Fear & Greed Index."""

    EXTREME_FEAR = "EXTREME_FEAR"
    FEAR = "FEAR"
    NEUTRAL = "NEUTRAL"
    GREED = "GREED"
    EXTREME_GREED = "EXTREME_GREED"


@dataclass
class FearGreedData:
    """Fear & Greed Index data."""

    value: int
    label: str
    yesterday_value: Optional[int]
    last_week_value: Optional[int]
    trend: str
    timestamp: datetime


@dataclass
class GlobalMarketData:
    """Global crypto market data from CoinGecko."""

    total_market_cap_usd: float
    market_cap_change_24h: float
    btc_dominance: float
    eth_dominance: float
    total_volume_24h: float
    active_cryptocurrencies: int
    trending_coins: list[str]


@dataclass
class MarketSentiment:
    """Complete market sentiment analysis."""

    fear_greed: FearGreedData
    global_market: GlobalMarketData
    market_phase: MarketPhase
    llm_guidance: str
    fetched_at: datetime


class MarketSentimentService:
    """Service to fetch and aggregate market sentiment from free APIs."""

    FEAR_GREED_URL = "https://api.alternative.me/fng/"
    COINGECKO_GLOBAL_URL = "https://api.coingecko.com/api/v3/global"
    COINGECKO_TRENDING_URL = "https://api.coingecko.com/api/v3/search/trending"

    def __init__(self, cache_ttl: int = 300):
        """Initialize with cache TTL in seconds (default: 5 minutes)."""
        self.cache_ttl = cache_ttl
        self._last_fetch: Optional[datetime] = None
        self._cached_sentiment: Optional[MarketSentiment] = None

    async def get_market_sentiment(self) -> Optional[MarketSentiment]:
        """Get comprehensive market sentiment. Returns cached data if still valid."""
        if self._cached_sentiment and self._last_fetch:
            if (datetime.utcnow() - self._last_fetch).total_seconds() < self.cache_ttl:
                return self._cached_sentiment

        try:
            results = await asyncio.gather(
                self._fetch_fear_greed(),
                self._fetch_global_market(),
                self._fetch_trending(),
                return_exceptions=True,
            )

            fear_greed = results[0] if not isinstance(results[0], Exception) else self._get_default_fear_greed()
            global_market = results[1] if not isinstance(results[1], Exception) else self._get_default_global_market()
            trending = results[2] if not isinstance(results[2], Exception) else []

            if isinstance(results[0], Exception):
                logger.warning(f"Failed to fetch Fear & Greed: {results[0]}")
            if isinstance(results[1], Exception):
                logger.warning(f"Failed to fetch global market: {results[1]}")

            # Ensure global_market and fear_greed are correct types before using them
            if not isinstance(global_market, GlobalMarketData):
                global_market = self._get_default_global_market()
            if not isinstance(fear_greed, FearGreedData):
                fear_greed = self._get_default_fear_greed()

            global_market.trending_coins = trending if isinstance(trending, list) else []
            market_phase = self._determine_market_phase(fear_greed.value)
            llm_guidance = self._generate_llm_guidance(fear_greed, global_market, market_phase)

            self._cached_sentiment = MarketSentiment(
                fear_greed=fear_greed,
                global_market=global_market,
                market_phase=market_phase,
                llm_guidance=llm_guidance,
                fetched_at=datetime.utcnow(),
            )
            self._last_fetch = datetime.utcnow()

            logger.info(
                f"Market Sentiment: F&G={fear_greed.value} ({fear_greed.label}), "
                f"BTC Dom={global_market.btc_dominance:.1f}%, Phase={market_phase.value}"
            )
            return self._cached_sentiment

        except Exception as e:
            logger.error(f"Error fetching market sentiment: {e}")
            return self._cached_sentiment

    async def _fetch_fear_greed(self) -> FearGreedData:
        """Fetch Fear & Greed Index from alternative.me."""
        async with aiohttp.ClientSession(timeout=API_TIMEOUT) as session:
            async with session.get(self.FEAR_GREED_URL, params={"limit": 7}) as response:
                if response.status != 200:
                    raise Exception(f"Fear & Greed API returned {response.status}")

                data = await response.json()
                if "data" not in data or not data["data"]:
                    raise Exception("Invalid Fear & Greed response")

                entries = data["data"]
                current = entries[0]
                current_value = int(current["value"])
                yesterday_value = int(entries[1]["value"]) if len(entries) > 1 else None
                last_week_value = int(entries[6]["value"]) if len(entries) > 6 else None

                trend = "unknown"
                if yesterday_value:
                    diff = current_value - yesterday_value
                    if diff > 5:
                        trend = "increasing"
                    elif diff < -5:
                        trend = "decreasing"
                    else:
                        trend = "stable"

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
        async with aiohttp.ClientSession(timeout=API_TIMEOUT) as session:
            async with session.get(self.COINGECKO_GLOBAL_URL) as response:
                if response.status != 200:
                    raise Exception(f"CoinGecko API returned {response.status}")

                data = await response.json()
                if "data" not in data:
                    raise Exception("Invalid CoinGecko response")

                gd = data["data"]
                return GlobalMarketData(
                    total_market_cap_usd=gd.get("total_market_cap", {}).get("usd", 0),
                    market_cap_change_24h=gd.get("market_cap_change_percentage_24h_usd", 0),
                    btc_dominance=gd.get("market_cap_percentage", {}).get("btc", 0),
                    eth_dominance=gd.get("market_cap_percentage", {}).get("eth", 0),
                    total_volume_24h=gd.get("total_volume", {}).get("usd", 0),
                    active_cryptocurrencies=gd.get("active_cryptocurrencies", 0),
                    trending_coins=[],
                )

    async def _fetch_trending(self) -> list[str]:
        """Fetch trending coins from CoinGecko."""
        async with aiohttp.ClientSession(timeout=API_TIMEOUT) as session:
            async with session.get(self.COINGECKO_TRENDING_URL) as response:
                if response.status != 200:
                    return []
                data = await response.json()
                return [
                    coin.get("item", {}).get("symbol", "").upper()
                    for coin in data.get("coins", [])[:5]
                    if coin.get("item", {}).get("symbol")
                ]

    def _determine_market_phase(self, fg_value: int) -> MarketPhase:
        """Determine market phase from Fear & Greed value."""
        if fg_value < 20:
            return MarketPhase.EXTREME_FEAR
        if fg_value < 40:
            return MarketPhase.FEAR
        if fg_value < 60:
            return MarketPhase.NEUTRAL
        if fg_value < 80:
            return MarketPhase.GREED
        return MarketPhase.EXTREME_GREED

    def _generate_llm_guidance(
        self, fear_greed: FearGreedData, global_market: GlobalMarketData, market_phase: MarketPhase
    ) -> str:
        """Generate actionable guidance for the LLM based on sentiment."""
        guidance_parts = []

        # Phase-based guidance
        phase_guidance = {
            MarketPhase.EXTREME_FEAR: "EXTREME FEAR - Good buying opportunity. Look for high-conviction LONG entries.",
            MarketPhase.FEAR: "FEAR - Be selective. Wait for clear setups with good R:R.",
            MarketPhase.NEUTRAL: "NEUTRAL - Trade based on technicals. No directional bias from sentiment.",
            MarketPhase.GREED: "GREED - Market may be overextended. Favor taking profits.",
            MarketPhase.EXTREME_GREED: "EXTREME GREED - High correction probability. Avoid aggressive longs.",
        }
        guidance_parts.append(phase_guidance[market_phase])

        # BTC Dominance
        btc_dom = global_market.btc_dominance
        if btc_dom > 55:
            guidance_parts.append(f"BTC Dom HIGH ({btc_dom:.1f}%) - Favor BTC over alts")
        elif btc_dom < 45:
            guidance_parts.append(f"BTC Dom LOW ({btc_dom:.1f}%) - Alt season potential")

        # Market cap trend
        mcap_change = global_market.market_cap_change_24h
        if mcap_change > 3:
            guidance_parts.append(f"Strong inflows (+{mcap_change:.1f}% 24h) - Bullish momentum")
        elif mcap_change < -3:
            guidance_parts.append(f"Capital outflows ({mcap_change:.1f}% 24h) - Risk-off mode")

        # Meme coin activity (risk-on indicator)
        meme_coins = {"PEPE", "DOGE", "SHIB", "WIF", "BONK", "FLOKI", "MEME"}
        trending_memes = [c for c in global_market.trending_coins if c in meme_coins]
        if len(trending_memes) >= 2:
            guidance_parts.append(f"Meme coins trending ({', '.join(trending_memes)}) - Retail speculating")

        return " | ".join(guidance_parts)

    def _get_default_fear_greed(self) -> FearGreedData:
        """Return default Fear & Greed data when API fails."""
        return FearGreedData(
            value=50, label="Neutral", yesterday_value=None,
            last_week_value=None, trend="unknown", timestamp=datetime.utcnow()
        )

    def _get_default_global_market(self) -> GlobalMarketData:
        """Return default global market data when API fails."""
        return GlobalMarketData(
            total_market_cap_usd=0, market_cap_change_24h=0, btc_dominance=50,
            eth_dominance=15, total_volume_24h=0, active_cryptocurrencies=0, trending_coins=[]
        )

    def format_for_prompt(self, sentiment: Optional[MarketSentiment] = None) -> str:
        """Format sentiment data for inclusion in LLM prompt."""
        sentiment = sentiment or self._cached_sentiment
        if sentiment is None:
            return "## 0. MARKET SENTIMENT CONTEXT\n\n*Sentiment data unavailable*\n"

        fg = sentiment.fear_greed
        gm = sentiment.global_market

        trend_arrows = {"increasing": "^", "decreasing": "v", "stable": "-"}
        trend_arrow = trend_arrows.get(fg.trend, "-")

        history_parts = []
        if fg.yesterday_value is not None:
            history_parts.append(f"Yesterday: {fg.yesterday_value}")
        if fg.last_week_value is not None:
            history_parts.append(f"Last Week: {fg.last_week_value}")
        history_str = f" ({', '.join(history_parts)})" if history_parts else ""

        mcap_str = (f"${gm.total_market_cap_usd / 1e12:.2f}T" if gm.total_market_cap_usd >= 1e12
                    else f"${gm.total_market_cap_usd / 1e9:.0f}B")

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

        lines.extend(["", "### LLM Guidance", sentiment.llm_guidance, ""])
        return "\n".join(lines)


_sentiment_service: Optional[MarketSentimentService] = None


def get_sentiment_service() -> MarketSentimentService:
    """Get or create the singleton MarketSentimentService instance."""
    global _sentiment_service
    if _sentiment_service is None:
        _sentiment_service = MarketSentimentService()
    return _sentiment_service
