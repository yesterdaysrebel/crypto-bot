import time


def timeframe_seconds(timeframe):
    if not isinstance(timeframe, str) or len(timeframe) < 2:
        return 0
    suffix = timeframe[-1].lower()
    try:
        amount = int(timeframe[:-1])
    except (TypeError, ValueError):
        return 0
    if suffix == "m":
        return amount * 60
    if suffix == "h":
        return amount * 3600
    if suffix == "d":
        return amount * 86400
    return 0


def drop_in_progress_bar(candles, timeframe, now=None):
    if not candles:
        return candles
    secs = timeframe_seconds(timeframe)
    if secs <= 0:
        return candles
    last_open = candles[-1].get("time")
    if last_open is None:
        return candles
    try:
        last_open = int(last_open)
    except (TypeError, ValueError):
        return candles
    current = int(now if now is not None else time.time())
    if current < last_open + secs:
        return candles[:-1]
    return candles


def normalize_candles(raw):
    if raw is None:
        return []

    if isinstance(raw, dict):
        data = raw.get("result") or raw.get("candles") or raw.get("data") or []
    else:
        data = raw

    candles = []
    for item in data:
        if isinstance(item, dict):
            try:
                time_value = item.get("time")
                if time_value is None:
                    time_value = item.get("timestamp")
                candles.append(
                    {
                        "time": time_value,
                        "open": float(item["open"]),
                        "high": float(item.get("high", item["open"])),
                        "low": float(item.get("low", item["open"])),
                        "close": float(item["close"]),
                        "volume": float(item.get("volume", 0)),
                    }
                )
            except Exception:
                continue
        elif isinstance(item, (list, tuple)) and len(item) >= 6:
            try:
                candles.append(
                    {
                        "time": item[0],
                        "open": float(item[1]),
                        "high": float(item[2]),
                        "low": float(item[3]),
                        "close": float(item[4]),
                        "volume": float(item[5]),
                    }
                )
            except Exception:
                continue

    # Delta candles endpoint returns descending time order, but every recurrence-
    # based indicator (EMA, ADX, ATR, RSI, BB) requires ascending time. Sort
    # defensively here so the live bot, replay tools, and tests share one
    # canonical orientation regardless of upstream API behavior. Bars with an
    # unparseable timestamp are dropped: passing them through unsorted would
    # silently corrupt every downstream indicator.
    sortable = []
    for candle in candles:
        try:
            sortable.append((int(candle["time"]), candle))
        except (TypeError, ValueError):
            continue
    sortable.sort(key=lambda pair: pair[0])
    return [candle for _, candle in sortable]
