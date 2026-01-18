#!/usr/bin/env python3
"""Test the exact flow that the orchestrator uses."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from src.blocks.block_market_data import MarketDataBlock

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

async def test():
    """Test market data block with paper_trading=False."""
    print("=" * 80)
    print("TESTING ORCHESTRATOR FLOW")
    print("=" * 80)

    # This is exactly what happens in TradingOrchestrator.__init__
    market_data_block = MarketDataBlock(paper_trading=False)

    print(f"\n1. MarketDataBlock initialized with paper_trading=False")
    print(f"   Exchange: {market_data_block.exchange}")
    print(f"   Symbols: {market_data_block.symbols}")

    # This is what happens in _run_cycle
    print(f"\n2. Calling fetch_all()...")
    snapshots = await market_data_block.fetch_all()

    if snapshots:
        print(f"✓ SUCCESS: Fetched data for {len(snapshots)} symbols")
        for symbol, snapshot in list(snapshots.items())[:2]:
            print(f"   {symbol}: ${snapshot.price}")
    else:
        print(f"✗ FAILURE: No snapshots returned")

    print(f"\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(test())
