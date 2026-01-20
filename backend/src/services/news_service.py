import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

from ..core.config import config

logger = logging.getLogger(__name__)


class NewsService:
    """
    Service to fetch and format news from CryptoCompare API.
    Implements caching to respect rate limits.
    """

    BASE_URL = "https://min-api.cryptocompare.com/data/v2/news/"

    def __init__(self) -> None:
        self.api_key = config.CRYPTOCOMPARE_API_KEY
        self.cache: dict[str, dict[str, Any]] = {}  # key -> {data: ..., timestamp: ...}
        self.cache_ttl = 300  # 5 minutes cache

    async def get_latest_news(self, symbols: Optional[list[str]] = None) -> list[dict[str, Any]]:
        """
        Get latest news, optionally filtered by symbols.
        Returns a simplified list of news items for the LLM.
        """
        if not self.api_key:
            logger.warning("⚠️ No CryptoCompare API key provided. News disabled.")
            return []

        try:
            # 1. Fetch News
            # CryptoCompare allows filtering by categories (e.g. BTC, ETH)
            params = {"lang": "EN"}

            if symbols:
                # Convert symbols to categories (BTC/USDT -> BTC)
                categories = [s.split("/")[0] for s in symbols]
                # Add General category to catch broad market news
                if "General" not in categories:
                    categories.append("General")
                params["categories"] = ",".join(categories)

            # Fetch from API (with caching)
            cache_key = f"news_{params.get('categories', 'all')}"
            raw_data = await self._fetch_cached(cache_key, params)

            if not raw_data or "Data" not in raw_data:
                return []

            # 2. Format for LLM
            formatted_news = self._format_news_for_llm(raw_data["Data"])
            return formatted_news[:10]  # Return top 10 most relevant

        except Exception as e:
            logger.error(f"❌ Error fetching news: {e}")
            return []

    async def _fetch_cached(self, cache_key: str, params: dict[str, Any]) -> dict[str, Any]:
        """Fetch from API with caching."""
        now = datetime.utcnow()

        # Check cache
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if (now - cached["timestamp"]).total_seconds() < self.cache_ttl:
                return cached["data"]  # type: ignore[no-any-return]

        # Fetch fresh
        data = await self._fetch_from_api(params)

        # Update cache
        if data:
            self.cache[cache_key] = {"data": data, "timestamp": now}

        return data

    async def _fetch_from_api(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute HTTP request to CryptoCompare with timeout."""
        headers = {"Authorization": f"Apikey {self.api_key}"}
        timeout = aiohttp.ClientTimeout(total=5)  # 5 second timeout

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.BASE_URL, params=params, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()  # type: ignore[no-any-return]
                    elif response.status == 429:
                        logger.warning("⚠️ CryptoCompare Rate Limit Hit")
                        return {}
                    elif response.status >= 500:
                        # Server errors - silently skip, not critical
                        logger.debug(f"CryptoCompare server error: {response.status}")
                        return {}
                    else:
                        logger.warning(f"CryptoCompare API Error: {response.status}")
                        return {}
        except asyncio.TimeoutError:
            logger.debug("CryptoCompare API timeout - skipping news")
            return {}
        except Exception as e:
            logger.debug(f"CryptoCompare connection error: {e}")
            return {}

    def _format_news_for_llm(self, raw_news: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Format raw news items into concise summaries for the LLM."""
        formatted = []
        for item in raw_news:
            try:
                # Calculate relative time (e.g. "10m ago")
                # CryptoCompare returns timestamp in seconds
                published_at = datetime.fromtimestamp(item["published_on"])
                age_minutes = int((datetime.utcnow() - published_at).total_seconds() / 60)
                time_str = f"{age_minutes}m ago" if age_minutes < 60 else f"{age_minutes//60}h ago"

                # Extract categories/currencies
                categories = item.get("categories", "").split("|")

                formatted.append(
                    {
                        "title": item["title"],
                        "source": item.get("source_info", {}).get("name", "Unknown"),
                        "time": time_str,
                        "currencies": categories,
                        "url": item["url"],
                    }
                )
            except Exception:
                continue

        return formatted
