#!/usr/bin/env python3
"""
Test script to validate the SL/TP validation fix
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from decimal import Decimal
from services.risk_manager_service import RiskManagerService
from models.bot import Bot
from models.position import Position, PositionStatus

def test_sl_tp_validation():
    """Test the SL/TP validation with absolute prices"""

    # Create a mock bot
    bot = Bot(
        id="test-bot-id",
        name="Test Bot",
        model_name="test",
        initial_capital=Decimal("10000"),
        capital=Decimal("10000"),
        trading_symbols=["ETH/USDT"],
        risk_params={
            "max_position_pct": 0.10,
            "max_drawdown_pct": 0.20,
            "max_trades_per_day": 10,
            "stop_loss_pct": 0.035,
            "take_profit_pct": 0.07
        }
    )

    # Test decision with absolute prices (like LLM provides)
    decision = {
        "symbol": "ETH/USDT",
        "action": "entry",
        "entry_price": 4064.62,  # Current market price
        "side": "long",
        "stop_loss": 4035.0,     # 0.73% below entry
        "take_profit": 4150.0,   # 2.11% above entry
        "size_pct": 0.05         # 5% position size
    }

    current_price = Decimal("4064.62")
    current_positions = []

    print("🧪 Testing SL/TP validation...")
    print(f"   Entry Price: ${decision['entry_price']}")
    print(f"   Stop Loss: ${decision['stop_loss']} ({(1 - decision['stop_loss']/decision['entry_price'])*100:.2f}%)")
    print(f"   Take Profit: ${decision['take_profit']} ({(decision['take_profit']/decision['entry_price'] - 1)*100:.2f}%)")
    print(f"   Side: {decision['side']}")

    # Test validation
    is_valid, message = RiskManagerService.validate_entry(
        bot=bot,
        decision=decision,
        current_positions=current_positions,
        current_price=current_price
    )

    print(f"\n✅ Validation Result: {'PASSED' if is_valid else 'FAILED'}")
    print(f"   Message: {message}")

    if is_valid:
        print("\n🎉 Fix successful! The validation now works with absolute prices.")
        return True
    else:
        print("\n❌ Fix failed! Validation still rejects valid SL/TP.")
        return False

def test_edge_cases():
    """Test edge cases"""

    print("\n🧪 Testing edge cases...")

    bot = Bot(
        id="test-bot-id",
        name="Test Bot",
        model_name="test",
        initial_capital=Decimal("10000"),
        capital=Decimal("10000"),
        trading_symbols=["ETH/USDT"],
        risk_params={
            "max_position_pct": 0.10,
            "max_drawdown_pct": 0.20,
            "max_trades_per_day": 10,
            "stop_loss_pct": 0.035,
            "take_profit_pct": 0.07
        }
    )

    current_price = Decimal("4064.62")
    current_positions = []

    # Test 1: Missing entry_price (should use current_price)
    decision1 = {
        "symbol": "ETH/USDT",
        "action": "entry",
        "side": "long",
        "stop_loss": 4035.0,
        "take_profit": 4150.0,
        "size_pct": 0.05
    }

    is_valid1, message1 = RiskManagerService.validate_entry(
        bot=bot,
        decision=decision1,
        current_positions=current_positions,
        current_price=current_price
    )

    print(f"   Test 1 (no entry_price): {'PASSED' if is_valid1 else 'FAILED'} - {message1}")

    # Test 2: Invalid price relationships (SL > Entry for LONG)
    decision2 = {
        "symbol": "ETH/USDT",
        "action": "entry",
        "entry_price": 4064.62,
        "side": "long",
        "stop_loss": 4100.0,  # Above entry (invalid for LONG)
        "take_profit": 4150.0,
        "size_pct": 0.05
    }

    is_valid2, message2 = RiskManagerService.validate_entry(
        bot=bot,
        decision=decision2,
        current_positions=current_positions,
        current_price=current_price
    )

    print(f"   Test 2 (invalid SL position): {'PASSED' if not is_valid2 else 'FAILED'} - {message2}")

    return is_valid1 and not is_valid2

if __name__ == "__main__":
    print("🚀 Testing SL/TP validation fix...\n")

    success1 = test_sl_tp_validation()
    success2 = test_edge_cases()

    if success1 and success2:
        print("\n🎉 All tests PASSED! The fix is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests FAILED! The fix needs more work.")
        sys.exit(1)