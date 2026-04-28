import csv
import os
import time
from datetime import datetime

from bot.config import OUTCOMES_PATH


class OutcomeJournal:
    def __init__(self, path=OUTCOMES_PATH):
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
                    "closed_ts_local",
                    "symbol",
                    "mode",
                    "side",
                    "entry",
                    "exit",
                    "stop",
                    "target",
                    "size",
                    "result_r",
                    "pnl_pct",
                    "duration_seconds",
                    "exit_reason",
                ]
            )

    def log_close(self, symbol, mode, trade, exit_price, exit_reason):
        ts = datetime.now().astimezone().isoformat()
        side = trade["side"]
        entry = float(trade["entry"])
        stop = float(trade["stop"])
        target = float(trade["target"])
        size = float(trade["size"])
        opened_ts = int(trade.get("opened_ts") or int(time.time()))
        risk = abs(entry - stop)
        if risk <= 0:
            result_r = 0.0
        else:
            move = (exit_price - entry) if side == "buy" else (entry - exit_price)
            result_r = move / risk
        pnl_pct = ((exit_price - entry) / entry) * 100.0 if side == "buy" else ((entry - exit_price) / entry) * 100.0
        duration_seconds = max(0, int(time.time()) - opened_ts)

        with open(self.path, "a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    ts,
                    symbol,
                    mode,
                    side,
                    f"{entry:.8f}",
                    f"{exit_price:.8f}",
                    f"{stop:.8f}",
                    f"{target:.8f}",
                    f"{size:.8f}",
                    f"{result_r:.8f}",
                    f"{pnl_pct:.8f}",
                    duration_seconds,
                    exit_reason,
                ]
            )
