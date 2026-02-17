#!/usr/bin/env python3
"""Utility script to check the current bot state."""

import json
import sys
import time
from datetime import date
from pathlib import Path

# Add parent directory to path to import bot modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.config import STATE_FILE, MIN_SECONDS_BETWEEN_TRADES, MAX_TRADES_PER_DAY


def check_state():
    """Display the current bot state."""
    state_file = Path(STATE_FILE)
    
    if not state_file.exists():
        print(f"State file not found: {state_file}")
        print("Bot will create a new state file on first run.")
        return
    
    with open(state_file, "r", encoding="utf-8") as handle:
        state = json.load(handle)
    
    print(f"State file: {state_file}")
    print("\nCurrent State:")
    print(f"  Day: {state.get('day', 'N/A')}")
    print(f"  Week: {state.get('week', 'N/A')}")
    print(f"  Day Start Equity: {state.get('day_start_equity', 0.0)}")
    print(f"  Week Start Equity: {state.get('week_start_equity', 0.0)}")
    print(f"  Daily Trades: {state.get('daily_trades', 0)}")
    
    last_trade_ts = int(state.get('last_trade_ts', 0))
    if last_trade_ts > 0:
        elapsed = int(time.time()) - last_trade_ts
        remaining = max(0, MIN_SECONDS_BETWEEN_TRADES - elapsed)
        print(f"  Last Trade Timestamp: {last_trade_ts} ({elapsed} seconds ago)")
        if remaining > 0:
            print(f"  Cooldown Remaining: {remaining} seconds ({remaining // 60} minutes)")
        else:
            print(f"  Cooldown: Complete (ready to trade)")
    else:
        print(f"  Last Trade Timestamp: Never")
        print(f"  Cooldown: Ready to trade")
    
    daily_trades = int(state.get('daily_trades', 0))
    today = str(date.today())
    if state.get('day') == today:
        print(f"\nToday's Status:")
        print(f"  Trades today: {daily_trades} / {MAX_TRADES_PER_DAY}")
        if daily_trades >= MAX_TRADES_PER_DAY:
            print(f"  ⚠️  MAX_TRADES_PER_DAY limit reached!")
    else:
        print(f"\nToday's Status:")
        print(f"  State is from a different day ({state.get('day')})")
        print(f"  Will reset on next bot run")


if __name__ == "__main__":
    check_state()
