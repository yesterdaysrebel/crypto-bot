"""Tests for Delta Exchange API client."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from datetime import datetime

from collectors.delta_client import DeltaExchangeClient


class TestDeltaExchangeClient:
    """Test Delta Exchange API client."""
    
    def test_init(self):
        """Test client initialization."""
        client = DeltaExchangeClient(
            api_key="test_key",
            api_secret="test_secret",
            base_url="https://api.delta.exchange"
        )
        assert client.api_key == "test_key"
        assert client.api_secret == "test_secret"
        assert client.base_url == "https://api.delta.exchange"
        assert "api-key" in client.session.headers
    
    @patch('collectors.delta_client.requests.Session')
    def test_get_products(self, mock_session):
        """Test getting products."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'result': [
                {'id': 27, 'symbol': 'BTCUSD', 'product_type': 'perpetual_futures'},
                {'id': 3136, 'symbol': 'ETHUSD', 'product_type': 'perpetual_futures'}
            ]
        }
        mock_response.raise_for_status = Mock()
        
        mock_session_instance = Mock()
        mock_session_instance.get.return_value = mock_response
        mock_session_instance.headers = {}
        mock_session.return_value = mock_session_instance
        
        client = DeltaExchangeClient("test_key", "test_secret")
        products = client.get_products()
        
        assert len(products) == 2
        assert products[0]['symbol'] == 'BTCUSD'
    
    @patch('collectors.delta_client.requests.Session')
    def test_get_ohlc(self, mock_session):
        """Test getting OHLC data."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'result': [
                {
                    'time': int(datetime.now().timestamp()),
                    'open': 50000.0,
                    'high': 50050.0,
                    'low': 49950.0,
                    'close': 50025.0,
                    'volume': 1000.0
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        
        mock_session_instance = Mock()
        mock_session_instance.get.return_value = mock_response
        mock_session_instance.headers = {}
        mock_session.return_value = mock_session_instance
        
        client = DeltaExchangeClient("test_key", "test_secret")
        ohlc = client.get_ohlc('BTCUSD', resolution='1h', limit=100)
        
        assert len(ohlc) == 1
        assert ohlc[0]['close'] == 50025.0
    
    @patch('collectors.delta_client.requests.Session')
    def test_place_order(self, mock_session):
        """Test placing an order."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'result': {
                'id': 'order123',
                'product_id': 27,
                'size': 0.1,
                'side': 'buy',
                'status': 'open'
            }
        }
        mock_response.raise_for_status = Mock()
        
        mock_session_instance = Mock()
        mock_session_instance.post.return_value = mock_response
        mock_session_instance.headers = {}
        mock_session.return_value = mock_session_instance
        
        client = DeltaExchangeClient("test_key", "test_secret")
        order = client.place_order(
            product_id=27,
            size=0.1,
            side='buy',
            order_type='limit_order',
            limit_price=50000.0
        )
        
        assert order['id'] == 'order123'
        assert order['side'] == 'buy'
    
    @patch('collectors.delta_client.requests.Session')
    def test_get_positions(self, mock_session):
        """Test getting positions."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'result': [
                {
                    'product_id': 27,
                    'size': 0.1,
                    'entry_price': 50000.0,
                    'mark_price': 50050.0,
                    'unrealised_pnl': 5.0
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        
        mock_session_instance = Mock()
        mock_session_instance.get.return_value = mock_response
        mock_session_instance.headers = {}
        mock_session.return_value = mock_session_instance
        
        client = DeltaExchangeClient("test_key", "test_secret")
        # get_positions now requires at least one parameter (product_id or underlying_asset_symbol)
        positions = client.get_positions(product_id=27)
        
        assert len(positions) == 1
        assert positions[0]['product_id'] == 27
    
    def test_sign_message(self):
        """Test message signing."""
        client = DeltaExchangeClient("test_key", "test_secret")
        signature, timestamp = client._sign_message(
            method='GET',
            path='/v2/products',
            query_string='',
            body=''
        )
        
        assert signature is not None
        assert len(signature) == 64  # SHA256 hex length
        assert timestamp is not None

