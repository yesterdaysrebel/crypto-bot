from bot.config import EMA_FAST, EMA_SLOW, STOP_PCT, TAKE_PROFIT_R, VWAP_LOOKBACK
from bot.indicators import ema, vwap


def generate_signal(candles, price_override=None):
    if len(candles) < max(EMA_SLOW, VWAP_LOOKBACK) + 2:
        return None

    closes = [c["close"] for c in candles]
    opens = [c["open"] for c in candles]

    price = price_override if price_override is not None else closes[-1]
    ema_fast = ema(closes, EMA_FAST)
    ema_slow = ema(closes, EMA_SLOW)
    vwap_value = vwap(candles[-VWAP_LOOKBACK:])

    last_bull = closes[-1] > opens[-1]
    last_bear = closes[-1] < opens[-1]

    if price > vwap_value and ema_fast > ema_slow and last_bull:
        stop = price * (1.0 - STOP_PCT)
        target = price + (price - stop) * TAKE_PROFIT_R
        return {"side": "buy", "entry": price, "stop": stop, "target": target}

    if price < vwap_value and ema_fast < ema_slow and last_bear:
        stop = price * (1.0 + STOP_PCT)
        target = price - (stop - price) * TAKE_PROFIT_R
        return {"side": "sell", "entry": price, "stop": stop, "target": target}

    return None
