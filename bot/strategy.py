from bot.config import (
    EMA_FAST,
    EMA_SLOW,
    TREND_EMA_PERIOD,
    STOP_PCT,
    TAKE_PROFIT_R,
    VWAP_LOOKBACK,
)
from bot.indicators import ema, vwap


def generate_signal(candles, price_override=None):
    min_len = max(EMA_SLOW, VWAP_LOOKBACK) + 2
    if TREND_EMA_PERIOD > 0:
        min_len = max(min_len, TREND_EMA_PERIOD + 2)
    if len(candles) < min_len:
        return None

    closes = [c["close"] for c in candles]
    opens = [c["open"] for c in candles]

    price = price_override if price_override is not None else closes[-1]
    ema_fast = ema(closes, EMA_FAST)
    ema_slow = ema(closes, EMA_SLOW)
    vwap_value = vwap(candles[-VWAP_LOOKBACK:])
    trend_ema = ema(closes, TREND_EMA_PERIOD) if TREND_EMA_PERIOD > 0 else None

    last_bull = closes[-1] > opens[-1]
    last_bear = closes[-1] < opens[-1]

    # Long: only when price is above trend EMA (don't buy in downtrends)
    if price > vwap_value and ema_fast > ema_slow and last_bull:
        if trend_ema is not None and price <= trend_ema:
            return None  # downtrend – skip long
        stop = price * (1.0 - STOP_PCT)
        target = price + (price - stop) * TAKE_PROFIT_R
        return {"side": "buy", "entry": price, "stop": stop, "target": target}

    # Short: only when price is below trend EMA (don't short in uptrends)
    if price < vwap_value and ema_fast < ema_slow and last_bear:
        if trend_ema is not None and price >= trend_ema:
            return None  # uptrend – skip short
        stop = price * (1.0 + STOP_PCT)
        target = price - (stop - price) * TAKE_PROFIT_R
        return {"side": "sell", "entry": price, "stop": stop, "target": target}

    return None
