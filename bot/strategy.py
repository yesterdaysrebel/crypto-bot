from bot.config import (
    EMA_FAST, EMA_SLOW, STOP_PCT, TAKE_PROFIT_R, VWAP_LOOKBACK,
    USE_ATR_STOPS, ATR_PERIOD, ATR_MULTIPLIER,
    RSI_PERIOD, RSI_OVERBOUGHT, RSI_OVERSOLD,
    BB_PERIOD, BB_STD_DEV, VOLUME_SURGE_MULTIPLIER,
    USE_BREAKOUT_STRATEGY
)
from bot.indicators import ema, vwap, atr, rsi, bollinger_bands


def generate_signal_basic(candles, price_override=None):
    """Original trend-following strategy with triple confirmation"""
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

    # Calculate stop loss (ATR-based or fixed percentage)
    if USE_ATR_STOPS:
        atr_value = atr(candles, ATR_PERIOD)
        stop_distance = atr_value * ATR_MULTIPLIER
    else:
        stop_distance = price * STOP_PCT

    if price > vwap_value and ema_fast > ema_slow and last_bull:
        stop = price - stop_distance
        target = price + stop_distance * TAKE_PROFIT_R
        return {"side": "buy", "entry": price, "stop": stop, "target": target}

    if price < vwap_value and ema_fast < ema_slow and last_bear:
        stop = price + stop_distance
        target = price - stop_distance * TAKE_PROFIT_R
        return {"side": "sell", "entry": price, "stop": stop, "target": target}

    return None


def generate_signal_breakout(candles, price_override=None):
    """Advanced breakout + momentum strategy for capturing big moves
    
    Strategy Logic:
    - Detects volatility squeeze (Bollinger Bands narrowing)
    - Confirms breakout with volume surge
    - Uses RSI to avoid overbought/oversold extremes
    - Employs ATR-based dynamic stops for volatile assets like SOL
    """
    required_length = max(EMA_SLOW, VWAP_LOOKBACK, BB_PERIOD, RSI_PERIOD, ATR_PERIOD) + 2
    if len(candles) < required_length:
        return None

    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    volumes = [c["volume"] for c in candles]

    price = price_override if price_override is not None else closes[-1]
    
    # Core indicators
    ema_fast = ema(closes, EMA_FAST)
    ema_slow = ema(closes, EMA_SLOW)
    vwap_value = vwap(candles[-VWAP_LOOKBACK:])
    rsi_value = rsi(closes, RSI_PERIOD)
    bb = bollinger_bands(closes, BB_PERIOD, BB_STD_DEV)
    atr_value = atr(candles, ATR_PERIOD)
    
    if not bb or atr_value == 0:
        return None
    
    # Volume analysis
    avg_volume = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
    current_volume = volumes[-1]
    volume_surge = current_volume > (avg_volume * VOLUME_SURGE_MULTIPLIER)
    
    # Bollinger Band squeeze detection (narrow bands = consolidation)
    bb_width_pct = (bb["width"] / bb["middle"]) * 100
    is_squeezed = bb_width_pct < 3.0  # Less than 3% width indicates squeeze
    
    # Calculate dynamic stop based on ATR
    stop_distance = atr_value * ATR_MULTIPLIER
    
    # LONG CONDITIONS (relaxed for better opportunity capture)
    # Core requirement: Strong trend OR clear breakout
    # Plus momentum confirmation
    
    # Option 1: Bollinger breakout with volume (squeeze not required)
    bb_breakout = price > bb["upper"] and volume_surge
    
    # Option 2: Strong trend (both EMA and VWAP aligned)
    strong_trend = ema_fast > ema_slow and price > vwap_value
    
    # Option 3: Moderate trend with volume (VWAP or EMA + volume)
    moderate_trend = (ema_fast > ema_slow or price > vwap_value) and volume_surge
    
    # Momentum check (avoid extreme overbought only)
    momentum_ok = rsi_value < RSI_OVERBOUGHT  # Allow oversold (can bounce hard)
    
    # Enter if ANY strong condition + momentum check
    if (bb_breakout or strong_trend or moderate_trend) and momentum_ok:
        stop = price - stop_distance
        target = price + stop_distance * TAKE_PROFIT_R
        return {"side": "buy", "entry": price, "stop": stop, "target": target}
    
    # SHORT CONDITIONS (same relaxed logic inverted)
    
    # Option 1: Bollinger breakdown with volume
    bb_breakdown = price < bb["lower"] and volume_surge
    
    # Option 2: Strong downtrend (both EMA and VWAP aligned)
    strong_downtrend = ema_fast < ema_slow and price < vwap_value
    
    # Option 3: Moderate downtrend with volume
    moderate_downtrend = (ema_fast < ema_slow or price < vwap_value) and volume_surge
    
    # Momentum check (avoid extreme oversold only)
    momentum_ok_short = rsi_value > RSI_OVERSOLD  # Allow overbought (can dump hard)
    
    # Enter if ANY strong condition + momentum check
    if (bb_breakdown or strong_downtrend or moderate_downtrend) and momentum_ok_short:
        stop = price + stop_distance
        target = price - stop_distance * TAKE_PROFIT_R
        return {"side": "sell", "entry": price, "stop": stop, "target": target}
    
    return None


def generate_signal(candles, price_override=None):
    """Main entry point - routes to appropriate strategy"""
    if USE_BREAKOUT_STRATEGY:
        return generate_signal_breakout(candles, price_override)
    else:
        return generate_signal_basic(candles, price_override)
