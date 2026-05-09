from bot.strategy import _regime_signal_with_reason


def _bar(t, c):
    return {"time": t, "open": c, "high": c + 0.5, "low": c - 0.5, "close": c, "volume": 100.0}


def test_regime_returns_no_regime_history_when_entry_candles_too_short():
    candles = [_bar(i * 3600, 100.0) for i in range(5)]
    trend = [_bar(i * 14400, 100.0) for i in range(220)]
    sig, reason = _regime_signal_with_reason(candles, trend_candles=trend)
    assert sig is None
    assert reason == "no_regime_history"


def test_regime_evaluates_with_exactly_200_entry_candles_and_trend_candles():
    """Delta returns max 200 candles per call. Strategy must be able to evaluate at that boundary."""
    candles = [_bar(i * 3600, 100.0 + i * 0.01) for i in range(200)]
    trend = [_bar(i * 14400, 100.0 + i * 0.01) for i in range(200)]
    sig, reason = _regime_signal_with_reason(candles, trend_candles=trend)
    assert reason != "no_regime_history"
    assert reason != "no_trend_history"


def test_regime_returns_no_trend_history_when_trend_candles_short_in_mtf_mode():
    candles = [_bar(i * 3600, 100.0) for i in range(200)]
    trend = [_bar(i * 14400, 100.0) for i in range(50)]
    sig, reason = _regime_signal_with_reason(candles, trend_candles=trend)
    assert sig is None
    assert reason == "no_trend_history"
