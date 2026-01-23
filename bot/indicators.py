def ema(values, period):
    if not values:
        return 0.0
    k = 2.0 / (period + 1.0)
    ema_value = values[0]
    for value in values[1:]:
        ema_value = value * k + ema_value * (1.0 - k)
    return ema_value


def vwap(candles):
    if not candles:
        return 0.0
    pv = 0.0
    vol = 0.0
    for candle in candles:
        price = candle["close"]
        volume = candle["volume"]
        pv += price * volume
        vol += volume
    return pv / vol if vol else candles[-1]["close"]
