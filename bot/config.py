import os


def _get_float(name, default):
    value = os.getenv(name)
    return float(value) if value is not None else default


def _get_int(name, default):
    value = os.getenv(name)
    return int(value) if value is not None else default


BASE_URL = os.getenv("BASE_URL", "https://api.india.delta.exchange")
SYMBOL = os.getenv("SYMBOL", "SOLUSD")
PRODUCT_ID = os.getenv("PRODUCT_ID")
QUOTE_ASSET_ID = os.getenv("QUOTE_ASSET_ID")

API_KEY = os.getenv("DELTA_API_KEY", "")
API_SECRET = os.getenv("DELTA_API_SECRET", "")

ACCOUNT_EQUITY = _get_float("ACCOUNT_EQUITY", 50000.0)
DAILY_CAPITAL = _get_float("DAILY_CAPITAL", 0.0)
RISK_PER_TRADE = _get_float("RISK_PER_TRADE", 0.005)
MAX_DAILY_LOSS = _get_float("MAX_DAILY_LOSS", 0.02)
MAX_WEEKLY_LOSS = _get_float("MAX_WEEKLY_LOSS", 0.05)
MAX_DRAWDOWN = _get_float("MAX_DRAWDOWN", 0.15)
LEVERAGE = _get_float("LEVERAGE", 0.0)

EMA_FAST = _get_int("EMA_FAST", 20)
EMA_SLOW = _get_int("EMA_SLOW", 50)
TREND_EMA_PERIOD = _get_int("TREND_EMA_PERIOD", 100)  # 0 = disable trend filter
VWAP_LOOKBACK = _get_int("VWAP_LOOKBACK", 50)
STOP_PCT = _get_float("STOP_PCT", 0.004)
TAKE_PROFIT_R = _get_float("TAKE_PROFIT_R", 1.5)

# Advanced strategy settings
USE_ATR_STOPS = os.getenv("USE_ATR_STOPS", "false").lower() == "true"
ATR_PERIOD = _get_int("ATR_PERIOD", 14)
ATR_MULTIPLIER = _get_float("ATR_MULTIPLIER", 2.0)
RSI_PERIOD = _get_int("RSI_PERIOD", 14)
RSI_OVERBOUGHT = _get_float("RSI_OVERBOUGHT", 70.0)
RSI_OVERSOLD = _get_float("RSI_OVERSOLD", 30.0)
BB_PERIOD = _get_int("BB_PERIOD", 20)
BB_STD_DEV = _get_float("BB_STD_DEV", 2.0)
VOLUME_SURGE_MULTIPLIER = _get_float("VOLUME_SURGE_MULTIPLIER", 1.5)
USE_BREAKOUT_STRATEGY = os.getenv("USE_BREAKOUT_STRATEGY", "false").lower() == "true"

ENTRY_ORDER_TYPE = os.getenv("ENTRY_ORDER_TYPE", "market").lower()
TIME_IN_FORCE = os.getenv("TIME_IN_FORCE", "gtc").lower()
POST_ONLY = os.getenv("POST_ONLY", "false").lower() == "true"
REDUCE_ONLY = os.getenv("REDUCE_ONLY", "true").lower() == "true"
TAKE_PROFIT_ENABLED = os.getenv("TAKE_PROFIT_ENABLED", "true").lower() == "true"
PARTIAL_PROFIT_ENABLED = os.getenv("PARTIAL_PROFIT_ENABLED", "false").lower() == "true"
PARTIAL_PROFIT_PCT = _get_float("PARTIAL_PROFIT_PCT", 0.5)
PARTIAL_PROFIT_R = _get_float("PARTIAL_PROFIT_R", 2.0)
TRAILING_STOP_ENABLED = os.getenv("TRAILING_STOP_ENABLED", "true").lower() == "true"

MIN_QTY = _get_float("MIN_QTY", 0.1)
MAX_QTY = _get_float("MAX_QTY", 0.0)
QTY_STEP = _get_float("QTY_STEP", 0.1)
FIXED_QTY = _get_float("FIXED_QTY", 0.0)
PRICE_SOURCE = os.getenv("PRICE_SOURCE", "candle").lower()

TIMEFRAME = os.getenv("TIMEFRAME", "1m")
CANDLE_LIMIT = _get_int("CANDLE_LIMIT", 200)
POLL_SECONDS = _get_float("POLL_SECONDS", 10.0)
MIN_SECONDS_BETWEEN_TRADES = _get_int("MIN_SECONDS_BETWEEN_TRADES", 60)
MAX_TRADES_PER_DAY = _get_int("MAX_TRADES_PER_DAY", 4)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
STATE_FILE = os.getenv("STATE_FILE", "bot_state.json")
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
JOURNAL_PATH = os.getenv("JOURNAL_PATH", "journals/trade_journal.csv")
LOG_TRADES = os.getenv("LOG_TRADES", "true").lower() == "true"
ENFORCE_TRADE_LIMITS = os.getenv("ENFORCE_TRADE_LIMITS", "true").lower() == "true"