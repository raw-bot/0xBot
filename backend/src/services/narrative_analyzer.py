"""
Narrative Analyzer Service - Analyze news narrative vs price reality.

Implements the NoF1-style "Narrative vs Reality Check" with time-decay classification.
Classifications: ABSORPTION, DISTRIBUTION, PRICED_IN, DIVERGENCE, IMPULSE
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class NarrativeClassification(Enum):
    """Classification of how price reacted to narrative/news."""

    ABSORPTION = "ABSORPTION"  # Negative news, price rising → Bullish
    DISTRIBUTION = "DISTRIBUTION"  # Positive news, price falling → Bearish
    PRICED_IN = "PRICED_IN"  # News > 2h old, price normalized
    DIVERGENCE = "DIVERGENCE"  # News and price moving opposite of expected
    IMPULSE = "IMPULSE"  # Fresh news with immediate price reaction
    NEUTRAL = "NEUTRAL"  # No clear classification


class NarrativeAnalyzer:
    """
    Analyze narrative vs reality with time-decay classification.

    This service takes news data and price action data, then classifies
    how the market is reacting to narratives - a key edge for trading.
    """

    # Time thresholds for news decay (in minutes)
    FRESH_NEWS_THRESHOLD = 60  # < 1 hour = fresh
    RECENT_NEWS_THRESHOLD = 120  # < 2 hours = recent
    STALE_NEWS_THRESHOLD = 360  # > 6 hours = stale

    def __init__(self):
        """Initialize the narrative analyzer."""
        pass

    def analyze_news_vs_reality(
        self, news_items: List[Dict], price_data: Dict[str, Dict], symbols: List[str]
    ) -> Dict[str, List[Dict]]:
        """
        Analyze all news items against price reality for given symbols.

        Args:
            news_items: List of news dicts with 'title', 'time', 'currencies', 'source'
            price_data: Dict mapping symbols to price info {'current_price', 'price_1h_ago', 'price_24h_ago', 'change_pct'}
            symbols: List of trading symbols to analyze

        Returns:
            Dict mapping symbols to list of analyzed news items with classifications
        """
        result = {symbol: [] for symbol in symbols}

        for news in news_items:
            try:
                # Parse news age
                age_minutes = self._parse_news_age(news.get("time", ""))

                # Determine which symbols this news affects
                affected_symbols = self._get_affected_symbols(news, symbols)

                # Determine news sentiment (positive/negative/neutral)
                sentiment = self._analyze_news_sentiment(news.get("title", ""))

                for symbol in affected_symbols:
                    if symbol not in price_data:
                        continue

                    price_info = price_data[symbol]

                    # Classify the narrative vs reality
                    classification = self._classify_narrative(
                        sentiment=sentiment,
                        age_minutes=age_minutes,
                        price_change_pct=price_info.get("change_pct", 0),
                        volume_ratio=price_info.get("volume_ratio", 1.0),
                    )

                    result[symbol].append(
                        {
                            "title": news.get("title", ""),
                            "source": news.get("source", "Unknown"),
                            "age_str": self._format_age(age_minutes),
                            "age_minutes": age_minutes,
                            "sentiment": sentiment,
                            "classification": classification.value,
                            "interpretation": self._get_interpretation(classification, sentiment),
                        }
                    )

            except Exception as e:
                logger.warning(f"Error analyzing news item: {e}")
                continue

        return result

    def _parse_news_age(self, time_str: str) -> int:
        """
        Parse news age string like '5m ago', '2h ago' to minutes.

        Args:
            time_str: Time string like "5m ago" or "2h ago"

        Returns:
            Age in minutes
        """
        if not time_str:
            return 999  # Very old if unknown

        time_str = time_str.lower().strip()

        try:
            if "m ago" in time_str:
                return int(time_str.replace("m ago", "").strip())
            elif "h ago" in time_str:
                hours = int(time_str.replace("h ago", "").strip())
                return hours * 60
            elif "d ago" in time_str:
                days = int(time_str.replace("d ago", "").strip())
                return days * 24 * 60
            else:
                return 999  # Unknown format, treat as old
        except ValueError:
            return 999

    def _format_age(self, minutes: int) -> str:
        """Format age in minutes to human-readable string."""
        if minutes < 60:
            return f"~{minutes}m ago"
        elif minutes < 1440:
            return f"~{minutes // 60}h ago"
        else:
            return f"~{minutes // 1440}d ago"

    def _get_affected_symbols(self, news: Dict, available_symbols: List[str]) -> List[str]:
        """
        Determine which trading symbols are affected by this news.

        Args:
            news: News dict with 'currencies' field
            available_symbols: List of symbols we're trading

        Returns:
            List of affected symbols
        """
        affected = []
        news_currencies = news.get("currencies", [])

        # Convert symbol to base currency (BTC/USDT -> BTC)
        symbol_to_base = {s: s.split("/")[0] for s in available_symbols}

        for symbol, base in symbol_to_base.items():
            # Check if any news currency matches
            for currency in news_currencies:
                if currency.upper() == base.upper():
                    affected.append(symbol)
                    break

            # Also check for "General" or market-wide news
            if "General" in news_currencies or "Market" in news_currencies:
                # General news affects all symbols
                if symbol not in affected:
                    affected.append(symbol)

        return affected

    def _analyze_news_sentiment(self, title: str) -> str:
        """
        Analyze sentiment of news headline (basic keyword-based).

        Args:
            title: News headline

        Returns:
            'positive', 'negative', or 'neutral'
        """
        title_lower = title.lower()

        # Positive keywords
        positive_keywords = [
            "rally",
            "surge",
            "soar",
            "jump",
            "gain",
            "bullish",
            "growth",
            "record",
            "high",
            "breakout",
            "buy",
            "accumulation",
            "adoption",
            "upgrade",
            "partnership",
            "launch",
            "approval",
            "wins",
            "success",
            "breakthrough",
            "milestone",
            "institutional",
            "etf approved",
        ]

        # Negative keywords
        negative_keywords = [
            "crash",
            "plunge",
            "drop",
            "fall",
            "bearish",
            "sell",
            "dump",
            "low",
            "breakdown",
            "fear",
            "panic",
            "liquidation",
            "hack",
            "reject",
            "denied",
            "ban",
            "regulation",
            "warning",
            "fail",
            "loss",
            "decline",
            "concern",
            "risk",
            "correction",
            "collapse",
        ]

        positive_count = sum(1 for kw in positive_keywords if kw in title_lower)
        negative_count = sum(1 for kw in negative_keywords if kw in title_lower)

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"

    def _classify_narrative(
        self, sentiment: str, age_minutes: int, price_change_pct: float, volume_ratio: float = 1.0
    ) -> NarrativeClassification:
        """
        Classify how price is reacting to the narrative.

        Args:
            sentiment: 'positive', 'negative', or 'neutral'
            age_minutes: How old the news is
            price_change_pct: Recent price change percentage
            volume_ratio: Current volume vs average (default 1.0)

        Returns:
            NarrativeClassification enum value
        """
        # If news is stale (> 6 hours), it's likely priced in
        if age_minutes > self.STALE_NEWS_THRESHOLD:
            return NarrativeClassification.PRICED_IN

        # For neutral sentiment, no narrative to compare
        if sentiment == "neutral":
            return NarrativeClassification.NEUTRAL

        # Fresh news (< 1 hour) - check for impulse
        if age_minutes < self.FRESH_NEWS_THRESHOLD:
            if sentiment == "positive" and price_change_pct > 1.0:
                return NarrativeClassification.IMPULSE
            elif sentiment == "negative" and price_change_pct < -1.0:
                return NarrativeClassification.IMPULSE

        # Check for divergence/absorption/distribution
        if sentiment == "positive":
            if price_change_pct > 0.5:
                # Positive news + price up = as expected, may be priced in
                if age_minutes > self.RECENT_NEWS_THRESHOLD:
                    return NarrativeClassification.PRICED_IN
                return NarrativeClassification.IMPULSE
            elif price_change_pct < -0.5:
                # Positive news + price down = DISTRIBUTION (bearish)
                return NarrativeClassification.DISTRIBUTION
            else:
                # Positive news + flat = absorbing
                return NarrativeClassification.ABSORPTION

        elif sentiment == "negative":
            if price_change_pct < -0.5:
                # Negative news + price down = as expected
                if age_minutes > self.RECENT_NEWS_THRESHOLD:
                    return NarrativeClassification.PRICED_IN
                return NarrativeClassification.IMPULSE
            elif price_change_pct > 0.5:
                # Negative news + price up = ABSORPTION (bullish divergence)
                return NarrativeClassification.ABSORPTION
            else:
                # Negative news + flat = distributing fear
                return NarrativeClassification.DISTRIBUTION

        return NarrativeClassification.NEUTRAL

    def _get_interpretation(self, classification: NarrativeClassification, sentiment: str) -> str:
        """
        Get human-readable interpretation of the classification.

        Args:
            classification: The narrative classification
            sentiment: Original news sentiment

        Returns:
            Interpretation string for prompt
        """
        interpretations = {
            NarrativeClassification.ABSORPTION: f"{'Negative' if sentiment == 'negative' else 'Bad'} news absorbed → Bullish divergence",
            NarrativeClassification.DISTRIBUTION: f"{'Positive' if sentiment == 'positive' else 'Good'} news being sold → Bearish divergence",
            NarrativeClassification.PRICED_IN: "News > 2h old, price normalized → No edge",
            NarrativeClassification.DIVERGENCE: f"Price moving opposite of {sentiment} narrative → Counter-trend signal",
            NarrativeClassification.IMPULSE: "Fresh news with immediate reaction → Momentum play",
            NarrativeClassification.NEUTRAL: "No clear narrative signal",
        }
        return interpretations.get(classification, "Unknown")

    def format_for_prompt(self, analyzed_news: Dict[str, List[Dict]]) -> str:
        """
        Format analyzed news into NoF1-style prompt section.

        Args:
            analyzed_news: Dict from analyze_news_vs_reality()

        Returns:
            Formatted string for LLM prompt
        """
        lines = []
        lines.append("## 2. NARRATIVE VS REALITY CHECK")
        lines.append("")

        has_content = False

        for symbol, news_list in analyzed_news.items():
            if not news_list:
                continue

            coin_name = symbol.split("/")[0]

            # Only show top 3 most relevant news per symbol
            for news in news_list[:3]:
                has_content = True
                classification = news["classification"]

                lines.append(f"**{news['title'][:80]}{'...' if len(news['title']) > 80 else ''}**")
                lines.append(f"- Narrative: {news['sentiment'].capitalize()} for {coin_name}")
                lines.append(f"- Time: {news['age_str']}")
                lines.append(f"- Status: **{classification}** → {news['interpretation']}")
                lines.append("")

        if not has_content:
            lines.append("No significant news affecting traded assets in the last 6 hours.")
            lines.append("")

        return "\n".join(lines)
