"""Service de validation des données de trading."""

from decimal import Decimal
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, validator

from ..core.logger import get_logger


class TradeValidation(BaseModel):
    """Modèle de validation pour les trades."""
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    
    @validator('symbol')
    def validate_symbol(cls, v):
        if not v or '/' not in v:
            raise ValueError('Symbol must be in format BASE/QUOTE (e.g., BTC/USDT)')
        return v
    
    @validator('side')
    def validate_side(cls, v):
        if v not in ['long', 'short', 'buy', 'sell']:
            raise ValueError('Side must be long, short, buy, or sell')
        return v
    
    @validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be positive')
        return v
    
    @validator('price')
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError('Price must be positive')
        return v


class ValidationService:
    """Service de validation des données."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def validate_trade_data(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Valide les données d'un trade."""
        try:
            TradeValidation(**data)
            return True, None
        except ValueError as e:
            self.logger.warning(f"Trade validation failed: {e}")
            return False, str(e)
    
    def validate_position_size(self, quantity: Decimal, max_percentage: float = 0.15) -> tuple[bool, str]:
        """Valide la taille d'une position."""
        if quantity > max_percentage:
            return False, f"Position size {quantity} exceeds maximum {max_percentage}"
        return True, "Position size valid"
    
    def validate_risk_parameters(self, entry_price: Decimal, stop_loss: Decimal, take_profit: Decimal) -> tuple[bool, str]:
        """Valide les paramètres de risque."""
        if stop_loss >= entry_price:
            return False, "Stop loss must be below entry price"
        if take_profit <= entry_price:
            return False, "Take profit must be above entry price"
        
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        ratio = reward / risk
        
        if ratio < 1.3:
            return False, f"Risk/reward ratio {ratio:.2f} below minimum 1.3"
        
        return True, f"Risk/reward ratio {ratio:.2f} is valid"


# Instance globale du service de validation
validation_service = ValidationService()
