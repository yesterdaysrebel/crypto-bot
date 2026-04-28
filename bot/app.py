import time

from bot.config import (
    ACCOUNT_EQUITY,
    CANDLE_LIMIT,
    DAILY_CAPITAL,
    DRY_RUN,
    ENTRY_ORDER_TYPE,
    LEVERAGE,
    LOG_LEVEL,
    LOG_TRADES,
    MIN_QTY,
    MAX_QTY,
    MIN_SECONDS_BETWEEN_TRADES,
    POLL_SECONDS,
    PRODUCT_ID,
    QUOTE_ASSET_ID,
    REDUCE_ONLY,
    RISK_PER_TRADE,
    SYMBOL,
    TAKE_PROFIT_ENABLED,
    PARTIAL_PROFIT_ENABLED,
    PARTIAL_PROFIT_PCT,
    PARTIAL_PROFIT_R,
    STOP_PCT,
    TIMEFRAME,
    TAKE_PROFIT_R,
    TIME_IN_FORCE,
    POST_ONLY,
    QTY_STEP,
    FIXED_QTY,
    PRICE_SOURCE,
    TRAILING_STOP_ENABLED,
    USE_BREAKOUT_STRATEGY,
    USE_HYBRID_STRATEGY,
    USE_MTF_REGIME,
    USE_REGIME_TREND,
    TREND_TIMEFRAME,
    ENTRY_TIMEFRAME,
)
from bot.analytics import AnalyticsLogger
from bot.delta_client import DeltaApi
from bot.journal import TradeJournal
from bot.logger import setup_logging
from bot.outcomes import OutcomeJournal
from bot.risk import position_size, trading_halted
from bot.state import BotState
try:
    from bot.strategy import evaluate_signal
except ImportError:
    from bot.strategy import generate_signal as _legacy_generate_signal

    def evaluate_signal(candles, price_override=None, trend_candles=None):
        signal = _legacy_generate_signal(
            candles,
            price_override=price_override,
            trend_candles=trend_candles,
        )
        return signal, "legacy_signal_router" if signal else "legacy_no_signal"
from bot.utils import normalize_candles


