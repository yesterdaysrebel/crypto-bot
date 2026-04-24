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
    TIMEFRAME,
    TIME_IN_FORCE,
    POST_ONLY,
    QTY_STEP,
    FIXED_QTY,
    PRICE_SOURCE,
    TRAILING_STOP_ENABLED,
    USE_BREAKOUT_STRATEGY,
    USE_REGIME_TREND,
)
from bot.delta_client import DeltaApi
from bot.journal import TradeJournal
from bot.logger import setup_logging
from bot.risk import position_size, trading_halted
from bot.state import BotState
from bot.strategy import generate_signal
from bot.utils import normalize_candles


class TradingBot:
    def __init__(self):
        self.logger = setup_logging(LOG_LEVEL)
        self.api = DeltaApi()
        self.state = BotState()
        self.journal = TradeJournal()
        self.product_id = self.api.resolve_product_id(SYMBOL, PRODUCT_ID)
        self.loop_count = 0
        self.last_heartbeat = 0
        self.strategy_name = self._active_strategy_name()
        if DRY_RUN:
            self.logger.warning("DRY_RUN is enabled: orders will not be placed")

    def _active_strategy_name(self):
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
        response = self.api.get_position(self.product_id)
        position = response.get("result", response)
        size = float(position.get("size", 0)) if isinstance(position, dict) else 0.0
        return abs(size) > 0

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
                    if isinstance(order, dict) and not order.get("reduce_only", False)
                ]
                return len(entry_orders) > 0
            elif isinstance(orders, dict) and orders:
                # Single order or dict response
                return not orders.get("reduce_only", False)
        except Exception as exc:
            # If we can't check orders, log warning but don't block trading
            # (some API clients might not support this)
            self.logger.debug("Could not check pending orders: %s", exc)
            return False
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
        self.api.place_order(
            product_id=self.product_id,
            side=signal["side"],
            size=size,
            order_type=entry_type,
            limit_price=signal["entry"] if ENTRY_ORDER_TYPE == "limit" else None,
            time_in_force=tif_value,
            post_only=POST_ONLY,
            reduce_only=False,
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

        halted, reason = trading_halted(self.state, equity)
        if halted:
            self.logger.warning("Trading halted: %s", reason)
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
            return

        if self._has_position():
            self.logger.debug("Position exists; waiting for exit before new entry")
            return

        # Skip pending orders check in dry run mode (no real orders are placed)
        if not DRY_RUN and self._has_pending_orders():
            self.logger.debug("Pending orders exist, skipping new trade setup")
            return

        raw_candles = self.api.get_candles(SYMBOL, TIMEFRAME, CANDLE_LIMIT)
        candles = normalize_candles(raw_candles)
        price_override = None
        if PRICE_SOURCE and PRICE_SOURCE != "candle":
            try:
                price_override = self.api.get_price(SYMBOL, PRICE_SOURCE, product_id=self.product_id)
            except Exception as exc:
                self.logger.warning("Price source %s unavailable, using candle close: %s", PRICE_SOURCE, exc)
        signal = generate_signal(candles, price_override=price_override)
        if not signal:
            # Log at debug level to avoid spam, but can be enabled for troubleshooting
            self.logger.debug("No trading signal generated (checking market conditions)")
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
            return

        trail_amount = abs(signal["entry"] - signal["stop"])
        self.logger.info(
            "Signal detected: side=%s entry=%s stop_ref=%s target=%s size=%s trail=%s",
            signal["side"],
            signal["entry"],
            signal["stop"],
            signal["target"],
            size,
            trail_amount,
        )

        if DRY_RUN:
            self.logger.info("DRY_RUN trade: %s %s @ %s", signal["side"], size, signal["entry"])
            self._record_journal(signal, size, "dry_run", "signal generated")
            self.state.record_trade()
            return

        self._place_bracket(signal, size)
        if LOG_TRADES:
            self._record_journal(signal, size, "live", "orders placed")
        self.state.record_trade()

    def run(self):
        self.logger.info(
            "Starting bot for %s (product_id=%s, strategy=%s, dry_run=%s)",
            SYMBOL,
            self.product_id,
            self.strategy_name,
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
