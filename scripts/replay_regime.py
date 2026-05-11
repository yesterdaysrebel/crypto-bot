#!/usr/bin/env python3
"""Replay the mtf_regime strategy over recent history to answer:
"did the May 9 tightening (ADX_MIN 20->22, ATR%_MIN 0.2->0.8) turn the bot off?"

Walks 1h candles bar-by-bar (with 4h trend candles truncated to no-lookahead),
captures the per-bar gate inputs (ADX, ATR%, trend bias, pullback triggers),
then runs an offline parameter sweep over (REGIME_ADX_MIN, REGIME_ATR_PCT_MIN).

Usage:
    python scripts/replay_regime.py                  # 60 days, current symbol
    python scripts/replay_regime.py --days 30
    python scripts/replay_regime.py --symbol SOLUSD --days 90

No API keys required: the Delta candles endpoint is public.
"""
from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.config import (
    ATR_MULTIPLIER,
    ATR_PERIOD,
    CANDLE_LIMIT,
    ENTRY_TIMEFRAME,
    REGIME_ADX_MIN,
    REGIME_ADX_PERIOD,
    REGIME_ATR_PCT_MIN,
    REGIME_FAST_EMA,
    REGIME_PULLBACK_EMA,
    REGIME_SLOW_EMA,
    SYMBOL,
    TAKE_PROFIT_R,
    TREND_TIMEFRAME,
)
from bot.delta_client import DeltaApi
from bot.indicators import adx, atr, ema
from bot.utils import drop_in_progress_bar, normalize_candles, timeframe_seconds


def fetch_history(api: DeltaApi, symbol: str, resolution: str, limit: int) -> list[dict]:
    """Fetch candles and drop the in-progress final bar."""
    raw = api.get_candles(symbol, resolution, limit)
    candles = normalize_candles(raw)
    candles = drop_in_progress_bar(candles, resolution)
    candles.sort(key=lambda c: int(c["time"]))
    return candles


def percentiles(values: list[float], quantiles=(5, 25, 50, 75, 90, 95)) -> dict[int, float]:
    if not values:
        return {q: float("nan") for q in quantiles}
    sorted_vals = sorted(values)
    out = {}
    for q in quantiles:
        idx = int(round((q / 100.0) * (len(sorted_vals) - 1)))
        out[q] = sorted_vals[idx]
    return out


def evaluate_bar(signal_window: list[dict], trend_window: list[dict]) -> dict | None:
    """Recompute the exact gate inputs used by _regime_signal_with_reason
    for a single bar. Returns None if there isn't enough warmup history yet.
    """
    if len(signal_window) < max(REGIME_PULLBACK_EMA, REGIME_ADX_PERIOD * 2, ATR_PERIOD, 2):
        return None
    if len(trend_window) < REGIME_SLOW_EMA:
        return None

    closes = [c["close"] for c in signal_window]
    highs = [c["high"] for c in signal_window]
    lows = [c["low"] for c in signal_window]
    trend_closes = [c["close"] for c in trend_window]

    price = closes[-1]
    last_close = closes[-1]
    prev_close = closes[-2]

    fast = ema(trend_closes, REGIME_FAST_EMA)
    slow = ema(trend_closes, REGIME_SLOW_EMA)
    pullback_ema_val = ema(closes, REGIME_PULLBACK_EMA)
    adx_val = adx(signal_window, REGIME_ADX_PERIOD)
    atr_val = atr(signal_window, ATR_PERIOD)
    if atr_val <= 0 or price <= 0:
        return None
    atr_pct = (atr_val / price) * 100.0

    trend_ref_close = trend_closes[-1]
    trend_up = fast > slow and trend_ref_close > slow
    trend_down = fast < slow and trend_ref_close < slow

    long_trigger = (
        prev_close <= pullback_ema_val
        and last_close > pullback_ema_val
        and last_close > highs[-2]
    )
    short_trigger = (
        prev_close >= pullback_ema_val
        and last_close < pullback_ema_val
        and last_close < lows[-2]
    )

    return {
        "time": int(signal_window[-1]["time"]),
        "close": price,
        "adx": adx_val,
        "atr_pct": atr_pct,
        "trend_up": trend_up,
        "trend_down": trend_down,
        "long_trigger": long_trigger,
        "short_trigger": short_trigger,
    }


def classify(row: dict, adx_min: float, atr_pct_min: float) -> str:
    """Reproduce the gate ordering in _regime_signal_with_reason."""
    if row["adx"] < adx_min:
        return "adx_below_min"
    if row["atr_pct"] < atr_pct_min:
        return "atr_pct_below_min"
    if row["trend_up"]:
        return "signal_long" if row["long_trigger"] else "pullback_trigger_not_met"
    if row["trend_down"]:
        return "signal_short" if row["short_trigger"] else "pullback_trigger_not_met"
    return "trend_bias_not_set"


