from bot.utils import drop_in_progress_bar, timeframe_seconds


def test_timeframe_seconds_known_values():
    assert timeframe_seconds("1m") == 60
    assert timeframe_seconds("15m") == 900
    assert timeframe_seconds("1h") == 3600
    assert timeframe_seconds("4h") == 14400
    assert timeframe_seconds("1d") == 86400


def test_timeframe_seconds_invalid_inputs_return_zero():
    assert timeframe_seconds("") == 0
    assert timeframe_seconds("xyz") == 0
    assert timeframe_seconds(None) == 0
    assert timeframe_seconds(60) == 0


def _bar(open_ts, close=100.0):
    return {"time": open_ts, "open": close, "high": close, "low": close, "close": close, "volume": 1.0}


def test_drop_in_progress_bar_drops_when_bar_still_open():
    candles = [_bar(0), _bar(3600), _bar(7200)]
    # now is 30 minutes into the third bar (still open)
    result = drop_in_progress_bar(candles, "1h", now=7200 + 1800)
    assert len(result) == 2
    assert result[-1]["time"] == 3600


def test_drop_in_progress_bar_keeps_when_bar_already_closed():
    candles = [_bar(0), _bar(3600), _bar(7200)]
    # now is 1 second after bar #3 closed
    result = drop_in_progress_bar(candles, "1h", now=7200 + 3601)
    assert len(result) == 3


def test_drop_in_progress_bar_handles_empty_and_unparseable_tf():
    assert drop_in_progress_bar([], "1h", now=0) == []
    candles = [_bar(0)]
    assert drop_in_progress_bar(candles, "junk", now=0) == candles
