#!/usr/bin/env python3
"""Utility script to reset the bot state file."""

import os
import sys
from pathlib import Path

# Add parent directory to path to import bot modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.config import STATE_FILE


def reset_state():
    """Reset the bot state file to default values."""
    state_file = Path(STATE_FILE)
    
    if state_file.exists():
        backup_file = state_file.with_suffix('.json.backup')
        state_file.rename(backup_file)
        print(f"Backed up existing state to: {backup_file}")
    
    # Create default state
    default_state = {
        "day": "",
        "week": "",
        "day_start_equity": 0.0,
        "week_start_equity": 0.0,
        "daily_trades": 0,
        "last_trade_ts": 0,
    }
    
    import json
    with open(state_file, "w", encoding="utf-8") as handle:
        json.dump(default_state, handle, indent=2)
    
    print(f"State file reset: {state_file}")
    print("Default state created:")
    for key, value in default_state.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    reset_state()
