#!/usr/bin/env python3
"""
📊 0xBot Portfolio Status Tool
==============================
This script provides the REAL state of the portfolio from PostgreSQL.
USE THIS as the source of truth, NOT the logs.

Usage: python check_portfolio.py
"""

import os
import sys
from decimal import Decimal

# Add the backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def get_db_connection():
    """Get direct PostgreSQL connection."""
    import psycopg2

    db_url = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/trading_agent"
    )

    # Parse URL
    if db_url.startswith("postgresql://"):
        parts = db_url.replace("postgresql://", "").split("@")
        user_pass = parts[0].split(":")
        host_db = parts[1].split("/")
        host_port = host_db[0].split(":")

        return psycopg2.connect(
            host=host_port[0],
            port=int(host_port[1]) if len(host_port) > 1 else 5432,
            user=user_pass[0],
            password=user_pass[1] if len(user_pass) > 1 else "",
            database=host_db[1],
        )
    raise ValueError("Invalid DATABASE_URL")


def format_money(value):
    """Format as currency."""
    if value is None:
        return "$0.00"
    return f"${float(value):,.2f}"


def format_pct(value):
    """Format as percentage."""
    if value is None:
        return "0.00%"
    sign = "+" if value >= 0 else ""
    return f"{sign}{float(value):.2f}%"


def main():
    print("\n" + "=" * 60)
    print("📊 0xBot PORTFOLIO STATUS (from PostgreSQL - SOURCE OF TRUTH)")
    print("=" * 60)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get bot info
        print("\n🤖 BOT STATUS")
        print("-" * 40)
        cursor.execute(
            """
            SELECT id, name, status, capital, initial_capital,
                   created_at, updated_at
            FROM bots
            ORDER BY created_at DESC
            LIMIT 1
        """
        )
        bot = cursor.fetchone()

        if not bot:
            print("❌ No bot found in database!")
            return

        bot_id, name, status, capital, initial_capital, created_at, updated_at = bot
        profit = float(capital) - float(initial_capital)
        profit_pct = (profit / float(initial_capital)) * 100 if initial_capital else 0

        status_emoji = "🟢" if status == "ACTIVE" else "🔴" if status == "STOPPED" else "🟡"

        print(f"  Name:           {name}")
        print(f"  Status:         {status_emoji} {status}")
        print(f"  Initial:        {format_money(initial_capital)}")
        print(f"  Current:        {format_money(capital)}")
        print(f"  Profit/Loss:    {format_money(profit)} ({format_pct(profit_pct)})")
        print(f"  Updated:        {updated_at}")

        # Get open positions
        print("\n📈 OPEN POSITIONS")
        print("-" * 40)
        cursor.execute(
            """
            SELECT symbol, side, quantity, entry_price, current_price,
                   stop_loss, take_profit, leverage
            FROM positions
            WHERE bot_id = %s AND status = 'OPEN'
            ORDER BY opened_at DESC
        """,
            (bot_id,),
        )
        positions = cursor.fetchall()

        if not positions:
            print("  ✅ No open positions (all cash)")
        else:
            total_unrealized = 0
            for pos in positions:
                symbol, side, qty, entry, current, sl, tp, leverage = pos
                if current and entry and qty:
                    if side == "LONG":
                        pnl = float(qty) * (float(current) - float(entry))
                    else:
                        pnl = float(qty) * (float(entry) - float(current))
                    total_unrealized += pnl
                    pnl_emoji = "🟢" if pnl >= 0 else "🔴"
                    print(f"  {symbol} {side}")
                    print(f"    Entry: {format_money(entry)} | Current: {format_money(current)}")
                    print(f"    Qty: {float(qty):.6f} | PnL: {pnl_emoji} {format_money(pnl)}")
                    print(f"    SL: {format_money(sl)} | TP: {format_money(tp)}")
                    print()

            print(f"  Total Unrealized PnL: {format_money(total_unrealized)}")

        # Get recent closed positions
        print("\n📋 RECENT CLOSED TRADES (last 5)")
        print("-" * 40)
        cursor.execute(
            """
            SELECT symbol, side, quantity, entry_price, current_price, closed_at
            FROM positions
            WHERE bot_id = %s AND status = 'CLOSED'
            ORDER BY closed_at DESC
            LIMIT 5
        """,
            (bot_id,),
        )
        closed = cursor.fetchall()

        if not closed:
            print("  No closed trades yet")
        else:
            for pos in closed:
                symbol, side, qty, entry, exit_price, closed_at = pos
                if entry and exit_price and qty:
                    if side == "LONG":
                        pnl = float(qty) * (float(exit_price) - float(entry))
                    else:
                        pnl = float(qty) * (float(entry) - float(exit_price))
                    pnl_emoji = "🟢" if pnl >= 0 else "🔴"
                    print(f"  {symbol} {side}")
                    print(f"    Entry: {format_money(entry)} → Exit: {format_money(exit_price)}")
                    print(f"    PnL: {pnl_emoji} {format_money(pnl)} | Closed: {closed_at}")
                    print()

        # Get trade count
        cursor.execute(
            """
            SELECT COUNT(*) FROM trades WHERE bot_id = %s
        """,
            (bot_id,),
        )
        trade_count = cursor.fetchone()[0]

        # Get equity snapshots count
        cursor.execute(
            """
            SELECT COUNT(*), MIN(timestamp), MAX(timestamp)
            FROM equity_snapshots
            WHERE bot_id = %s
        """,
            (bot_id,),
        )
        snap_info = cursor.fetchone()

        print("\n📊 STATISTICS")
        print("-" * 40)
        print(f"  Total Trades:       {trade_count}")
        print(f"  Equity Snapshots:   {snap_info[0]}")
        if snap_info[1]:
            print(f"  First Snapshot:     {snap_info[1]}")
            print(f"  Last Snapshot:      {snap_info[2]}")

        conn.close()

        print("\n" + "=" * 60)
        print("✅ Data source: PostgreSQL database (trading_agent)")
        print("⚠️  DO NOT rely on llm_decisions.log for portfolio state!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nMake sure PostgreSQL is running and accessible.")
        sys.exit(1)


if __name__ == "__main__":
    main()
