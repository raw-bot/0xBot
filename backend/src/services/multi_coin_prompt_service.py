"""
Multi-Coin Prompt Service - Backward compatibility wrapper.

This module has been refactored into a modular package structure:
- multi_coin_prompt.service.MultiCoinPromptService (facade)
- multi_coin_prompt.prompt_builder.PromptBuilder
- multi_coin_prompt.market_formatter.MarketDataFormatter
- multi_coin_prompt.analysis_integrator.AnalysisIntegrator

For backward compatibility, we re-export the main service here.
"""

# Import from new package location for backward compatibility
from .multi_coin_prompt.service import MultiCoinPromptService

__all__ = ["MultiCoinPromptService"]
