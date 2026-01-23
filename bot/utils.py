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
                candles.append(
                    {
                        "time": item.get("time") or item.get("timestamp"),
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
    return candles
