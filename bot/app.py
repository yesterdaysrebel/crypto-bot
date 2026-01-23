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
    MIN_SECONDS_BETWEEN_TRADES,
    POLL_SECONDS,
    PRODUCT_ID,
    QUOTE_ASSET_ID,
    REDUCE_ONLY,
    RISK_PER_TRADE,
    SYMBOL,
    TAKE_PROFIT_ENABLED,
    TIMEFRAME,
    TIME_IN_FORCE,
    POST_ONLY,
    QTY_STEP,
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
        if DRY_RUN:
            self.logger.warning("DRY_RUN is enabled: orders will not be placed")

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

    def _place_bracket(self, signal, size):
        entry_type = self.api.order_type_value(ENTRY_ORDER_TYPE)
        tif_value = self.api.tif_value(TIME_IN_FORCE)

        self.logger.info(
            "Placing entry order: side=%s size=%s entry=%s",
            signal["side"],
            size,
            signal["entry"],
        )

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
        self.logger.info("Placing stop loss at %s", signal["stop"])
        self.api.place_stop_order(
            product_id=self.product_id,
            side=stop_side,
            size=size,
            stop_price=signal["stop"],
            order_type="market",
        )

        if TAKE_PROFIT_ENABLED:
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
            return

        if self._has_position():
            return

        raw_candles = self.api.get_candles(SYMBOL, TIMEFRAME, CANDLE_LIMIT)
        candles = normalize_candles(raw_candles)
        signal = generate_signal(candles)
        if not signal:
            return

        size = position_size(
            equity=equity,
            entry=signal["entry"],
            stop=signal["stop"],
            min_qty=MIN_QTY,
            qty_step=QTY_STEP,
            risk_per_trade=RISK_PER_TRADE,
            max_notional=(DAILY_CAPITAL * LEVERAGE) if DAILY_CAPITAL and LEVERAGE else None,
        )
        if size <= 0:
            self.logger.warning("Size computed as 0; skipping trade")
            return

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
        self.logger.info("Starting bot for %s (product_id=%s)", SYMBOL, self.product_id)
        while True:
            try:
                self.run_once()
            except Exception as exc:
                self.logger.exception("Bot error: %s", exc)
            time.sleep(POLL_SECONDS)