class TradingBot:
    def __init__(self):
        self._validate_runtime_config()
        self.logger = setup_logging(LOG_LEVEL)
        self.api = DeltaApi()
        self.state = BotState()
        self.journal = TradeJournal()
        self.analytics = AnalyticsLogger()
        self.outcomes = OutcomeJournal()
        self.product_id = self.api.resolve_product_id(SYMBOL, PRODUCT_ID)
        self.loop_count = 0
        self.last_heartbeat = 0
        self.strategy_name = self._active_strategy_name()
        if DRY_RUN:
            self.logger.warning("DRY_RUN is enabled: orders will not be placed")

    def _validate_runtime_config(self):
        strategy_flags = [
            USE_HYBRID_STRATEGY,
            USE_MTF_REGIME,
            USE_REGIME_TREND,
            USE_BREAKOUT_STRATEGY,
        ]
        enabled_strategy_count = sum(1 for flag in strategy_flags if flag)
        if enabled_strategy_count > 1:
            raise ValueError(
                "Invalid strategy config: enable only one of "
                "USE_HYBRID_STRATEGY/USE_MTF_REGIME/USE_REGIME_TREND/USE_BREAKOUT_STRATEGY"
            )
        if MIN_SECONDS_BETWEEN_TRADES < 0:
            raise ValueError("MIN_SECONDS_BETWEEN_TRADES must be >= 0")
        if POLL_SECONDS <= 0:
            raise ValueError("POLL_SECONDS must be > 0")
        if RISK_PER_TRADE <= 0 or RISK_PER_TRADE > 0.05:
            raise ValueError("RISK_PER_TRADE must be > 0 and <= 0.05")
        if PARTIAL_PROFIT_ENABLED and not (0 < PARTIAL_PROFIT_PCT < 1):
            raise ValueError("PARTIAL_PROFIT_PCT must be between 0 and 1 when enabled")

    def _active_strategy_name(self):
        if USE_HYBRID_STRATEGY:
            return "hybrid"
        if USE_MTF_REGIME:
            return "mtf_regime"
        if USE_REGIME_TREND:
            return "regime_trend"
        if USE_BREAKOUT_STRATEGY:
            return "breakout"
        return "basic"

    def _get_equity(self):
        if QUOTE_ASSET_ID:
            response = self.api.get_balances(QUOTE_ASSET_ID)
            balances = response.get("result", response)
            if isinstance(balances, list) and balances:
                return float(balances[0].get("available_balance", ACCOUNT_EQUITY))
        return ACCOUNT_EQUITY

    def _has_position(self):
        position = self._get_position()
        size = float(position.get("size", 0))
        return abs(size) > 0

    def _get_position(self):
        response = self.api.get_position(self.product_id)
        position = response.get("result", response)
        if isinstance(position, dict):
            return position
        return {}

    def _get_open_orders(self):
        response = self.api.get_orders(product_id=self.product_id, states="open,pending")
        orders = response.get("result", response)
        if isinstance(orders, list):
            return [order for order in orders if isinstance(order, dict)]
        if isinstance(orders, dict) and orders:
            return [orders]
        return []

    def _bool_field(self, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes"}
        return False

    def _order_is_reduce_only(self, order):
        return self._bool_field(order.get("reduce_only")) or self._bool_field(order.get("reduceOnly"))

    def _order_is_stop_like(self, order):
        order_type = str(order.get("order_type") or order.get("type") or "").lower()
        if "stop" in order_type:
            return True
        if order.get("stop_price") is not None or order.get("trigger_price") is not None:
            return True
        if self._bool_field(order.get("isTrailingStopLoss")):
            return True
        return False

    def _reconcile_protective_orders(self, equity, signal_timeframe, trend_timeframe, mode):
        if DRY_RUN:
            return
        position = self._get_position()
        size = abs(float(position.get("size", 0) or 0))
        if size <= 0:
            return

        entry_price = float(
            position.get("entry_price")
            or position.get("avg_price")
            or position.get("average_price")
            or position.get("mark_price")
            or 0
        )
        if entry_price <= 0:
            try:
                entry_price = float(self.api.get_price(SYMBOL, PRICE_SOURCE, product_id=self.product_id))
            except Exception:
                self.logger.warning("Cannot reconcile exits: missing reliable reference price")
                return

        side = "buy" if float(position.get("size", 0)) > 0 else "sell"
        exit_side = "sell" if side == "buy" else "buy"
        live_trade_plan = self.state.get_live_trade_plan() or {}
        plan_side = str(live_trade_plan.get("side", "")).lower()
        if plan_side != side:
            live_trade_plan = {}

        stop_price_plan = live_trade_plan.get("stop")
        target_price_plan = live_trade_plan.get("target")
        trail_amount_plan = live_trade_plan.get("trail_amount")
        risk_distance = max(abs(entry_price * 0.001), abs(entry_price * STOP_PCT))
        open_orders = self._get_open_orders()
        reduce_orders = [order for order in open_orders if self._order_is_reduce_only(order)]
        exit_orders = [
            order
            for order in reduce_orders
            if str(order.get("side", "")).lower() == exit_side
        ]
        has_stop = any(self._order_is_stop_like(order) for order in exit_orders)
        has_take_profit = any(not self._order_is_stop_like(order) for order in exit_orders)
        tif_value = self.api.tif_value(TIME_IN_FORCE)

        if not has_stop:
            if TRAILING_STOP_ENABLED:
                trail_amount = (
                    abs(float(trail_amount_plan))
                    if trail_amount_plan is not None
                    else risk_distance
                )
                self.api.place_stop_order(
                    product_id=self.product_id,
                    side=exit_side,
                    size=size,
                    order_type="market",
                    is_trailing=True,
                    trail_amount=trail_amount,
                )
                self.logger.warning("Reconciliation: missing stop detected; trailing stop restored")
            else:
                if stop_price_plan is not None:
                    stop_price = float(stop_price_plan)
                else:
                    stop_price = entry_price - risk_distance if side == "buy" else entry_price + risk_distance
                self.api.place_stop_order(
                    product_id=self.product_id,
                    side=exit_side,
                    size=size,
                    order_type="market",
                    stop_price=stop_price,
                    is_trailing=False,
                )
                self.logger.warning("Reconciliation: missing stop detected; fixed stop restored")
            self.analytics.log(
                symbol=SYMBOL,
                strategy=self.strategy_name,
                mode=mode,
                event="reconciled",
                reason="restored_missing_stop",
                equity=equity,
                price=entry_price,
                side=side,
                entry=entry_price,
                size=size,
                signal_timeframe=signal_timeframe,
                trend_timeframe=trend_timeframe,
            )

        if TAKE_PROFIT_ENABLED and not PARTIAL_PROFIT_ENABLED and not has_take_profit:
            if target_price_plan is not None:
                target_price = float(target_price_plan)
            else:
                target_price = (
                    entry_price + (risk_distance * TAKE_PROFIT_R)
                    if side == "buy"
                    else entry_price - (risk_distance * TAKE_PROFIT_R)
                )
            self.api.place_order(
                product_id=self.product_id,
                side=exit_side,
                size=size,
                order_type=self.api.order_type_value("limit"),
                limit_price=target_price,
                time_in_force=tif_value,
                post_only=POST_ONLY,
                reduce_only=True,
            )
            self.logger.warning("Reconciliation: missing take profit detected; take profit restored")
            self.analytics.log(
                symbol=SYMBOL,
                strategy=self.strategy_name,
                mode=mode,
                event="reconciled",
                reason="restored_missing_take_profit",
                equity=equity,
                price=entry_price,
                side=side,
                entry=entry_price,
                target=target_price,
                size=size,
                signal_timeframe=signal_timeframe,
                trend_timeframe=trend_timeframe,
            )

    def _has_pending_orders(self):
        """Check if there are any pending/open orders for this product"""
        try:
            # Common order states: "open", "pending", "filled", "cancelled", "rejected"
            # We want to check for orders that are still active (not filled/cancelled/rejected)
            response = self.api.get_orders(product_id=self.product_id, states="open,pending")
            orders = response.get("result", response)
            if isinstance(orders, list):
                # Filter to only non-reduce-only orders (entry orders)
                entry_orders = [
                    order for order in orders
                    if isinstance(order, dict) and not self._order_is_reduce_only(order)
                ]
                return len(entry_orders) > 0
            elif isinstance(orders, dict) and orders:
                # Single order or dict response
                return not self._order_is_reduce_only(orders)
        except Exception as exc:
            # Fail closed: if order state is unknown, block new entries.
            self.logger.warning("Could not check pending orders; blocking new trade setup: %s", exc)
            return True
        return False

    def _entry_order_accepted(self, response):
        if not isinstance(response, dict):
            return False
        payload = response.get("result", response)
        if isinstance(payload, dict):
            state = str(payload.get("state", "")).lower()
            if state in {"rejected", "cancelled", "canceled", "failed"}:
                return False
            if payload.get("id") is not None or payload.get("order_id") is not None:
                return True
        # Conservative fallback: if shape is unknown, treat as not accepted.
        return False

    def _place_bracket(self, signal, size):
        entry_type = self.api.order_type_value(ENTRY_ORDER_TYPE)
        tif_value = self.api.tif_value(TIME_IN_FORCE)
        trail_amount = abs(signal["entry"] - signal["stop"])
        stop_side = "sell" if signal["side"] == "buy" else "buy"

        # Calculate partial profit sizes
        if PARTIAL_PROFIT_ENABLED:
            partial_size = int(size * PARTIAL_PROFIT_PCT)
            trailing_size = size - partial_size
            
            # Ensure sizes respect minimum quantities
            if partial_size < 1:
                partial_size = 0
                trailing_size = size
            if trailing_size < 1:
                trailing_size = 1
                partial_size = size - 1
        else:
            partial_size = 0
            trailing_size = size

        self.logger.info(
            "Placing orders: side=%s size=%s entry=%s stop_ref=%s trail=%s target=%s",
            signal["side"],
            size,
            signal["entry"],
            signal["stop"],
            trail_amount,
            signal["target"],
        )

        # Place entry order
        entry_response = self.api.place_order(
            product_id=self.product_id,
            side=signal["side"],
            size=size,
            order_type=entry_type,
            limit_price=signal["entry"] if ENTRY_ORDER_TYPE == "limit" else None,
            time_in_force=tif_value,
            post_only=POST_ONLY,
            reduce_only=False,
        )
        if not self._entry_order_accepted(entry_response):
            raise RuntimeError(f"Entry order was not accepted: {entry_response}")

        # For market entries, verify that a position actually opened before placing exits.
        if ENTRY_ORDER_TYPE == "market":
            position_open = False
            for _ in range(3):
                if self._has_position():
                    position_open = True
                    break
                time.sleep(1)
            if not position_open:
                raise RuntimeError("Market entry was accepted but no open position detected")
        self.state.set_live_trade_plan(
            {
                "symbol": SYMBOL,
                "side": signal["side"],
                "entry": signal["entry"],
                "stop": signal["stop"],
                "target": signal["target"],
                "trail_amount": trail_amount,
                "size": size,
                "opened_ts": int(time.time()),
                "partial_profit_enabled": PARTIAL_PROFIT_ENABLED,
            }
        )

        stop_side = "sell" if signal["side"] == "buy" else "buy"
        
        if TRAILING_STOP_ENABLED:
            self.logger.info("Placing trailing stop loss with trail %s", trail_amount)
            self.api.place_stop_order(
                product_id=self.product_id,
                side=stop_side,
                size=size,
                order_type="market",
                is_trailing=True,
                trail_amount=trail_amount,
            )
        else:
            # Use fixed stop loss instead of trailing
            self.logger.info("Placing fixed stop loss at %s", signal["stop"])
            self.api.place_stop_order(
                product_id=self.product_id,
                side=stop_side,
                size=size,
                order_type="market",
                stop_price=signal["stop"],
                is_trailing=False,
            )

        # Place partial profit target at 2:1 (or configured R:R)
        if PARTIAL_PROFIT_ENABLED and partial_size > 0:
            partial_target = signal["entry"] + (trail_amount * PARTIAL_PROFIT_R) if signal["side"] == "buy" else signal["entry"] - (trail_amount * PARTIAL_PROFIT_R)
            self.logger.info(
                "Placing PARTIAL take profit at %s for %s%% of position (size=%s)",
                partial_target,
                int(PARTIAL_PROFIT_PCT * 100),
                partial_size,
            )
            self.api.place_order(
                product_id=self.product_id,
                side=stop_side,
                size=partial_size,
                order_type=self.api.order_type_value("limit"),
                limit_price=partial_target,
                time_in_force=tif_value,
                post_only=POST_ONLY,
                reduce_only=REDUCE_ONLY,
            )
            self.logger.info(
                "Remaining %s%% (size=%s) will trail with stop loss",
                int((1 - PARTIAL_PROFIT_PCT) * 100),
                trailing_size,
            )

        # Place final take profit at original target (if enabled and not using partial)
        if TAKE_PROFIT_ENABLED and not PARTIAL_PROFIT_ENABLED:
            self.logger.info("Placing take profit at %s", signal["target"])
            self.api.place_order(
                product_id=self.product_id,
                side=stop_side,
                size=size,
                order_type=self.api.order_type_value("limit"),
                limit_price=signal["target"],
                time_in_force=tif_value,
                post_only=POST_ONLY,
                reduce_only=REDUCE_ONLY,
            )

    def _record_journal(self, signal, size, mode, note):
        self.journal.log(
            symbol=SYMBOL,
            product_id=self.product_id,
            side=signal["side"],
            entry=signal["entry"],
            stop=signal["stop"],
            target=signal["target"],
            size=size,
            mode=mode,
            note=note,
        )

    def run_once(self):
        equity = self._get_equity()
        self.state.rollover(equity)
        signal_timeframe = ENTRY_TIMEFRAME if USE_MTF_REGIME else TIMEFRAME
        trend_timeframe = TREND_TIMEFRAME if USE_MTF_REGIME else ""
        mode = "dry_run" if DRY_RUN else "live"
        current_price = None

        # In DRY_RUN, track a virtual open trade lifecycle for outcome stats.
        open_paper_trade = self.state.get_open_paper_trade() if DRY_RUN else None
        if open_paper_trade:
            try:
                current_price = self.api.get_price(SYMBOL, PRICE_SOURCE, product_id=self.product_id)
            except Exception:
                current_price = None
            if current_price is not None:
                side = open_paper_trade["side"]
                stop = float(open_paper_trade["stop"])
                target = float(open_paper_trade["target"])
                hit_stop = (side == "buy" and current_price <= stop) or (side == "sell" and current_price >= stop)
                hit_target = (side == "buy" and current_price >= target) or (side == "sell" and current_price <= target)
                if hit_stop or hit_target:
                    exit_reason = "stop_hit" if hit_stop else "target_hit"
                    self.outcomes.log_close(
                        symbol=SYMBOL,
                        mode=mode,
                        trade=open_paper_trade,
                        exit_price=current_price,
                        exit_reason=exit_reason,
                    )
                    self.analytics.log(
                        symbol=SYMBOL,
                        strategy=self.strategy_name,
                        mode=mode,
                        event="trade_closed",
                        reason=exit_reason,
                        equity=equity,
                        price=current_price,
                        side=open_paper_trade["side"],
                        entry=float(open_paper_trade["entry"]),
                        stop=float(open_paper_trade["stop"]),
                        target=float(open_paper_trade["target"]),
                        size=float(open_paper_trade["size"]),
                        signal_timeframe=signal_timeframe,
                        trend_timeframe=trend_timeframe,
                    )
                    self.state.clear_open_paper_trade()
                else:
                    self.analytics.log(
                        symbol=SYMBOL,
                        strategy=self.strategy_name,
                        mode=mode,
                        event="position_open",
                        reason="paper_trade_active",
                        equity=equity,
                        price=current_price,
                        side=open_paper_trade["side"],
                        entry=float(open_paper_trade["entry"]),
                        stop=float(open_paper_trade["stop"]),
                        target=float(open_paper_trade["target"]),
                        size=float(open_paper_trade["size"]),
                        signal_timeframe=signal_timeframe,
                        trend_timeframe=trend_timeframe,
                    )
                    self.logger.debug("Paper trade still open; waiting for stop/target hit")
                    return
            self.logger.debug("Paper trade open but price unavailable; skipping new entry")
            self.analytics.log(
                symbol=SYMBOL,
                strategy=self.strategy_name,
                mode=mode,
                event="blocked",
                reason="paper_trade_open_price_unavailable",
                equity=equity,
                signal_timeframe=signal_timeframe,
                trend_timeframe=trend_timeframe,
            )
            return

        halted, reason = trading_halted(self.state, equity)
        if halted:
            self.logger.warning("Trading halted: %s", reason)
            self.analytics.log(
                symbol=SYMBOL,
                strategy=self.strategy_name,
                mode=mode,
                event="blocked",
                reason=f"risk_halt:{reason}",
                equity=equity,
                signal_timeframe=signal_timeframe,
                trend_timeframe=trend_timeframe,
            )
            return

        if not self.state.can_trade_cooldown(MIN_SECONDS_BETWEEN_TRADES):
            last_ts = int(self.state.state.get("last_trade_ts") or 0)
            elapsed = int(time.time()) - last_ts
            remaining = MIN_SECONDS_BETWEEN_TRADES - elapsed
            self.logger.debug(
                "Cooldown active: %s seconds remaining (last trade: %s seconds ago)",
                remaining,
                elapsed,
            )
            self.analytics.log(
                symbol=SYMBOL,
                strategy=self.strategy_name,
                mode=mode,
                event="blocked",
                reason=f"cooldown:{remaining}s_remaining",
                equity=equity,
                signal_timeframe=signal_timeframe,
                trend_timeframe=trend_timeframe,
            )
            return

        if self._has_position():
            self._reconcile_protective_orders(
                equity=equity,
                signal_timeframe=signal_timeframe,
                trend_timeframe=trend_timeframe,
                mode=mode,
            )
            self.logger.debug("Position exists; waiting for exit before new entry")
            self.analytics.log(
                symbol=SYMBOL,
                strategy=self.strategy_name,
                mode=mode,
                event="blocked",
                reason="position_open",
                equity=equity,
                signal_timeframe=signal_timeframe,
                trend_timeframe=trend_timeframe,
            )
            return
        # Skip pending orders check in dry run mode (no real orders are placed)
        if not DRY_RUN and self._has_pending_orders():
            self.logger.debug("Pending orders exist, skipping new trade setup")
            self.analytics.log(
                symbol=SYMBOL,
                strategy=self.strategy_name,
                mode=mode,
                event="blocked",
                reason="pending_orders",
                equity=equity,
                signal_timeframe=signal_timeframe,
                trend_timeframe=trend_timeframe,
            )
            return
        self.state.clear_live_trade_plan()

        raw_candles = self.api.get_candles(SYMBOL, signal_timeframe, CANDLE_LIMIT)
        candles = normalize_candles(raw_candles)
        trend_candles = None
        if USE_MTF_REGIME:
            raw_trend_candles = self.api.get_candles(SYMBOL, TREND_TIMEFRAME, CANDLE_LIMIT)
            trend_candles = normalize_candles(raw_trend_candles)
        price_override = None
        if PRICE_SOURCE and PRICE_SOURCE != "candle":
            try:
                price_override = self.api.get_price(SYMBOL, PRICE_SOURCE, product_id=self.product_id)
            except Exception as exc:
                self.logger.warning("Price source %s unavailable, using candle close: %s", PRICE_SOURCE, exc)
        signal, reason = evaluate_signal(candles, price_override=price_override, trend_candles=trend_candles)
        if not signal:
            self.logger.debug("No trading signal: %s", reason)
            self.analytics.log(
                symbol=SYMBOL,
                strategy=self.strategy_name,
                mode=mode,
                event="no_signal",
                reason=reason,
                equity=equity,
                price=price_override if price_override is not None else candles[-1]["close"],
                signal_timeframe=signal_timeframe,
                trend_timeframe=trend_timeframe,
            )
            return

        size = position_size(
            equity=equity,
            entry=signal["entry"],
            stop=signal["stop"],
            min_qty=MIN_QTY,
            qty_step=QTY_STEP,
            risk_per_trade=RISK_PER_TRADE,
            fixed_qty=FIXED_QTY,
            max_notional=(DAILY_CAPITAL * LEVERAGE) if DAILY_CAPITAL and LEVERAGE else None,
            max_qty=MAX_QTY,
        )
        if size <= 0:
            self.logger.warning("Size computed as 0; skipping trade")
            self.analytics.log(
                symbol=SYMBOL,
                strategy=self.strategy_name,
                mode=mode,
                event="blocked",
                reason="size_zero",
                equity=equity,
                price=signal["entry"],
                side=signal["side"],
                entry=signal["entry"],
                stop=signal["stop"],
                target=signal["target"],
                signal_timeframe=signal_timeframe,
                trend_timeframe=trend_timeframe,
            )
            return

        trail_amount = abs(signal["entry"] - signal["stop"])
        self.logger.info(
            "Signal detected: side=%s entry=%s stop_ref=%s target=%s size=%s trail=%s reason=%s",
            signal["side"],
            signal["entry"],
            signal["stop"],
            signal["target"],
            size,
            trail_amount,
            reason,
        )
        self.analytics.log(
            symbol=SYMBOL,
            strategy=self.strategy_name,
            mode=mode,
            event="signal",
            reason=reason,
            equity=equity,
            price=signal["entry"],
            side=signal["side"],
            entry=signal["entry"],
            stop=signal["stop"],
            target=signal["target"],
            size=size,
            signal_timeframe=signal_timeframe,
            trend_timeframe=trend_timeframe,
        )

        if DRY_RUN:
            self.logger.info("DRY_RUN trade: %s %s @ %s", signal["side"], size, signal["entry"])
            self._record_journal(signal, size, "dry_run", "signal generated")
            self.state.set_open_paper_trade(
                {
                    "side": signal["side"],
                    "entry": signal["entry"],
                    "stop": signal["stop"],
                    "target": signal["target"],
                    "size": size,
                    "opened_ts": int(time.time()),
                }
            )
            self.analytics.log(
                symbol=SYMBOL,
                strategy=self.strategy_name,
                mode=mode,
                event="trade_simulated",
                reason=reason,
                equity=equity,
                price=signal["entry"],
                side=signal["side"],
                entry=signal["entry"],
                stop=signal["stop"],
                target=signal["target"],
                size=size,
                signal_timeframe=signal_timeframe,
                trend_timeframe=trend_timeframe,
            )
            self.state.record_trade()
            return

        self._place_bracket(signal, size)
        if LOG_TRADES:
            self._record_journal(signal, size, "live", "orders placed")
        self.analytics.log(
            symbol=SYMBOL,
            strategy=self.strategy_name,
            mode=mode,
            event="trade_live",
            reason=reason,
            equity=equity,
            price=signal["entry"],
            side=signal["side"],
            entry=signal["entry"],
            stop=signal["stop"],
            target=signal["target"],
            size=size,
            signal_timeframe=signal_timeframe,
            trend_timeframe=trend_timeframe,
        )
        self.state.record_trade()

    def run(self):
        self.logger.info(
            "Starting bot for %s (product_id=%s, strategy=%s, tf=%s, trend_tf=%s, dry_run=%s)",
            SYMBOL,
            self.product_id,
            self.strategy_name,
            ENTRY_TIMEFRAME if USE_MTF_REGIME else TIMEFRAME,
            TREND_TIMEFRAME if USE_MTF_REGIME else "n/a",
            DRY_RUN,
        )
        while True:
            try:
                self.loop_count += 1
                now = time.time()
                if now - self.last_heartbeat >= 60:
                    try:
                        current_price = self.api.get_price(SYMBOL, PRICE_SOURCE, product_id=self.product_id)
                        self.logger.info("Bot heartbeat: alive, loop=%d, price=%s", self.loop_count, current_price)
                    except Exception:
                        self.logger.info("Bot heartbeat: alive, loop=%d", self.loop_count)
                    self.last_heartbeat = now
                self.run_once()
            except Exception as exc:
                self.logger.exception("Bot error: %s", exc)
            time.sleep(POLL_SECONDS)
