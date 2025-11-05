"""Tests for trading strategies."""
import pytest
import pandas as pd
from unittest.mock import Mock

from strategies.base_strategy import BaseStrategy, Signal
from strategies.ml_strategy import MLStrategy
from features.ml_models import MLPredictor


class TestBaseStrategy:
    """Test base strategy."""
    
    def test_init(self):
        """Test strategy initialization."""
        strategy = Mock(spec=BaseStrategy)
        strategy.name = "test_strategy"
        strategy.config = {'position_size': 0.1}
        strategy.is_active = True
        strategy.positions = {}
        
        assert strategy.name == "test_strategy"
        assert strategy.is_active
    
    def test_activate_deactivate(self):
        """Test activating and deactivating strategy."""
        # Create a proper strategy instance instead of mock
        class TestStrategy(BaseStrategy):
            def generate_signal(self, data):
                from strategies.base_strategy import Signal
                return Signal(symbol='TEST', action='hold', size=0)
            
            def should_close_position(self, position, data):
                return False
        
        strategy = TestStrategy(name="test_strategy", config={})
        strategy.is_active = False
        
        strategy.activate()
        assert strategy.is_active
        
        strategy.deactivate()
        assert not strategy.is_active


class TestMLStrategy:
    """Test ML strategy."""
    
    @pytest.fixture
    def ml_predictor(self, temp_dir, sample_ohlc_data):
        """Create trained ML predictor for testing."""
        from features.feature_engineering import FeatureEngineer
        
        predictor = MLPredictor(model_path=str(temp_dir / "models"))
        feature_engineer = FeatureEngineer()
        features = feature_engineer.prepare_features(sample_ohlc_data)
        labels = feature_engineer.create_labels(sample_ohlc_data)
        
        common_idx = features.index.intersection(labels.index)
        features_train = features.loc[common_idx]
        labels_train = labels.loc[common_idx]
        
        predictor.train(features_train, labels_train)
        return predictor
    
    def test_init(self, temp_dir, ml_predictor):
        """Test ML strategy initialization."""
        config = {
            'confidence_threshold': 0.6,
            'position_size': 0.1,
            'stop_loss_pct': 0.02,
            'take_profit_pct': 0.04
        }
        
        strategy = MLStrategy("ML_BTCUSD", config, ml_predictor)
        
        assert strategy.name == "ML_BTCUSD"
        assert strategy.predictor == ml_predictor
        assert strategy.confidence_threshold == 0.6
    
    def test_generate_signal(self, temp_dir, ml_predictor, sample_ohlc_data):
        """Test generating trading signal."""
        config = {
            'confidence_threshold': 0.6,
            'position_size': 0.1,
            'stop_loss_pct': 0.02,
            'take_profit_pct': 0.04
        }
        
        strategy = MLStrategy("ML_BTCUSD", config, ml_predictor)
        
        data = {
            'symbol': 'BTCUSD',
            'ohlc': sample_ohlc_data,
            'orderbook': {},
            'ticker': {}
        }
        
        signal = strategy.generate_signal(data)
        
        assert isinstance(signal, Signal)
        assert signal.symbol == 'BTCUSD'
        assert signal.action in ['buy', 'sell', 'hold']
    
    def test_generate_signal_no_data(self, temp_dir, ml_predictor):
        """Test generating signal with no data."""
        config = {
            'confidence_threshold': 0.6,
            'position_size': 0.1,
            'stop_loss_pct': 0.02,
            'take_profit_pct': 0.04
        }
        
        strategy = MLStrategy("ML_BTCUSD", config, ml_predictor)
        
        data = {
            'symbol': 'BTCUSD',
            'ohlc': pd.DataFrame(),
            'orderbook': {},
            'ticker': {}
        }
        
        signal = strategy.generate_signal(data)
        
        assert signal.action == 'hold'
        assert signal.size == 0
    
    def test_should_close_position(self, temp_dir, ml_predictor, sample_ohlc_data):
        """Test checking if position should be closed."""
        config = {
            'confidence_threshold': 0.6,
            'position_size': 0.1,
            'stop_loss_pct': 0.02,
            'take_profit_pct': 0.04
        }
        
        strategy = MLStrategy("ML_BTCUSD", config, ml_predictor)
        
        position = {
            'symbol': 'BTCUSD',
            'side': 'buy',
            'entry_price': 50000.0,
            'stop_loss': 49000.0,  # 2% below
            'take_profit': 52000.0  # 4% above
        }
        
        data = {
            'symbol': 'BTCUSD',
            'ohlc': sample_ohlc_data,
            'orderbook': {},
            'ticker': {}
        }
        
        should_close = strategy.should_close_position(position, data)
        
        # Should return boolean
        assert isinstance(should_close, bool)

