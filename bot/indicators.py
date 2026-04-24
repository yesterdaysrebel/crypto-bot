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


def atr(candles, period=14):
    """Calculate Average True Range for volatility-based stops"""
    if len(candles) < period + 1:
        return 0.0
    
    true_ranges = []
    for i in range(1, len(candles)):
        high = candles[i]["high"]
        low = candles[i]["low"]
        prev_close = candles[i - 1]["close"]
        
        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )
        true_ranges.append(tr)
    
    # Use EMA for ATR calculation
    if len(true_ranges) < period:
        return sum(true_ranges) / len(true_ranges)
    
    return ema(true_ranges[-period:], period)


def rsi(values, period=14):
    """Calculate Relative Strength Index for momentum"""
    if len(values) < period + 1:
        return 50.0
    
    gains = []
    losses = []
    
    for i in range(1, len(values)):
        change = values[i] - values[i - 1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    if len(gains) < period:
        return 50.0
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi_value = 100.0 - (100.0 / (1.0 + rs))
    return rsi_value


def bollinger_bands(values, period=20, std_dev=2.0):
    """Calculate Bollinger Bands for volatility and breakouts"""
    if len(values) < period:
        return None
    
    recent = values[-period:]
    sma = sum(recent) / period
    
    variance = sum((x - sma) ** 2 for x in recent) / period
    std = variance ** 0.5
    
    upper = sma + (std_dev * std)
    lower = sma - (std_dev * std)
    
    return {"upper": upper, "middle": sma, "lower": lower, "width": upper - lower}


def adx(candles, period=14):
    """Calculate Average Directional Index (trend strength, 0-100)."""
    if len(candles) < (period * 2):
        return 0.0

    trs = []
    plus_dm = []
    minus_dm = []

    for i in range(1, len(candles)):
        high = candles[i]["high"]
        low = candles[i]["low"]
        prev_high = candles[i - 1]["high"]
        prev_low = candles[i - 1]["low"]
        prev_close = candles[i - 1]["close"]

        up_move = high - prev_high
        down_move = prev_low - low

        pdm = up_move if up_move > down_move and up_move > 0 else 0.0
        mdm = down_move if down_move > up_move and down_move > 0 else 0.0

        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close),
        )

        trs.append(tr)
        plus_dm.append(pdm)
        minus_dm.append(mdm)

    if len(trs) < period:
        return 0.0

    tr_smooth = sum(trs[:period])
    plus_smooth = sum(plus_dm[:period])
    minus_smooth = sum(minus_dm[:period])

    dx_values = []
    for i in range(period, len(trs)):
        tr_smooth = tr_smooth - (tr_smooth / period) + trs[i]
        plus_smooth = plus_smooth - (plus_smooth / period) + plus_dm[i]
        minus_smooth = minus_smooth - (minus_smooth / period) + minus_dm[i]

        if tr_smooth == 0:
            dx_values.append(0.0)
            continue

        plus_di = (plus_smooth / tr_smooth) * 100.0
        minus_di = (minus_smooth / tr_smooth) * 100.0
        di_sum = plus_di + minus_di

        if di_sum == 0:
            dx_values.append(0.0)
            continue

        dx = (abs(plus_di - minus_di) / di_sum) * 100.0
        dx_values.append(dx)

    if not dx_values:
        return 0.0

    return ema(dx_values, period)
