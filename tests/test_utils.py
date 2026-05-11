from bot.utils import drop_in_progress_bar, normalize_candles, timeframe_seconds


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


def test_normalize_candles_sorts_descending_input_ascending():
    # Mirrors Delta's actual response shape: newest bar first.
    raw = [
        {"time": 7200, "open": 3, "high": 3, "low": 3, "close": 3, "volume": 1},
        {"time": 3600, "open": 2, "high": 2, "low": 2, "close": 2, "volume": 1},
        {"time": 0,    "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1},
    ]
    result = normalize_candles(raw)
    assert [c["time"] for c in result] == [0, 3600, 7200]
    assert [c["close"] for c in result] == [1.0, 2.0, 3.0]


def test_normalize_candles_handles_list_form_and_mixed_order():
    raw = [
        [3600, 2, 2, 2, 2, 1],
        [0,    1, 1, 1, 1, 1],
        [7200, 3, 3, 3, 3, 1],
    ]
    result = normalize_candles(raw)
    assert [int(c["time"]) for c in result] == [0, 3600, 7200]


def test_normalize_candles_drops_bars_with_unsortable_time():
    # Bars with an unparseable timestamp would silently break ascending-order
    # invariants for every downstream indicator, so we drop them instead of
    # passing them through. The good bar still comes through.
    raw = [
        {"time": "not-an-int", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 0},
        {"time": 1000,         "open": 2, "high": 2, "low": 2, "close": 2, "volume": 1},
    ]
    result = normalize_candles(raw)
    assert [c["time"] for c in result] == [1000]


def test_normalize_candles_preserves_zero_timestamp():
    # Regression: previously item.get("time") or item.get("timestamp") treated
    # 0 as falsy and silently nulled out the time field.
    raw = [{"time": 0, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}]
    result = normalize_candles(raw)
    assert result[0]["time"] == 0
