"""Tests for data collector."""
import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch

from collectors.data_collector import DataCollector
from collectors.delta_client import DeltaExchangeClient


class TestDataCollector:
    """Test data collector."""
    
    def test_init(self, temp_dir, mock_config):
        """Test data collector initialization."""
        client = Mock(spec=DeltaExchangeClient)
        collector = DataCollector(client, mock_config)
        
        assert collector.client == client
        assert collector.config == mock_config
        assert collector.data_dir.exists()
    
    def test_collect_ohlc(self, mock_delta_client, mock_config):
        """Test collecting OHLC data."""
        collector = DataCollector(mock_delta_client, mock_config)
        df = collector.collect_ohlc('BTCUSD', resolution='1h', hours=24, save=True)
        
        assert not df.empty
        assert 'open' in df.columns
        assert 'high' in df.columns
        assert 'low' in df.columns
        assert 'close' in df.columns
        assert 'volume' in df.columns
    
    def test_collect_ohlc_saves_to_disk(self, mock_delta_client, mock_config):
        """Test that OHLC data is saved to disk."""
        collector = DataCollector(mock_delta_client, mock_config)
        df = collector.collect_ohlc('BTCUSD', resolution='1h', hours=24, save=True)
        
        file_path = mock_config.data_dir / "BTCUSD_1h_ohlc.csv"
        assert file_path.exists()
        
        # Load and verify
        loaded_df = pd.read_csv(file_path, index_col='time', parse_dates=True)
        assert not loaded_df.empty
        assert len(loaded_df) == len(df)
    
    def test_load_historical_data(self, mock_delta_client, mock_config, sample_ohlc_data):
        """Test loading historical data from disk."""
        collector = DataCollector(mock_delta_client, mock_config)
        
        # Save sample data first (ensure index is named 'time')
        file_path = mock_config.data_dir / "BTCUSD_1h_ohlc.csv"
        sample_ohlc_data.index.name = 'time'
        sample_ohlc_data.to_csv(file_path)
        
        # Load it back
        loaded_df = collector.load_historical_data('BTCUSD', resolution='1h')
        
        assert not loaded_df.empty
        assert len(loaded_df) == len(sample_ohlc_data)
    
    def test_load_historical_data_nonexistent(self, mock_delta_client, mock_config):
        """Test loading non-existent historical data."""
        collector = DataCollector(mock_delta_client, mock_config)
        df = collector.load_historical_data('NONEXISTENT', resolution='1h')
        
        assert df.empty
    
    def test_update_historical_data(self, mock_delta_client, mock_config, sample_ohlc_data):
        """Test updating historical data."""
        collector = DataCollector(mock_delta_client, mock_config)
        
        # Save initial data (ensure index is named 'time')
        file_path = mock_config.data_dir / "BTCUSD_1h_ohlc.csv"
        sample_ohlc_data.index.name = 'time'
        sample_ohlc_data.to_csv(file_path)
        
        # Mock new data collection
        mock_delta_client.get_ohlc.return_value = [
            {
                'time': int(pd.Timestamp.now().timestamp()),
                'open': 51000.0,
                'high': 51050.0,
                'low': 50950.0,
                'close': 51025.0,
                'volume': 1100.0
            }
        ]
        
        # Update historical data
        updated_df = collector.update_historical_data('BTCUSD', resolution='1h')
        
        assert not updated_df.empty
        assert len(updated_df) >= len(sample_ohlc_data)
    
    def test_collect_orderbook(self, mock_delta_client, mock_config):
        """Test collecting orderbook data."""
        collector = DataCollector(mock_delta_client, mock_config)
        orderbook = collector.collect_orderbook('BTCUSD')
        
        assert 'buy' in orderbook or 'sell' in orderbook
    
    def test_get_ticker_data(self, mock_delta_client, mock_config):
        """Test getting ticker data."""
        collector = DataCollector(mock_delta_client, mock_config)
        ticker_df = collector.get_ticker_data(['BTCUSD'])
        
        assert not ticker_df.empty
        assert 'symbol' in ticker_df.columns or len(ticker_df) > 0

