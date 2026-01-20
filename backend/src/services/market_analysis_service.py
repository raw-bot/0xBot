"""Market analysis service for multi-coin analysis, correlations, and regime detection."""

from datetime import datetime
from typing import Any, Dict, List

import numpy as np

from ..core.logger import get_logger

logger = get_logger(__name__)


class MarketAnalysisService:
    """Service for advanced market analysis across multiple coins."""

    @staticmethod
    def calculate_correlation_matrix(
        price_data: dict[str, list[float]], period: int = 30
    ) -> dict[str, dict[str, float]]:
        """Calculate correlation matrix between multiple assets."""
        try:
            symbols = list(price_data.keys())
            if len(symbols) < 2:
                return {}

            min_length = min(len(prices) for prices in price_data.values())
            period = min(period, min_length)

            returns = {
                symbol: np.diff(np.array(prices[-period:])) / np.array(prices[-period:])[:-1]
                for symbol, prices in price_data.items()
            }

            correlation_matrix: dict[str, dict[str, float]] = {}
            for symbol1 in symbols:
                correlation_matrix[symbol1] = {}
                for symbol2 in symbols:
                    if symbol1 == symbol2:
                        correlation_matrix[symbol1][symbol2] = 1.0
                    else:
                        corr = np.corrcoef(returns[symbol1], returns[symbol2])[0, 1]
                        correlation_matrix[symbol1][symbol2] = 0.0 if np.isnan(corr) else float(corr)
            return correlation_matrix
        except Exception as e:
            logger.error(f"Error calculating correlation matrix: {e}")
            return {}

    @staticmethod
    def calculate_btc_dominance(market_caps: dict[str, float]) -> float:
        """Calculate BTC dominance (BTC market cap / total crypto market cap)."""
        try:
            btc_key = next((k for k in market_caps if "BTC" in k), None)
            if not btc_key:
                return 0.0
            total_cap = sum(market_caps.values())
            return (market_caps[btc_key] / total_cap * 100) if total_cap else 0.0
        except Exception as e:
            logger.error(f"Error calculating BTC dominance: {e}")
            return 0.0
    
    @staticmethod
    def detect_market_regime(
        price_data: dict[str, list[float]], volatility_threshold: float = 0.02
    ) -> dict[str, Any]:
        """Detect current market regime (risk-on/risk-off/neutral)."""
        try:
            if len(price_data) < 2:
                return {"regime": "unknown", "confidence": 0.0, "signals": {}}

            correlations = MarketAnalysisService.calculate_correlation_matrix(price_data, period=20)

            all_corrs = [
                corr for s1, corr_dict in correlations.items()
                for s2, corr in corr_dict.items() if s1 != s2
            ]
            avg_correlation = float(np.mean(all_corrs)) if all_corrs else 0.0

            volatilities = []
            performances = {}
            for symbol, prices in price_data.items():
                prices_array = np.array(prices[-20:])
                returns = np.diff(prices_array) / prices_array[:-1]
                volatilities.append(np.std(returns))
                if len(prices) >= 20:
                    performances[symbol] = (prices[-1] - prices[-20]) / prices[-20]

            avg_volatility = float(np.mean(volatilities))

            btc_key = next((k for k in performances if "BTC" in k), None)
            btc_perf = performances.get(btc_key, 0.0) if btc_key else 0.0
            alt_perfs = [p for s, p in performances.items() if "BTC" not in s]
            avg_alt_perf = float(np.mean(alt_perfs)) if alt_perfs else 0.0

            signals = {
                "avg_correlation": avg_correlation,
                "avg_volatility": avg_volatility,
                "btc_performance": float(btc_perf),
                "alt_performance": avg_alt_perf,
                "high_volatility": avg_volatility > volatility_threshold,
            }

            risk_on_score = sum([
                avg_correlation < 0.6,
                avg_alt_perf > btc_perf + 0.01,
                avg_volatility < volatility_threshold * 0.8,
            ])
            risk_off_score = sum([
                avg_correlation > 0.7,
                btc_perf > avg_alt_perf + 0.01,
                avg_volatility > volatility_threshold * 1.2,
            ])

            if risk_on_score >= 2:
                regime, confidence = "risk_on", 1.0 if risk_on_score == 3 else 0.67
            elif risk_off_score >= 2:
                regime, confidence = "risk_off", 1.0 if risk_off_score == 3 else 0.67
            else:
                regime, confidence = "neutral", 0.5

            return {"regime": regime, "confidence": confidence, "signals": signals}
        except Exception as e:
            logger.error(f"Error detecting market regime: {e}")
            return {"regime": "unknown", "confidence": 0.0, "signals": {}}
    
    @staticmethod
    def calculate_market_breadth(price_changes: dict[str, float]) -> dict[str, Any]:
        """Calculate market breadth indicators."""
        try:
            if not price_changes:
                return {
                    "advance_decline_ratio": 0.0, "advancing": 0, "declining": 0,
                    "unchanged": 0, "average_change": 0.0,
                }

            changes = list(price_changes.values())
            advancing = sum(1 for c in changes if c > 0)
            declining = sum(1 for c in changes if c < 0)
            unchanged = sum(1 for c in changes if c == 0)
            ad_ratio = advancing / declining if declining else (advancing or 1.0)

            return {
                "advance_decline_ratio": float(ad_ratio),
                "advancing": advancing,
                "declining": declining,
                "unchanged": unchanged,
                "average_change": float(np.mean(changes)),
                "breadth_strong": advancing > declining * 1.5,
            }
        except Exception as e:
            logger.error(f"Error calculating market breadth: {e}")
            return {
                "advance_decline_ratio": 0.0, "advancing": 0, "declining": 0,
                "unchanged": 0, "average_change": 0.0,
            }

    @staticmethod
    def analyze_capital_flows(volumes: dict[str, float], price_changes: dict[str, float]) -> dict[str, Any]:
        """Analyze capital flows between assets."""
        try:
            if not volumes or not price_changes:
                return {"btc_inflow": False, "alt_inflow": False, "dominant_flow": "unknown"}

            def calc_flow(symbols: list[str]) -> float:
                flow = sum(volumes.get(s, 0) * price_changes.get(s, 0) for s in symbols)
                total = sum(volumes.get(s, 0) for s in symbols)
                return flow / total if total else 0

            btc_symbols = [s for s in volumes if "BTC" in s]
            alt_symbols = [s for s in volumes if "BTC" not in s]
            btc_flow = calc_flow(btc_symbols)
            alt_flow = calc_flow(alt_symbols)

            if btc_flow > 0 and btc_flow > alt_flow * 1.2:
                dominant = "into_btc"
            elif alt_flow > 0 and alt_flow > btc_flow * 1.2:
                dominant = "into_alts"
            elif btc_flow < 0 and alt_flow < 0:
                dominant = "out_of_crypto"
            else:
                dominant = "balanced"

            return {
                "btc_inflow": btc_flow > 0,
                "alt_inflow": alt_flow > 0,
                "btc_flow_strength": float(btc_flow),
                "alt_flow_strength": float(alt_flow),
                "dominant_flow": dominant,
            }
        except Exception as e:
            logger.error(f"Error analyzing capital flows: {e}")
            return {"btc_inflow": False, "alt_inflow": False, "dominant_flow": "unknown"}

    @staticmethod
    def get_comprehensive_market_context(multi_coin_data: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """Get comprehensive market context from multi-coin data."""
        try:
            price_data, volumes, market_caps, price_changes = {}, {}, {}, {}

            for symbol, data in multi_coin_data.items():
                if "prices" in data:
                    price_data[symbol] = data["prices"]
                    if len(data["prices"]) >= 20:
                        price_changes[symbol] = (data["prices"][-1] - data["prices"][-20]) / data["prices"][-20]
                if "volume" in data:
                    volumes[symbol] = data["volume"]
                if "market_cap" in data:
                    market_caps[symbol] = data["market_cap"]

            return {
                "correlations": MarketAnalysisService.calculate_correlation_matrix(price_data),
                "regime": MarketAnalysisService.detect_market_regime(price_data),
                "breadth": MarketAnalysisService.calculate_market_breadth(price_changes),
                "capital_flows": MarketAnalysisService.analyze_capital_flows(volumes, price_changes),
                "btc_dominance": MarketAnalysisService.calculate_btc_dominance(market_caps) if market_caps else 0.0,
                "analyzed_symbols": list(multi_coin_data.keys()),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error getting comprehensive market context: {e}")
            return {
                "correlations": {},
                "regime": {"regime": "unknown", "confidence": 0.0},
                "breadth": {},
                "capital_flows": {},
                "btc_dominance": 0.0,
                "analyzed_symbols": [],
                "timestamp": datetime.utcnow().isoformat(),
            }

