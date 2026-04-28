import csv
import os
from datetime import datetime

from bot.config import ANALYTICS_PATH


class AnalyticsLogger:
    def __init__(self, path=ANALYTICS_PATH):
        self.path = path
        self._ensure_header()

    def _ensure_header(self):
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        if os.path.exists(self.path):
            return
        with open(self.path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "ts_local",
                    "symbol",
                    "strategy",
                    "mode",
                    "event",
                    "reason",
                    "equity",
                    "price",
                    "side",
                    "entry",
                    "stop",
                    "target",
                    "size",
                    "signal_timeframe",
                    "trend_timeframe",
                ]
            )

    def log(
        self,
        symbol,
        strategy,
        mode,
        event,
        reason="",
        equity=None,
        price=None,
        side=None,
        entry=None,
        stop=None,
        target=None,
        size=None,
        signal_timeframe="",
        trend_timeframe="",
    ):
        ts = datetime.now().astimezone().isoformat()
        with open(self.path, "a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    ts,
                    symbol,
                    strategy,
                    mode,
                    event,
                    reason,
                    "" if equity is None else f"{equity:.8f}",
                    "" if price is None else f"{price:.8f}",
                    side or "",
                    "" if entry is None else f"{entry:.8f}",
                    "" if stop is None else f"{stop:.8f}",
                    "" if target is None else f"{target:.8f}",
                    "" if size is None else f"{size:.8f}",
                    signal_timeframe,
                    trend_timeframe,
                ]
            )
