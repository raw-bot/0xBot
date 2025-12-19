import asyncio
import json
import os
import re
import sys
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, Mock

# Read the file content
file_path = os.path.join(os.getcwd(), "backend/src/services/monk_mode_service.py")
with open(file_path, "r") as f:
    content = f.read()

# Remove imports to avoid issues
lines = content.split("\n")
filtered_lines = []
for line in lines:
    if line.strip().startswith("from ..") or line.strip().startswith("import "):
        # Keep standard library imports if needed, but for safety let's mock or rely on exec context
        if (
            "json" in line
            or "re" in line
            or "datetime" in line
            or "decimal" in line
            or "typing" in line
        ):
            filtered_lines.append(line)
        else:
            continue
    else:
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
    "List": list,
    "Dict": dict,
    "Any": object,
    "json": json,
    "re": re,
    "datetime": datetime,
    "logging": MagicMock(),
    "logger": logger_mock,
}
namespace["logging"].getLogger.return_value = logger_mock

# Execute the class definition
exec(code, namespace)

# Get the class
MonkModePromptService = namespace["MonkModePromptService"]


async def test_monk_mode_service():
    print("🧪 Testing Monk Mode Service (Exec)...")

    service = MonkModePromptService()

    # Mock Data
    bot = MagicMock()
    all_coins_data = {
        "BTC/USDT": {
            "snapshot": {
                "current_price": 95000,
                "funding_rate": 0.0001,
                "technical_indicators": {"5m": {"rsi14": 60, "macd": 100}},
            }
        }
    }
    all_positions = []
    portfolio_state = {"cash": 10000, "total_value": 10000}

    # 1. Test Prompt Generation
    print("\n1. Testing Prompt Generation...")
    decision_data = service.get_monk_mode_decision(
        bot, all_coins_data, all_positions, portfolio_state
    )
    prompt = decision_data["prompt"]

    # Verify key sections exist
    required_sections = [
        "Context Snapshot",
        "Raw Data Dashboard",
        "Narrative vs Reality",
        "FOMO Map",
        "Alpha Setups",
        "Edge Quality Matrix",
        "Kelly-like logic",
    ]

    all_present = True
    for section in required_sections:
        if section not in prompt:
            print(f"❌ Missing section: {section}")
            all_present = False

    if all_present:
        print("✅ PASS: All required prompt sections present")

    # 2. Test JSON Parsing
    print("\n2. Testing JSON Parsing...")
    mock_llm_response = """
    CHAIN_OF_THOUGHT:
    The market is bullish. I see an edge in BTC.

    ```json
    {
      "BTC/USDT": {
        "signal": "buy_to_enter",
        "confidence": 0.8,
        "quantity": 0.1,
        "leverage": 1,
        "stop_loss": 94000,
        "profit_target": 100000,
        "invalidation_condition": "Close below 94k",
        "justification": "Trend follow",
        "risk_usd": 100
      }
    }
    ```
    """

    parsed = service.parse_monk_mode_response(mock_llm_response)
    if "BTC/USDT" in parsed and parsed["BTC/USDT"]["signal"] == "buy_to_enter":
        print("✅ PASS: JSON parsed correctly")
    else:
        print(f"❌ FAIL: Parsing failed. Result: {parsed}")


if __name__ == "__main__":
    asyncio.run(test_monk_mode_service())
