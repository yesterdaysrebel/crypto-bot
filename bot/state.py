import json
import os
import time
from datetime import date

from bot.config import STATE_FILE


class BotState:
    def __init__(self, state_file=STATE_FILE):
        self.state_file = state_file
        self.state = self._load()

    def _load(self):
        try:
            with open(self.state_file, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return {
                "day": "",
                "week": "",
                "day_start_equity": 0.0,
                "week_start_equity": 0.0,
                "daily_trades": 0,
                "last_trade_ts": 0,
                "open_paper_trade": None,
                "live_trade_plan": None,
            }

    def _save(self):
        temp_file = f"{self.state_file}.tmp"
        with open(temp_file, "w", encoding="utf-8") as handle:
            json.dump(self.state, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_file, self.state_file)

    def rollover(self, equity):
        today = str(date.today())
        week = f"{date.today().isocalendar().year}-W{date.today().isocalendar().week}"

        if self.state["day"] != today:
            self.state["day"] = today
            self.state["day_start_equity"] = equity
            self.state["daily_trades"] = 0

        if self.state["week"] != week:
            self.state["week"] = week
            self.state["week_start_equity"] = equity

        self._save()

    def record_trade(self):
        self.state["daily_trades"] = int(self.state.get("daily_trades", 0)) + 1
        self.state["last_trade_ts"] = int(time.time())
        self._save()

    def daily_loss_pct(self, equity):
        start = float(self.state.get("day_start_equity") or equity)
        return (start - equity) / start if start else 0.0

    def weekly_loss_pct(self, equity):
        start = float(self.state.get("week_start_equity") or equity)
        return (start - equity) / start if start else 0.0

    def drawdown_pct(self, equity):
        week_start = float(self.state.get("week_start_equity") or equity)
        return (week_start - equity) / week_start if week_start else 0.0

    def can_trade_cooldown(self, min_seconds_between_trades):
        last_ts = int(self.state.get("last_trade_ts") or 0)
        return (int(time.time()) - last_ts) >= min_seconds_between_trades

    def get_open_paper_trade(self):
        return self.state.get("open_paper_trade")

    def set_open_paper_trade(self, trade):
        self.state["open_paper_trade"] = trade
        self._save()

    def clear_open_paper_trade(self):
        self.state["open_paper_trade"] = None
        self._save()

    def get_live_trade_plan(self):
        return self.state.get("live_trade_plan")

    def set_live_trade_plan(self, trade_plan):
        self.state["live_trade_plan"] = trade_plan
        self._save()

    def clear_live_trade_plan(self):
        self.state["live_trade_plan"] = None
        self._save()
