import csv
import os
from datetime import datetime, timezone

from bot.config import JOURNAL_PATH, LOG_TRADES


class TradeJournal:
    def __init__(self, path=JOURNAL_PATH):
        self.path = path
        self._ensure_header()

    def _ensure_header(self):
        if not LOG_TRADES:
            return
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        if os.path.exists(self.path):
            return
        with open(self.path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "ts_utc",
                    "symbol",
                    "product_id",
                    "side",
                    "entry",
                    "stop",
                    "target",
                    "size",
                    "mode",
                    "note",
                ]
            )

    def log(self, symbol, product_id, side, entry, stop, target, size, mode, note=""):
        if not LOG_TRADES:
            return
        ts = datetime.now(timezone.utc).isoformat()
        with open(self.path, "a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    ts,
                    symbol,
                    product_id,
                    side,
                    f"{entry:.8f}",
                    f"{stop:.8f}",
                    f"{target:.8f}",
                    f"{size:.8f}",
                    mode,
                    note,
                ]
            )
