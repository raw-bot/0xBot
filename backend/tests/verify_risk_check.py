import asyncio
import os
import sys
from decimal import Decimal
from unittest.mock import MagicMock, Mock

# Read the file content
file_path = os.path.join(os.getcwd(), "backend/src/services/risk_manager_service.py")
with open(file_path, "r") as f:
    content = f.read()

# Remove imports to avoid issues
lines = content.split("\n")
filtered_lines = []
for line in lines:
    if line.strip().startswith("from ..") or line.strip().startswith("import "):
        continue
    filtered_lines.append(line)

# Reassemble code
code = "\n".join(filtered_lines)

# Create a namespace for execution
logger_mock = MagicMock()


def get_logger_mock(name):
    return logger_mock


namespace = {
    "Decimal": Decimal,
    "Optional": None,
    "uuid": MagicMock(),
    "get_logger": get_logger_mock,
    "logger": logger_mock,
    "config": MagicMock(),
    "Bot": MagicMock(),
    "Position": MagicMock(),
    "PositionStatus": MagicMock(),
}

# Mock config values
namespace["config"].DEFAULT_POSITION_SIZE_PCT = 0.10
namespace["PositionStatus"].OPEN = "OPEN"

# Execute the class definition
exec(code, namespace)

# Get the class
RiskManagerService = namespace["RiskManagerService"]


async def test_risk_validation():
    print("🧪 Testing Risk Manager Validation (Exec)...")

    # Mock Bot
    bot = MagicMock()
    bot.capital = Decimal("10000")
    bot.risk_params = {"max_position_pct": 0.08, "max_drawdown_pct": 0.20}

    # Test Case 1: Valid Trade (5% size)
    print("\n1. Testing Valid Trade (5% size)...")
    decision_valid = {
        "symbol": "BTC/USDT",
        "size_pct": 0.05,
        "side": "long",
        "entry_price": 50000,
        "stop_loss": 49000,
        "take_profit": 52000,
    }
    is_valid, reason = RiskManagerService.validate_entry(bot, decision_valid, [], Decimal("50000"))
    if is_valid:
        print("✅ PASS: Valid trade accepted")
    else:
        print(f"❌ FAIL: Valid trade rejected: {reason}")

    # Test Case 2: Excessive Size (20% size > 8% max)
    print("\n2. Testing Excessive Size (20% size)...")
    decision_large = {
        "symbol": "ETH/USDT",
        "size_pct": 0.20,
        "side": "long",
        "entry_price": 3000,
        "stop_loss": 2900,
        "take_profit": 3200,
    }
    is_valid, reason = RiskManagerService.validate_entry(bot, decision_large, [], Decimal("3000"))
    if not is_valid and "exceeds max" in reason:
        print(f"✅ PASS: Large trade rejected correctly: {reason}")
    else:
        print(f"❌ FAIL: Large trade NOT rejected properly. Result: {is_valid}, Reason: {reason}")

    # Test Case 3: Negative Capital Protection
    print("\n3. Testing Negative Capital...")
    quantity = RiskManagerService.calculate_position_size(
        Decimal("-100"), Decimal("0.05"), Decimal("100")
    )
    if quantity == 0:
        print("✅ PASS: Negative capital results in 0 quantity")
    else:
        print(f"❌ FAIL: Negative capital allowed quantity {quantity}")


if __name__ == "__main__":
    asyncio.run(test_risk_validation())
