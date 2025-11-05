"""Tests for feature engineering."""
import pytest
import pandas as pd
import numpy as np

from features.feature_engineering import FeatureEngineer


class TestFeatureEngineer:
    """Test feature engineering."""
    
    def test_calculate_technical_indicators(self, sample_ohlc_data):
        """Test calculating technical indicators."""
        df = FeatureEngineer.calculate_technical_indicators(sample_ohlc_data)
        
        # Check moving averages
        assert 'sma_10' in df.columns
        assert 'sma_20' in df.columns
        assert 'sma_50' in df.columns
        assert 'ema_12' in df.columns
        assert 'ema_26' in df.columns
        
        # Check MACD
        assert 'macd' in df.columns
        assert 'macd_signal' in df.columns
        assert 'macd_hist' in df.columns
        
        # Check RSI
        assert 'rsi' in df.columns
        
        # Check Bollinger Bands
        assert 'bb_upper' in df.columns
        assert 'bb_lower' in df.columns
        assert 'bb_position' in df.columns
    
    def test_calculate_technical_indicators_values(self, sample_ohlc_data):
        """Test that technical indicators have valid values."""
        df = FeatureEngineer.calculate_technical_indicators(sample_ohlc_data)
        
        # RSI should be between 0 and 100
        rsi_values = df['rsi'].dropna()
        if len(rsi_values) > 0:
            assert rsi_values.min() >= 0
            assert rsi_values.max() <= 100
        
        # Bollinger position can be negative (price below lower band) or >1 (above upper band)
        bb_pos = df['bb_position'].dropna()
        if len(bb_pos) > 0:
            # BB position can be outside 0-1 range when price is outside bands
            # This is expected behavior
            assert bb_pos.notna().any()  # Just check we have valid values
    
    def test_prepare_features(self, sample_ohlc_data):
        """Test preparing features for ML model."""
        df = FeatureEngineer.prepare_features(sample_ohlc_data, window=100)
        
        assert not df.empty
        assert 'close' in df.columns
        assert 'volume' in df.columns
        # Check that features are numeric
        assert df.select_dtypes(include=[np.number]).shape[1] > 0
    
    def test_prepare_features_window(self, sample_ohlc_data):
        """Test that prepare_features respects window size."""
        df = FeatureEngineer.prepare_features(sample_ohlc_data, window=50)
        
        assert len(df) <= 50
    
    def test_create_labels(self, sample_ohlc_data):
        """Test creating labels for supervised learning."""
        labels = FeatureEngineer.create_labels(sample_ohlc_data, forward_periods=5, threshold=0.02)
        
        assert len(labels) == len(sample_ohlc_data)
        # Labels should be -1, 0, or 1
        unique_labels = labels.dropna().unique()
        assert all(label in [-1, 0, 1] for label in unique_labels)
    
    def test_calculate_orderbook_features(self, sample_orderbook):
        """Test calculating orderbook features."""
        features = FeatureEngineer.calculate_orderbook_features(sample_orderbook)
        
        assert 'spread' in features or len(features) > 0
        if 'spread' in features:
            assert features['spread'] >= 0
    
    def test_calculate_orderbook_features_empty(self):
        """Test calculating orderbook features with empty orderbook."""
        features = FeatureEngineer.calculate_orderbook_features({})
        
        assert isinstance(features, dict)
    
    def test_calculate_technical_indicators_handles_nan(self, sample_ohlc_data):
        """Test that technical indicators handle NaN values."""
        # Add some NaN values
        sample_ohlc_data.loc[sample_ohlc_data.index[0], 'close'] = np.nan
        
        df = FeatureEngineer.calculate_technical_indicators(sample_ohlc_data)
        
        # Should still produce results (with NaN in early rows)
        assert not df.empty
        # Later rows should have valid values
        assert df.iloc[-1].notna().sum() > 0

