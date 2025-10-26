"""Technical indicator service using TA-Lib."""

import numpy as np
import talib
from typing import Optional

from ..core.logger import get_logger

logger = get_logger(__name__)


class IndicatorService:
    """Service for calculating technical indicators."""
    
    @staticmethod
    def calculate_ema(
        prices: list[float],
        period: int = 20
    ) -> list[float]:
        """
        Calculate Exponential Moving Average.
        
        Args:
            prices: List of prices (typically closing prices)
            period: EMA period (default: 20)
            
        Returns:
            List of EMA values (same length as input, with NaN for initial values)
        """
        try:
            prices_array = np.array(prices, dtype=float)
            ema = talib.EMA(prices_array, timeperiod=period)
            
            # Convert NaN to None for cleaner handling
            result = [float(val) if not np.isnan(val) else None for val in ema]
            
            logger.debug(f"Calculated EMA({period}) for {len(prices)} prices")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating EMA: {e}")
            raise
    
    @staticmethod
    def calculate_sma(
        prices: list[float],
        period: int = 20
    ) -> list[float]:
        """
        Calculate Simple Moving Average.
        
        Args:
            prices: List of prices
            period: SMA period (default: 20)
            
        Returns:
            List of SMA values
        """
        try:
            prices_array = np.array(prices, dtype=float)
            sma = talib.SMA(prices_array, timeperiod=period)
            
            result = [float(val) if not np.isnan(val) else None for val in sma]
            
            logger.debug(f"Calculated SMA({period}) for {len(prices)} prices")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating SMA: {e}")
            raise
    
    @staticmethod
    def calculate_rsi(
        prices: list[float],
        period: int = 14
    ) -> list[float]:
        """
        Calculate Relative Strength Index.
        
        Args:
            prices: List of prices
            period: RSI period (default: 14)
            
        Returns:
            List of RSI values (0-100 range)
        """
        try:
            prices_array = np.array(prices, dtype=float)
            rsi = talib.RSI(prices_array, timeperiod=period)
            
            result = [float(val) if not np.isnan(val) else None for val in rsi]
            
            logger.debug(f"Calculated RSI({period}) for {len(prices)} prices")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            raise
    
    @staticmethod
    def calculate_macd(
        prices: list[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> dict:
        """
        Calculate MACD (Moving Average Convergence Divergence).
        
        Args:
            prices: List of prices
            fast_period: Fast EMA period (default: 12)
            slow_period: Slow EMA period (default: 26)
            signal_period: Signal line period (default: 9)
            
        Returns:
            Dictionary with 'macd', 'signal', 'histogram' lists
        """
        try:
            prices_array = np.array(prices, dtype=float)
            macd, signal, histogram = talib.MACD(
                prices_array,
                fastperiod=fast_period,
                slowperiod=slow_period,
                signalperiod=signal_period
            )
            
            result = {
                'macd': [float(val) if not np.isnan(val) else None for val in macd],
                'signal': [float(val) if not np.isnan(val) else None for val in signal],
                'histogram': [float(val) if not np.isnan(val) else None for val in histogram]
            }
            
            logger.debug(f"Calculated MACD for {len(prices)} prices")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating MACD: {e}")
            raise
    
    @staticmethod
    def calculate_bollinger_bands(
        prices: list[float],
        period: int = 20,
        std_dev: int = 2
    ) -> dict:
        """
        Calculate Bollinger Bands.
        
        Args:
            prices: List of prices
            period: Moving average period (default: 20)
            std_dev: Number of standard deviations (default: 2)
            
        Returns:
            Dictionary with 'upper', 'middle', 'lower' lists
        """
        try:
            prices_array = np.array(prices, dtype=float)
            upper, middle, lower = talib.BBANDS(
                prices_array,
                timeperiod=period,
                nbdevup=std_dev,
                nbdevdn=std_dev
            )
            
            result = {
                'upper': [float(val) if not np.isnan(val) else None for val in upper],
                'middle': [float(val) if not np.isnan(val) else None for val in middle],
                'lower': [float(val) if not np.isnan(val) else None for val in lower]
            }
            
            logger.debug(f"Calculated Bollinger Bands for {len(prices)} prices")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {e}")
            raise
    
    @staticmethod
    def calculate_atr(
        highs: list[float],
        lows: list[float],
        closes: list[float],
        period: int = 14
    ) -> list[float]:
        """
        Calculate Average True Range (volatility indicator).
        
        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of closing prices
            period: ATR period (default: 14)
            
        Returns:
            List of ATR values
        """
        try:
            highs_array = np.array(highs, dtype=float)
            lows_array = np.array(lows, dtype=float)
            closes_array = np.array(closes, dtype=float)
            
            atr = talib.ATR(highs_array, lows_array, closes_array, timeperiod=period)
            
            result = [float(val) if not np.isnan(val) else None for val in atr]
            
            logger.debug(f"Calculated ATR({period}) for {len(closes)} candles")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating ATR: {e}")
            raise
    
    @staticmethod
    def calculate_stochastic(
        highs: list[float],
        lows: list[float],
        closes: list[float],
        fastk_period: int = 14,
        slowk_period: int = 3,
        slowd_period: int = 3
    ) -> dict:
        """
        Calculate Stochastic Oscillator.
        
        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of closing prices
            fastk_period: Fast %K period (default: 14)
            slowk_period: Slow %K period (default: 3)
            slowd_period: Slow %D period (default: 3)
            
        Returns:
            Dictionary with 'k' and 'd' lists
        """
        try:
            highs_array = np.array(highs, dtype=float)
            lows_array = np.array(lows, dtype=float)
            closes_array = np.array(closes, dtype=float)
            
            slowk, slowd = talib.STOCH(
                highs_array,
                lows_array,
                closes_array,
                fastk_period=fastk_period,
                slowk_period=slowk_period,
                slowd_period=slowd_period
            )
            
            result = {
                'k': [float(val) if not np.isnan(val) else None for val in slowk],
                'd': [float(val) if not np.isnan(val) else None for val in slowd]
            }
            
            logger.debug(f"Calculated Stochastic for {len(closes)} candles")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating Stochastic: {e}")
            raise
    
    @staticmethod
    def calculate_all_indicators(
        closes: list[float],
        highs: Optional[list[float]] = None,
        lows: Optional[list[float]] = None
    ) -> dict:
        """
        Calculate all commonly used indicators at once.
        
        Args:
            closes: List of closing prices
            highs: Optional list of high prices (for ATR, etc.)
            lows: Optional list of low prices (for ATR, etc.)
            
        Returns:
            Dictionary with all indicator values
        """
        try:
            indicators = {
                'ema_20': IndicatorService.calculate_ema(closes, 20),
                'ema_50': IndicatorService.calculate_ema(closes, 50),
                'sma_20': IndicatorService.calculate_sma(closes, 20),
                'rsi_14': IndicatorService.calculate_rsi(closes, 14),
                'macd': IndicatorService.calculate_macd(closes),
                'bb': IndicatorService.calculate_bollinger_bands(closes)
            }
            
            # Add indicators that require high/low data
            if highs and lows:
                indicators['atr_14'] = IndicatorService.calculate_atr(highs, lows, closes, 14)
                indicators['stoch'] = IndicatorService.calculate_stochastic(highs, lows, closes)
            
            logger.debug(f"Calculated all indicators for {len(closes)} prices")
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculating all indicators: {e}")
            raise
    
    @staticmethod
    def get_latest_values(indicators: dict) -> dict:
        """
        Extract the latest (most recent) value from each indicator.
        
        Args:
            indicators: Dictionary of indicator arrays
            
        Returns:
            Dictionary with latest values only (None values kept as None for proper handling)
        """
        latest = {}
        
        for key, value in indicators.items():
            if isinstance(value, dict):
                # Handle nested dictionaries (like MACD, BB)
                latest[key] = {}
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, list) and sub_value:
                        # Get last non-None value, but if all are None keep None
                        non_none = [v for v in reversed(sub_value) if v is not None]
                        latest[key][sub_key] = non_none[0] if non_none else None
                    else:
                        latest[key][sub_key] = None
            elif isinstance(value, list) and value:
                # Get last non-None value from the end
                # Start from the end to get most recent valid value
                non_none = [v for v in reversed(value) if v is not None]
                latest[key] = non_none[0] if non_none else None
            else:
                latest[key] = None
        
        return latest