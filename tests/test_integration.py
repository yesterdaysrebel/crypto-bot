"""Integration tests."""
import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock

from config.config import Config
from collectors.delta_client import DeltaExchangeClient
from collectors.data_collector import DataCollector
from features.ml_models import MLPredictor
from strategies.ml_strategy import MLStrategy


class TestIntegration:
    """Integration tests."""
    
    def test_data_collection_to_ml_training(self, temp_dir, mock_config, sample_ohlc_data):
        """Test end-to-end data collection to ML training."""
        # Mock client
        client = Mock(spec=DeltaExchangeClient)
        client.get_ohlc.return_value = [
            {
                'time': int(pd.Timestamp.now().timestamp()),
                'open': 50000.0,
                'high': 50050.0,
                'low': 49950.0,
                'close': 50025.0,
                'volume': 1000.0
            }
        ] * 100
        
        # Collect data
        collector = DataCollector(client, mock_config)
        df = collector.collect_ohlc('BTCUSD', resolution='1h', hours=24, save=True)
        
        assert not df.empty
        
        # Prepare features
        from features.feature_engineering import FeatureEngineer
        feature_engineer = FeatureEngineer()
        features = feature_engineer.prepare_features(df)
        labels = feature_engineer.create_labels(df)
        
        assert not features.empty
        assert not labels.empty
        
        # Train model
        predictor = MLPredictor(model_path=str(temp_dir / "models"))
        metrics = predictor.train(features, labels)
        
        assert predictor.is_trained
        assert 'train_accuracy' in metrics
    
    def test_ml_strategy_end_to_end(self, temp_dir, mock_config, sample_ohlc_data):
        """Test ML strategy end-to-end."""
        # Train model
        from features.feature_engineering import FeatureEngineer
        feature_engineer = FeatureEngineer()
        features = feature_engineer.prepare_features(sample_ohlc_data)
        labels = feature_engineer.create_labels(sample_ohlc_data)
        
        common_idx = features.index.intersection(labels.index)
        features_train = features.loc[common_idx]
        labels_train = labels.loc[common_idx]
        
        predictor = MLPredictor(model_path=str(temp_dir / "models"))
        predictor.train(features_train, labels_train)
        
        # Create strategy
        strategy_config = {
            'confidence_threshold': 0.6,
            'position_size': 0.1,
            'stop_loss_pct': 0.02,
            'take_profit_pct': 0.04
        }
        
        strategy = MLStrategy("ML_BTCUSD", strategy_config, predictor)
        
        # Generate signal
        data = {
            'symbol': 'BTCUSD',
            'ohlc': sample_ohlc_data,
            'orderbook': {},
            'ticker': {}
        }
        
        signal = strategy.generate_signal(data)
        
        assert signal is not None
        assert signal.symbol == 'BTCUSD'
        assert signal.action in ['buy', 'sell', 'hold']
    
    @patch('collectors.delta_client.requests.Session')
    def test_full_workflow(self, mock_session, temp_dir, mock_config):
        """Test full workflow from API to signal generation."""
        import pandas as pd
        
        # Mock API responses
        mock_response = Mock()
        mock_response.json.return_value = {
            'result': [
                {
                    'time': int(pd.Timestamp.now().timestamp()) - i * 3600,
                    'open': 50000.0 - i * 10,
                    'high': 50050.0 - i * 10,
                    'low': 49950.0 - i * 10,
                    'close': 50025.0 - i * 10,
                    'volume': 1000.0
                }
                for i in range(100)
            ]
        }
        mock_response.raise_for_status = Mock()
        
        mock_session_instance = Mock()
        mock_session_instance.get.return_value = mock_response
        mock_session_instance.headers = {}
        mock_session.return_value = mock_session_instance
        
        # Initialize client
        client = DeltaExchangeClient("test_key", "test_secret")
        
        # Collect data
        collector = DataCollector(client, mock_config)
        df = collector.collect_ohlc('BTCUSD', resolution='1h', hours=24, save=True)
        
        assert not df.empty
        
        # Train model
        from features.feature_engineering import FeatureEngineer
        feature_engineer = FeatureEngineer()
        features = feature_engineer.prepare_features(df)
        labels = feature_engineer.create_labels(df)
        
        common_idx = features.index.intersection(labels.index)
        features_train = features.loc[common_idx]
        labels_train = labels.loc[common_idx]
        
        predictor = MLPredictor(model_path=str(temp_dir / "models"))
        predictor.train(features_train, labels_train)
        
        # Generate signal
        strategy_config = {
            'confidence_threshold': 0.6,
            'position_size': 0.1,
            'stop_loss_pct': 0.02,
            'take_profit_pct': 0.04
        }
        
        strategy = MLStrategy("ML_BTCUSD", strategy_config, predictor)
        signal = strategy.generate_signal({'symbol': 'BTCUSD', 'ohlc': df, 'orderbook': {}, 'ticker': {}})
        
        assert signal is not None

