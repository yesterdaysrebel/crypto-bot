"""Configuration management for the trading bot."""
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DeltaExchangeConfig:
    """Delta Exchange API configuration."""
    api_key: str
    api_secret: str
    base_url: str = "https://api.india.delta.exchange"
    testnet: bool = False
    
    @classmethod
    def from_env(cls) -> "DeltaExchangeConfig":
        """Load configuration from environment variables."""
        return cls(
            api_key=os.getenv("DELTA_API_KEY", ""),
            api_secret=os.getenv("DELTA_API_SECRET", ""),
            base_url=os.getenv("DELTA_BASE_URL", "https://api.india.delta.exchange"),
            testnet=os.getenv("DELTA_TESTNET", "false").lower() == "true"
        )


@dataclass
class TradingConfig:
    """Trading configuration."""
    max_position_size: float = 100.0  # USD
    max_leverage: int = 25
    risk_per_trade: float = 0.02  # 2% of capital
    default_timeframe: str = "5m"
    products: list[str] = None
    
    def __post_init__(self):
        if self.products is None:
            self.products = ["SOLUSD"]
    
    @classmethod
    def from_env(cls) -> "TradingConfig":
        """Load configuration from environment variables."""
        products_str = os.getenv("TRADING_PRODUCTS", "BTCUSD,ETHUSD")
        return cls(
            max_position_size=float(os.getenv("MAX_POSITION_SIZE", "1000.0")),
            max_leverage=int(os.getenv("MAX_LEVERAGE", "10")),
            risk_per_trade=float(os.getenv("RISK_PER_TRADE", "0.02")),
            default_timeframe=os.getenv("DEFAULT_TIMEFRAME", "1h"),
            products=[p.strip() for p in products_str.split(",")]
        )


@dataclass
class MLConfig:
    """ML/AI configuration."""
    model_path: str = "models"
    retrain_interval_hours: int = 24
    feature_window: int = 100  # Number of candles for features
    prediction_threshold: float = 0.6
    
    @classmethod
    def from_env(cls) -> "MLConfig":
        """Load configuration from environment variables."""
        return cls(
            model_path=os.getenv("ML_MODEL_PATH", "models"),
            retrain_interval_hours=int(os.getenv("ML_RETRAIN_INTERVAL_HOURS", "24")),
            feature_window=int(os.getenv("ML_FEATURE_WINDOW", "100")),
            prediction_threshold=float(os.getenv("ML_PREDICTION_THRESHOLD", "0.6"))
        )


class Config:
    """Main configuration class."""
    
    def __init__(self):
        self.delta = DeltaExchangeConfig.from_env()
        self.trading = TradingConfig.from_env()
        self.ml = MLConfig.from_env()
        self.data_dir = Path(os.getenv("DATA_DIR", "data"))
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # Create necessary directories
        self.data_dir.mkdir(exist_ok=True)
        Path(self.ml.model_path).mkdir(parents=True, exist_ok=True)
    
    def validate(self) -> bool:
        """Validate configuration."""
        if not self.delta.api_key or not self.delta.api_secret:
            raise ValueError("Delta Exchange API key and secret must be set")
        return True

