from math import floor

from bot.config import (
    MAX_DAILY_LOSS,
    MAX_WEEKLY_LOSS,
    MAX_DRAWDOWN,
    MAX_TRADES_PER_DAY,
)


def round_step(value, step):
    if step <= 0:
        return value
    return floor(value / step) * step


def position_size(
    equity,
    entry,
    stop,
    min_qty,
    qty_step,
    risk_per_trade,
    max_notional=None,
):
    stop_dist = abs(entry - stop)
    if stop_dist <= 0:
        return 0.0
    risk_amount = equity * risk_per_trade
    size = risk_amount / stop_dist
    if max_notional and entry > 0:
        size = min(size, max_notional / entry)
    size = max(size, min_qty)
    return round_step(size, qty_step)


def trading_halted(state, equity):
    if state.daily_loss_pct(equity) >= MAX_DAILY_LOSS:
        return True, "max daily loss reached"
    if state.weekly_loss_pct(equity) >= MAX_WEEKLY_LOSS:
        return True, "max weekly loss reached"
    if state.drawdown_pct(equity) >= MAX_DRAWDOWN:
        return True, "max drawdown reached"
    if int(state.state.get("daily_trades", 0)) >= MAX_TRADES_PER_DAY:
        return True, "max trades per day reached"
    return False, ""
