import asyncio
import json
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.services.monk_mode_service import MonkModePromptService


def test_reflection_logging():
    print("🧪 Testing Reflection Logging...")

    service = MonkModePromptService()

    # Mock LLM Response with Chain of Thought
    mock_response = {
        "CHAIN_OF_THOUGHT": [
            "1. Market Analysis: BTC is bullish.",
            "2. Hypothesis: Trend continuation.",
            "3. Decision: Buy BTC.",
        ],
        "BTC/USDT": {"signal": "buy", "quantity": 0.1},
    }

    response_text = json.dumps(mock_response)

    # Parse response (should trigger logging)
    print("📝 Parsing response...")
    service.parse_monk_mode_response(response_text, target_symbols=["BTC/USDT"])

    # Verify File Creation
    log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "monk_thoughts.md")

    print(f"🔍 Checking log file: {log_file}")
    if os.path.exists(log_file):
        print("✅ Log file exists")
        with open(log_file, "r") as f:
            content = f.read()
            print("\n📄 File Content Snippet:")
            print(content[-200:])  # Print last 200 chars

            if "1. Market Analysis: BTC is bullish." in content:
                print("✅ Reflection found in file")
            else:
                print("❌ Reflection NOT found in file")
    else:
        print("❌ Log file does NOT exist")


if __name__ == "__main__":
    test_reflection_logging()
