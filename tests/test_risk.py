from bot.risk import position_size


def test_position_size_capped_by_max_notional_when_set():
    # equity 50000, 0.5% risk = $250; entry $93.5, stop $91.93 (~1.7% away),
    # raw size = 250/1.57 ≈ 159. With $2000 notional cap, 2000/93.5 ≈ 21.4.
    size = position_size(
        equity=50000,
        entry=93.5,
        stop=91.93,
        min_qty=0.1,
        qty_step=0.1,
        risk_per_trade=0.005,
        max_notional=2000.0,
        max_qty=0.0,
    )
    assert 21.0 <= size <= 21.5


def test_position_size_capped_by_max_qty_when_set():
    # Same inputs but with max_qty=20 instead of notional cap.
    size = position_size(
        equity=50000,
        entry=93.5,
        stop=91.93,
        min_qty=0.1,
        qty_step=0.1,
        risk_per_trade=0.005,
        max_notional=None,
        max_qty=20.0,
    )
    assert size == 20.0


def test_position_size_full_risk_when_no_caps_bind():
    # Same inputs with no caps; raw size ≈ 159.
    size = position_size(
        equity=50000,
        entry=93.5,
        stop=91.93,
        min_qty=0.1,
        qty_step=0.1,
        risk_per_trade=0.005,
        max_notional=None,
        max_qty=0.0,
    )
    assert 158.0 <= size <= 160.0


def test_position_size_zero_when_stop_distance_is_zero():
    size = position_size(
        equity=50000,
        entry=93.5,
        stop=93.5,
        min_qty=0.1,
        qty_step=0.1,
        risk_per_trade=0.005,
    )
    assert size == 0.0
