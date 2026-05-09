from bot.config import (
    ATR_MULTIPLIER,
    ATR_PERIOD,
    BB_PERIOD,
    BB_STD_DEV,
    EMA_FAST,
    EMA_SLOW,
    RSI_OVERBOUGHT,
    RSI_OVERSOLD,
    RSI_PERIOD,
    TREND_EMA_PERIOD,
    STOP_PCT,
    TAKE_PROFIT_R,
    USE_BREAKOUT_STRATEGY,
    USE_REGIME_TREND,
    USE_MTF_REGIME,
    VWAP_LOOKBACK,
    VOLUME_SURGE_MULTIPLIER,
    REGIME_FAST_EMA,
    REGIME_SLOW_EMA,
    REGIME_PULLBACK_EMA,
    REGIME_ADX_PERIOD,
    REGIME_ADX_MIN,
    REGIME_ATR_PCT_MIN,
)
from bot.indicators import adx, atr, bollinger_bands, ema, rsi, vwap


def generate_signal_basic(candles, price_override=None):
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


def _regime_signal_with_reason(candles, price_override=None, trend_candles=None):
    """Regime-aware trend strategy with explicit rejection reasons."""
    required_entry_length = max(
        REGIME_PULLBACK_EMA,
        REGIME_ADX_PERIOD * 2,
        ATR_PERIOD,
        2,  # Need at least two bars for crossover/trigger checks.
    )
    if len(candles) < required_entry_length:
        return None, "no_regime_history"

    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]

    price = price_override if price_override is not None else closes[-1]
    last_close = closes[-1]
    prev_close = closes[-2]

    trend_source = trend_candles if trend_candles else candles
    trend_closes = [c["close"] for c in trend_source]
    if len(trend_closes) < REGIME_SLOW_EMA:
        return None, "no_trend_history"

    fast = ema(trend_closes, REGIME_FAST_EMA)
    slow = ema(trend_closes, REGIME_SLOW_EMA)
    pullback_ema = ema(closes, REGIME_PULLBACK_EMA)
    adx_value = adx(candles, REGIME_ADX_PERIOD)
    atr_value = atr(candles, ATR_PERIOD)

    if atr_value <= 0 or price <= 0:
        return None, "invalid_atr_or_price"

    atr_pct = (atr_value / price) * 100.0
    if adx_value < REGIME_ADX_MIN:
        return None, "adx_below_min"
    if atr_pct < REGIME_ATR_PCT_MIN:
        return None, "atr_pct_below_min"

    trend_ref_close = trend_closes[-1]
    trend_up = fast > slow and trend_ref_close > slow
    trend_down = fast < slow and trend_ref_close < slow

    # Entry trigger: reclaim/lose pullback EMA with momentum.
    long_trigger = prev_close <= pullback_ema and last_close > pullback_ema and last_close > highs[-2]
    short_trigger = prev_close >= pullback_ema and last_close < pullback_ema and last_close < lows[-2]

    stop_distance = atr_value * ATR_MULTIPLIER

    if trend_up and long_trigger:
        stop = price - stop_distance
        target = price + (stop_distance * TAKE_PROFIT_R)
        return {"side": "buy", "entry": price, "stop": stop, "target": target}, "signal_regime"

    if trend_down and short_trigger:
        stop = price + stop_distance
        target = price - (stop_distance * TAKE_PROFIT_R)
        return {"side": "sell", "entry": price, "stop": stop, "target": target}, "signal_regime"

    if trend_up or trend_down:
        return None, "pullback_trigger_not_met"
    return None, "trend_bias_not_set"


def generate_signal_regime_trend(candles, price_override=None, trend_candles=None):
    """Regime-aware trend strategy with volatility and pullback entries."""
    signal, _ = _regime_signal_with_reason(
        candles,
        price_override=price_override,
        trend_candles=trend_candles,
    )
    return signal


def _evaluate_basic(candles, price_override=None):
    signal = generate_signal_basic(candles, price_override=price_override)
    return signal, "signal_basic" if signal else "no_basic_setup"


def _evaluate_breakout(candles, price_override=None):
    signal = generate_signal_breakout(candles, price_override=price_override)
    return signal, "signal_breakout" if signal else "no_breakout_setup"


def _evaluate_regime(candles, price_override=None, trend_candles=None):
    signal, reason = _regime_signal_with_reason(
        candles,
        price_override=price_override,
        trend_candles=trend_candles,
    )
    return signal, reason


def evaluate_signal(candles, price_override=None, trend_candles=None):
    """Return (signal, reason) for analytics-friendly decision tracing."""
    if USE_MTF_REGIME:
        return _evaluate_regime(
            candles,
            price_override=price_override,
            trend_candles=trend_candles,
        )
    if USE_REGIME_TREND:
        return _evaluate_regime(candles, price_override=price_override)
    if USE_BREAKOUT_STRATEGY:
        return _evaluate_breakout(candles, price_override=price_override)
    return _evaluate_basic(candles, price_override=price_override)


def generate_signal(candles, price_override=None, trend_candles=None):
    """Main entry point - routes to appropriate strategy."""
    signal, _ = evaluate_signal(
        candles,
        price_override=price_override,
        trend_candles=trend_candles,
    )
    return signal
