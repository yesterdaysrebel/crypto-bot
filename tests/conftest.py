"""Pytest configuration and fixtures."""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock, MagicMock

from config.config import Config, DeltaExchangeConfig, TradingConfig, MLConfig


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_ohlc_data():
    """Sample OHLC data for testing."""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
    np.random.seed(42)
    
    # Generate realistic price data
    base_price = 50000
    prices = []
    current_price = base_price
    
    for _ in range(100):
        change = np.random.normal(0, 0.01)  # 1% volatility
        current_price *= (1 + change)
        prices.append(current_price)
    
    df = pd.DataFrame({
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
        'close': [p * (1 + np.random.normal(0, 0.002)) for p in prices],
        'volume': np.random.uniform(1000, 10000, 100)
    }, index=dates)
    
    # Ensure high >= close >= low and high >= open >= low
    df['high'] = df[['open', 'high', 'low', 'close']].max(axis=1)
    df['low'] = df[['open', 'high', 'low', 'close']].min(axis=1)
    
    return df


@pytest.fixture
def sample_orderbook():
    """Sample orderbook data."""
    return {
        'buy': [
            ['50000.0', '1.5'],
            ['49999.5', '2.0'],
            ['49999.0', '1.0']
        ],
        'sell': [
            ['50001.0', '1.2'],
            ['50001.5', '2.5'],
            ['50002.0', '1.8']
        ]
    }


@pytest.fixture
def sample_ticker():
    """Sample ticker data."""
    return {
        'symbol': 'BTCUSD',
        'open': 50000.0,
        'high': 50100.0,
        'low': 49900.0,
        'close': 50050.0,
        'volume': 1000.0,
        'last_price': 50050.0
    }


@pytest.fixture
def mock_config(temp_dir):
    """Mock configuration for testing."""
    config = Config()
    config.delta = DeltaExchangeConfig(
        api_key="test_api_key",
        api_secret="test_api_secret",
        base_url="https://api.india.delta.exchange"
    )
    config.trading = TradingConfig(
        max_position_size=1000.0,
        max_leverage=10,
        risk_per_trade=0.02,
        default_timeframe="1h",
        products=["BTCUSD", "ETHUSD"]
    )
    config.ml = MLConfig(
        model_path=str(temp_dir / "models"),
        retrain_interval_hours=24,
        feature_window=100,
        prediction_threshold=0.6
    )
    config.data_dir = temp_dir / "data"
    config.data_dir.mkdir(parents=True, exist_ok=True)
    return config


@pytest.fixture
def mock_delta_client():
    """Mock Delta Exchange client."""
    client = Mock()
    
    # Mock product list
    client.get_products.return_value = [
        {'id': 27, 'symbol': 'BTCUSD', 'product_type': 'perpetual_futures'},
        {'id': 3136, 'symbol': 'ETHUSD', 'product_type': 'perpetual_futures'}
    ]
    
    # Mock OHLC data
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
    ohlc_data = []
    for i, date in enumerate(dates):
        ohlc_data.append({
            'time': int(date.timestamp()),
            'open': 50000.0 + i * 10,
            'high': 50050.0 + i * 10,
            'low': 49950.0 + i * 10,
            'close': 50025.0 + i * 10,
            'volume': 1000.0
        })
    client.get_ohlc.return_value = ohlc_data
    
    # Mock orderbook
    client.get_l2_orderbook.return_value = {
        'buy': [['50000.0', '1.5'], ['49999.5', '2.0']],
        'sell': [['50001.0', '1.2'], ['50001.5', '2.5']]
    }
    
    # Mock ticker
    client.get_tickers.return_value = [{
        'symbol': 'BTCUSD',
        'open': 50000.0,
        'high': 50100.0,
        'low': 49900.0,
        'close': 50050.0,
        'volume': 1000.0
    }]
    
    # Mock authenticated endpoints
    client.get_wallet_balances.return_value = [{'asset': 'USDC', 'balance': 10000.0}]
    client.get_active_orders.return_value = []
    client.get_positions.return_value = []
    client.place_order.return_value = {'id': 'order123', 'status': 'open'}
    
    return client


@pytest.fixture
def sample_product_data():
    """Sample product data."""
    return {
        'id': 27,
        'symbol': 'BTCUSD',
        'product_type': 'perpetual_futures',
        'underlying_asset': {'symbol': 'BTC'},
        'settling_asset': {'symbol': 'USDC'}
    }


@pytest.fixture
def sample_position():
    """Sample position data."""
    return {
        'symbol': 'BTCUSD',
        'product_id': 27,
        'size': 0.1,
        'entry_price': 50000.0,
        'mark_price': 50050.0,
        'liquidation_price': 45000.0,
        'pnl': 5.0,
        'side': 'buy'
    }