def sweep(rows: list[dict], adx_grid: list[float], atr_grid: list[float]) -> list[dict]:
    """Run a (ADX_MIN, ATR_PCT_MIN) grid over the captured rows."""
    out = []
    for adx_min in adx_grid:
        for atr_pct_min in atr_grid:
            counts = Counter(classify(r, adx_min, atr_pct_min) for r in rows)
            signals = counts.get("signal_long", 0) + counts.get("signal_short", 0)
            out.append(
                {
                    "adx_min": adx_min,
                    "atr_pct_min": atr_pct_min,
                    "signals": signals,
                    "signal_long": counts.get("signal_long", 0),
                    "signal_short": counts.get("signal_short", 0),
                    "rejections": counts,
                }
            )
    return out


def fmt_ts(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--symbol", default=SYMBOL, help=f"Symbol to replay (default: {SYMBOL})")
    parser.add_argument("--days", type=int, default=60, help="Days of 1h history to evaluate (default: 60)")
    parser.add_argument(
        "--entry-tf",
        default=ENTRY_TIMEFRAME,
        help=f"Entry timeframe (default: {ENTRY_TIMEFRAME})",
    )
    parser.add_argument(
        "--trend-tf",
        default=TREND_TIMEFRAME,
        help=f"Trend timeframe (default: {TREND_TIMEFRAME})",
    )
    parser.add_argument(
        "--adx-min",
        type=float,
        default=None,
        help=f"Override REGIME_ADX_MIN for the histogram (default from config: {REGIME_ADX_MIN})",
    )
    parser.add_argument(
        "--atr-pct-min",
        type=float,
        default=None,
        help=f"Override REGIME_ATR_PCT_MIN for the histogram (default from config: {REGIME_ATR_PCT_MIN})",
    )
    args = parser.parse_args()

    adx_min_active = REGIME_ADX_MIN if args.adx_min is None else args.adx_min
    atr_pct_min_active = REGIME_ATR_PCT_MIN if args.atr_pct_min is None else args.atr_pct_min
    overridden = args.adx_min is not None or args.atr_pct_min is not None

    entry_secs = timeframe_seconds(args.entry_tf)
    trend_secs = timeframe_seconds(args.trend_tf)
    if entry_secs <= 0 or trend_secs <= 0:
        print(f"ERROR: cannot parse timeframes ({args.entry_tf}, {args.trend_tf})", file=sys.stderr)
        return 2

    # Warmup: we need REGIME_SLOW_EMA bars before the first evaluable bar.
    eval_bars = int(args.days * 86400 / entry_secs)
    entry_warmup = max(REGIME_SLOW_EMA, REGIME_ADX_PERIOD * 4)
    entry_limit = eval_bars + entry_warmup + 5

    # Trend candles must cover the same wall-clock window plus REGIME_SLOW_EMA warmup.
    trend_bars_needed = int(args.days * 86400 / trend_secs)
    trend_limit = trend_bars_needed + REGIME_SLOW_EMA + 5

    # Most Delta endpoints cap a single request at ~2000 bars.
    entry_limit = min(entry_limit, 2000)
    trend_limit = min(trend_limit, 2000)

    print(f"Replaying {args.symbol} {args.entry_tf}/{args.trend_tf} for ~{args.days}d "
          f"(entry_limit={entry_limit}, trend_limit={trend_limit})")
    print(f"Strategy params: REGIME_FAST_EMA={REGIME_FAST_EMA} REGIME_SLOW_EMA={REGIME_SLOW_EMA} "
          f"PULLBACK_EMA={REGIME_PULLBACK_EMA} ADX_PERIOD={REGIME_ADX_PERIOD} "
          f"ATR_PERIOD={ATR_PERIOD} ATR_MULT={ATR_MULTIPLIER} TP_R={TAKE_PROFIT_R}")
    label = "Override" if overridden else "Live config"
    print(f"{label}:    REGIME_ADX_MIN={adx_min_active}  REGIME_ATR_PCT_MIN={atr_pct_min_active}")
    if overridden:
        print(f"(config defaults: REGIME_ADX_MIN={REGIME_ADX_MIN}  REGIME_ATR_PCT_MIN={REGIME_ATR_PCT_MIN})")
    print()

    api = DeltaApi()
    t0 = time.time()
    entry_candles = fetch_history(api, args.symbol, args.entry_tf, entry_limit)
    trend_candles = fetch_history(api, args.symbol, args.trend_tf, trend_limit)
    print(f"Fetched {len(entry_candles)} {args.entry_tf} candles and "
          f"{len(trend_candles)} {args.trend_tf} candles in {time.time() - t0:.1f}s")
    if not entry_candles or not trend_candles:
        print("ERROR: no candles returned", file=sys.stderr)
        return 1
    print(f"Entry range: {fmt_ts(int(entry_candles[0]['time']))}  ->  "
          f"{fmt_ts(int(entry_candles[-1]['time']))}")
    print(f"Trend range: {fmt_ts(int(trend_candles[0]['time']))}  ->  "
          f"{fmt_ts(int(trend_candles[-1]['time']))}\n")

    # Bar-by-bar walk. At each entry bar t, trend window = 4h candles whose
    # close (= time + 4h) is <= entry candle's close, so no lookahead.
    rows: list[dict] = []
    trend_idx = 0
    for i in range(REGIME_SLOW_EMA, len(entry_candles)):
        entry_close_ts = int(entry_candles[i]["time"]) + entry_secs
        while (
            trend_idx < len(trend_candles)
            and int(trend_candles[trend_idx]["time"]) + trend_secs <= entry_close_ts
        ):
            trend_idx += 1
        trend_window = trend_candles[:trend_idx]
        signal_window = entry_candles[: i + 1]

        row = evaluate_bar(signal_window, trend_window)
        if row is not None:
            rows.append(row)

    if not rows:
        print("ERROR: no evaluable bars (need more history)", file=sys.stderr)
        return 1

    print(f"Evaluable bars: {len(rows)}  ({fmt_ts(rows[0]['time'])}  ->  {fmt_ts(rows[-1]['time'])})\n")

    # -- Distribution diagnostics ------------------------------------------------
    adx_pcts = percentiles([r["adx"] for r in rows])
    atr_pcts = percentiles([r["atr_pct"] for r in rows])
    print("ADX percentiles (1h):")
    for q in sorted(adx_pcts):
        print(f"  p{q:>2}: {adx_pcts[q]:6.2f}")
    print("\nATR% percentiles (1h):")
    for q in sorted(atr_pcts):
        print(f"  p{q:>2}: {atr_pcts[q]:6.3f}%")
    print()

    trend_up_pct = 100.0 * sum(1 for r in rows if r["trend_up"]) / len(rows)
    trend_down_pct = 100.0 * sum(1 for r in rows if r["trend_down"]) / len(rows)
    print(f"Trend bias on bars: up={trend_up_pct:.1f}%  down={trend_down_pct:.1f}%  "
          f"flat={100 - trend_up_pct - trend_down_pct:.1f}%\n")

    # -- Active-config rejection histogram ---------------------------------------
    counts = Counter(classify(r, adx_min_active, atr_pct_min_active) for r in rows)
    config_label = "OVERRIDE" if overridden else "LIVE"
    print(f"Rejection histogram at {config_label} config (ADX_MIN={adx_min_active}, "
          f"ATR%_MIN={atr_pct_min_active}):")
    for reason, n in counts.most_common():
        pct = 100.0 * n / len(rows)
        print(f"  {reason:<28} {n:>5}  ({pct:5.1f}%)")
    signals_live = counts.get("signal_long", 0) + counts.get("signal_short", 0)
    days_span = (rows[-1]["time"] - rows[0]["time"]) / 86400.0
    rate = (signals_live / days_span) if days_span > 0 else 0.0
    print(f"\n  -> {signals_live} would-be signals over {days_span:.1f} days "
          f"({rate:.2f}/day, ~1 per {(1 / rate if rate > 0 else float('inf')):.1f} days)\n")

    # -- Parameter sweep ---------------------------------------------------------
    adx_grid = sorted({12.0, 15.0, 18.0, 20.0, 22.0, 25.0, float(adx_min_active)})
    atr_grid = sorted({0.1, 0.2, 0.3, 0.5, 0.8, 1.2, float(atr_pct_min_active)})
    results = sweep(rows, adx_grid, atr_grid)

    print(f"Signal-count sweep (rows = ADX_MIN, cols = ATR%_MIN) over {days_span:.1f} days:")
    header = "ADX_MIN \\ ATR%_MIN | " + " ".join(f"{a:>6.2f}" for a in atr_grid)
    print(header)
    print("-" * len(header))
    for adx_min in adx_grid:
        row_cells = []
        for atr_pct_min in atr_grid:
            n = next(
                r["signals"]
                for r in results
                if r["adx_min"] == adx_min and r["atr_pct_min"] == atr_pct_min
            )
            row_cells.append(f"{n:>6d}")
        marker = f"  <- {'override' if overridden else 'active'}" if adx_min == adx_min_active else ""
        print(f"            {adx_min:>6.1f} | " + " ".join(row_cells) + marker)
    print()
    print("Tip: pick a cell whose count gives you ~2-6 signals/month, then confirm")
    print("by reading the per-bar ADX/ATR% percentiles above to ensure the chosen")
    print("thresholds aren't on a knife edge of the distribution.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
