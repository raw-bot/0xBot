"""Market analysis service for multi-coin analysis, correlations, and regime detection."""

import numpy as np
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from ..core.logger import get_logger

logger = get_logger(__name__)


class MarketAnalysisService:
    """
    Service for advanced market analysis across multiple coins.
    
    Features:
    - Correlation analysis between assets
    - BTC dominance tracking
    - Market regime detection (risk-on/risk-off)
    - Market breadth indicators
    - Capital flow analysis
    """
    
    @staticmethod
    def calculate_correlation_matrix(
        price_data: Dict[str, List[float]],
        period: int = 30
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate correlation matrix between multiple assets.
        
        Args:
            price_data: Dict of symbol -> list of prices
            period: Number of periods to use for correlation
            
        Returns:
            Correlation matrix as nested dict
        """
        try:
            symbols = list(price_data.keys())
            n = len(symbols)
            
            if n < 2:
                logger.warning("Need at least 2 symbols for correlation analysis")
                return {}
            
            # Ensure all series have same length and are long enough
            min_length = min(len(prices) for prices in price_data.values())
            if min_length < period:
                logger.warning(f"Not enough data for correlation (need {period}, got {min_length})")
                period = min_length
            
            # Calculate returns for each asset
            returns = {}
            for symbol, prices in price_data.items():
                prices_array = np.array(prices[-period:])
                returns[symbol] = np.diff(prices_array) / prices_array[:-1]
            
            # Calculate correlation matrix
            correlation_matrix = {}
            for i, symbol1 in enumerate(symbols):
                correlation_matrix[symbol1] = {}
                for j, symbol2 in enumerate(symbols):
                    if symbol1 == symbol2:
                        correlation_matrix[symbol1][symbol2] = 1.0
                    else:
                        corr = np.corrcoef(returns[symbol1], returns[symbol2])[0, 1]
                        # Handle NaN (can happen with constant prices)
                        correlation_matrix[symbol1][symbol2] = float(corr) if not np.isnan(corr) else 0.0
            
            return correlation_matrix
            
        except Exception as e:
            logger.error(f"Error calculating correlation matrix: {e}")
            return {}
    
    @staticmethod
    def calculate_btc_dominance(
        market_caps: Dict[str, float]
    ) -> float:
        """
        Calculate BTC dominance (BTC market cap / total crypto market cap).
        
        Args:
            market_caps: Dict of symbol -> market cap
            
        Returns:
            BTC dominance as percentage (0-100)
        """
        try:
            if 'BTC/USDT' not in market_caps and 'BTCUSDT' not in market_caps:
                logger.warning("BTC not found in market caps")
                return 0.0
            
            btc_key = 'BTC/USDT' if 'BTC/USDT' in market_caps else 'BTCUSDT'
            btc_cap = market_caps[btc_key]
            total_cap = sum(market_caps.values())
            
            if total_cap == 0:
                return 0.0
            
            dominance = (btc_cap / total_cap) * 100
            return float(dominance)
            
        except Exception as e:
            logger.error(f"Error calculating BTC dominance: {e}")
            return 0.0
    
    @staticmethod
    def detect_market_regime(
        price_data: Dict[str, List[float]],
        volatility_threshold: float = 0.02
    ) -> Dict[str, any]:
        """
        Detect current market regime (risk-on/risk-off/neutral).
        
        Uses multiple signals:
        - Correlation between assets (high = risk-off, low = risk-on)
        - Average volatility
        - BTC vs alts performance
        
        Args:
            price_data: Dict of symbol -> list of prices
            volatility_threshold: Threshold for high volatility
            
        Returns:
            Dict with regime info
        """
        try:
            if len(price_data) < 2:
                return {
                    'regime': 'unknown',
                    'confidence': 0.0,
                    'signals': {}
                }
            
            # Calculate correlations
            correlations = MarketAnalysisService.calculate_correlation_matrix(price_data, period=20)
            
            # Average correlation (excluding diagonal)
            all_corrs = []
            for symbol1, corr_dict in correlations.items():
                for symbol2, corr_value in corr_dict.items():
                    if symbol1 != symbol2:
                        all_corrs.append(corr_value)
            
            avg_correlation = np.mean(all_corrs) if all_corrs else 0.0
            
            # Calculate volatility for each asset
            volatilities = {}
            for symbol, prices in price_data.items():
                prices_array = np.array(prices[-20:])
                returns = np.diff(prices_array) / prices_array[:-1]
                volatilities[symbol] = np.std(returns)
            
            avg_volatility = np.mean(list(volatilities.values()))
            
            # Calculate recent performance (last 20 periods)
            performances = {}
            for symbol, prices in price_data.items():
                if len(prices) >= 20:
                    perf = (prices[-1] - prices[-20]) / prices[-20]
                    performances[symbol] = perf
            
            # BTC vs alts
            btc_key = next((k for k in performances.keys() if 'BTC' in k), None)
            btc_performance = performances.get(btc_key, 0.0) if btc_key else 0.0
            
            alt_performances = [perf for symbol, perf in performances.items() if 'BTC' not in symbol]
            avg_alt_performance = np.mean(alt_performances) if alt_performances else 0.0
            
            # Determine regime
            signals = {
                'avg_correlation': float(avg_correlation),
                'avg_volatility': float(avg_volatility),
                'btc_performance': float(btc_performance),
                'alt_performance': float(avg_alt_performance),
                'high_volatility': avg_volatility > volatility_threshold
            }
            
            # Risk-on: Low correlation, alts outperform BTC, moderate volatility
            risk_on_score = 0
            if avg_correlation < 0.6:  # Plus strict (nécessite vraiment low correlation)
                risk_on_score += 1
            if avg_alt_performance > btc_performance + 0.01:  # Alts doivent VRAIMENT surperformer (+1%)
                risk_on_score += 1
            if avg_volatility < volatility_threshold * 0.8:  # Volatilité vraiment basse
                risk_on_score += 1
            
            # Risk-off: High correlation, BTC outperforms alts, high volatility
            risk_off_score = 0
            if avg_correlation > 0.7:
                risk_off_score += 1
            if btc_performance > avg_alt_performance + 0.01:  # BTC doit VRAIMENT surperformer
                risk_off_score += 1
            if avg_volatility > volatility_threshold * 1.2:  # Volatilité vraiment haute
                risk_off_score += 1
            
            # Determine regime - PLUS STRICT
            if risk_on_score == 3:  # Exiger 3/3 pour risk-on avec haute confiance
                regime = 'risk_on'
                confidence = 1.0
            elif risk_on_score == 2:  # 2/3 = risk-on mais confiance moyenne
                regime = 'risk_on'
                confidence = 0.67
            elif risk_off_score == 3:  # 3/3 pour risk-off
                regime = 'risk_off'
                confidence = 1.0
            elif risk_off_score == 2:  # 2/3 pour risk-off
                regime = 'risk_off'
                confidence = 0.67
            else:
                regime = 'neutral'
                confidence = 0.5
            
            return {
                'regime': regime,
                'confidence': float(confidence),
                'signals': signals
            }
            
        except Exception as e:
            logger.error(f"Error detecting market regime: {e}")
            return {
                'regime': 'unknown',
                'confidence': 0.0,
                'signals': {}
            }
    
    @staticmethod
    def calculate_market_breadth(
        price_changes: Dict[str, float]
    ) -> Dict[str, any]:
        """
        Calculate market breadth indicators.
        
        Args:
            price_changes: Dict of symbol -> price change percentage
            
        Returns:
            Dict with breadth metrics
        """
        try:
            if not price_changes:
                return {
                    'advance_decline_ratio': 0.0,
                    'advancing': 0,
                    'declining': 0,
                    'unchanged': 0,
                    'average_change': 0.0
                }
            
            advancing = sum(1 for change in price_changes.values() if change > 0)
            declining = sum(1 for change in price_changes.values() if change < 0)
            unchanged = sum(1 for change in price_changes.values() if change == 0)
            
            # Advance/Decline ratio
            ad_ratio = advancing / declining if declining > 0 else (advancing if advancing > 0 else 1.0)
            
            # Average change
            avg_change = np.mean(list(price_changes.values()))
            
            return {
                'advance_decline_ratio': float(ad_ratio),
                'advancing': advancing,
                'declining': declining,
                'unchanged': unchanged,
                'average_change': float(avg_change),
                'breadth_strong': advancing > declining * 1.5  # Strong breadth if 1.5x more advancing
            }
            
        except Exception as e:
            logger.error(f"Error calculating market breadth: {e}")
            return {
                'advance_decline_ratio': 0.0,
                'advancing': 0,
                'declining': 0,
                'unchanged': 0,
                'average_change': 0.0
            }
    
    @staticmethod
    def analyze_capital_flows(
        volumes: Dict[str, float],
        price_changes: Dict[str, float]
    ) -> Dict[str, any]:
        """
        Analyze capital flows between assets.
        
        Args:
            volumes: Dict of symbol -> trading volume
            price_changes: Dict of symbol -> price change percentage
            
        Returns:
            Dict with flow analysis
        """
        try:
            if not volumes or not price_changes:
                return {
                    'btc_inflow': False,
                    'alt_inflow': False,
                    'dominant_flow': 'unknown'
                }
            
            # Separate BTC and alts
            btc_symbols = [s for s in volumes.keys() if 'BTC' in s]
            alt_symbols = [s for s in volumes.keys() if 'BTC' not in s]
            
            # BTC volume-weighted flow
            btc_flow = 0
            btc_total_vol = 0
            for symbol in btc_symbols:
                if symbol in volumes and symbol in price_changes:
                    btc_flow += volumes[symbol] * price_changes[symbol]
                    btc_total_vol += volumes[symbol]
            
            # Alt volume-weighted flow
            alt_flow = 0
            alt_total_vol = 0
            for symbol in alt_symbols:
                if symbol in volumes and symbol in price_changes:
                    alt_flow += volumes[symbol] * price_changes[symbol]
                    alt_total_vol += volumes[symbol]
            
            # Normalize
            btc_flow = btc_flow / btc_total_vol if btc_total_vol > 0 else 0
            alt_flow = alt_flow / alt_total_vol if alt_total_vol > 0 else 0
            
            # Determine dominant flow
            if btc_flow > 0 and btc_flow > alt_flow * 1.2:
                dominant_flow = 'into_btc'
            elif alt_flow > 0 and alt_flow > btc_flow * 1.2:
                dominant_flow = 'into_alts'
            elif btc_flow < 0 and alt_flow < 0:
                dominant_flow = 'out_of_crypto'
            else:
                dominant_flow = 'balanced'
            
            return {
                'btc_inflow': btc_flow > 0,
                'alt_inflow': alt_flow > 0,
                'btc_flow_strength': float(btc_flow),
                'alt_flow_strength': float(alt_flow),
                'dominant_flow': dominant_flow
            }
            
        except Exception as e:
            logger.error(f"Error analyzing capital flows: {e}")
            return {
                'btc_inflow': False,
                'alt_inflow': False,
                'dominant_flow': 'unknown'
            }
    
    @staticmethod
    def get_comprehensive_market_context(
        multi_coin_data: Dict[str, Dict[str, any]]
    ) -> Dict[str, any]:
        """
        Get comprehensive market context from multi-coin data.
        
        Args:
            multi_coin_data: Dict of symbol -> {prices, volume, market_cap, etc}
            
        Returns:
            Complete market analysis
        """
        try:
            # Extract data
            price_data = {}
            volumes = {}
            market_caps = {}
            price_changes = {}
            
            for symbol, data in multi_coin_data.items():
                if 'prices' in data:
                    price_data[symbol] = data['prices']
                    
                    # Calculate price change
                    if len(data['prices']) >= 2:
                        price_changes[symbol] = (data['prices'][-1] - data['prices'][-20]) / data['prices'][-20] if len(data['prices']) >= 20 else 0
                
                if 'volume' in data:
                    volumes[symbol] = data['volume']
                
                if 'market_cap' in data:
                    market_caps[symbol] = data['market_cap']
            
            # Calculate all metrics
            correlations = MarketAnalysisService.calculate_correlation_matrix(price_data)
            regime = MarketAnalysisService.detect_market_regime(price_data)
            breadth = MarketAnalysisService.calculate_market_breadth(price_changes)
            flows = MarketAnalysisService.analyze_capital_flows(volumes, price_changes)
            
            # BTC dominance (if market caps available)
            btc_dominance = 0.0
            if market_caps:
                btc_dominance = MarketAnalysisService.calculate_btc_dominance(market_caps)
            
            return {
                'correlations': correlations,
                'regime': regime,
                'breadth': breadth,
                'capital_flows': flows,
                'btc_dominance': btc_dominance,
                'analyzed_symbols': list(multi_coin_data.keys()),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting comprehensive market context: {e}")
            return {
                'correlations': {},
                'regime': {'regime': 'unknown', 'confidence': 0.0},
                'breadth': {},
                'capital_flows': {},
                'btc_dominance': 0.0,
                'analyzed_symbols': [],
                'timestamp': datetime.utcnow().isoformat()
            }

