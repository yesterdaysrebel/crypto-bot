"""Tests for configuration management."""
import pytest
import os
from unittest.mock import patch

from config.config import Config, DeltaExchangeConfig, TradingConfig, MLConfig


class TestDeltaExchangeConfig:
    """Test Delta Exchange configuration."""
    
    def test_from_env(self):
        """Test loading from environment variables."""
        with patch.dict(os.environ, {
            'DELTA_API_KEY': 'test_key',
            'DELTA_API_SECRET': 'test_secret',
            'DELTA_BASE_URL': 'https://api.delta.exchange',
            'DELTA_TESTNET': 'false'
        }):
            config = DeltaExchangeConfig.from_env()
            
            assert config.api_key == 'test_key'
            assert config.api_secret == 'test_secret'
            assert config.base_url == 'https://api.delta.exchange'
            assert config.testnet is False
    
    def test_from_env_defaults(self):
        """Test loading with default values."""
        with patch.dict(os.environ, {}, clear=True):
            config = DeltaExchangeConfig.from_env()
            
            assert config.api_key == ''
            assert config.base_url == 'https://api.delta.exchange'
            assert config.testnet is False


class TestTradingConfig:
    """Test trading configuration."""
    
    def test_from_env(self):
        """Test loading from environment variables."""
        with patch.dict(os.environ, {
            'TRADING_PRODUCTS': 'BTCUSD,ETHUSD',
            'MAX_POSITION_SIZE': '2000.0',
            'MAX_LEVERAGE': '20',
            'RISK_PER_TRADE': '0.03',
            'DEFAULT_TIMEFRAME': '4h'
        }):
            config = TradingConfig.from_env()
            
            assert config.max_position_size == 2000.0
            assert config.max_leverage == 20
            assert config.risk_per_trade == 0.03
            assert config.default_timeframe == '4h'
            assert 'BTCUSD' in config.products
            assert 'ETHUSD' in config.products
    
    def test_from_env_defaults(self):
        """Test loading with default values."""
        with patch.dict(os.environ, {}, clear=True):
            config = TradingConfig.from_env()
            
            assert config.max_position_size == 1000.0
            assert config.max_leverage == 10
            assert config.risk_per_trade == 0.02
            assert config.default_timeframe == '1h'
            assert 'BTCUSD' in config.products


class TestMLConfig:
    """Test ML configuration."""
    
    def test_from_env(self):
        """Test loading from environment variables."""
        with patch.dict(os.environ, {
            'ML_MODEL_PATH': 'custom_models',
            'ML_RETRAIN_INTERVAL_HOURS': '48',
            'ML_FEATURE_WINDOW': '200',
            'ML_PREDICTION_THRESHOLD': '0.7'
        }):
            config = MLConfig.from_env()
            
            assert config.model_path == 'custom_models'
            assert config.retrain_interval_hours == 48
            assert config.feature_window == 200
            assert config.prediction_threshold == 0.7
    
    def test_from_env_defaults(self):
        """Test loading with default values."""
        with patch.dict(os.environ, {}, clear=True):
            config = MLConfig.from_env()
            
            assert config.model_path == 'models'
            assert config.retrain_interval_hours == 24
            assert config.feature_window == 100
            assert config.prediction_threshold == 0.6


class TestConfig:
    """Test main configuration."""
    
    def test_init(self, temp_dir):
        """Test configuration initialization."""
        with patch.dict(os.environ, {
            'DELTA_API_KEY': 'test_key',
            'DELTA_API_SECRET': 'test_secret'
        }):
            config = Config()
            
            assert config.delta is not None
            assert config.trading is not None
            assert config.ml is not None
    
    def test_validate_success(self, temp_dir):
        """Test successful validation."""
        with patch.dict(os.environ, {
            'DELTA_API_KEY': 'test_key',
            'DELTA_API_SECRET': 'test_secret'
        }):
            config = Config()
            assert config.validate() is True
    
    def test_validate_failure(self, temp_dir):
        """Test validation failure with missing credentials."""
        with patch.dict(os.environ, {}, clear=True):
            config = Config()
            with pytest.raises(ValueError, match="API key and secret must be set"):
                config.validate()

