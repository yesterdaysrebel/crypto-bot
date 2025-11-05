"""Tests for execution engine."""
import pytest
from unittest.mock import Mock, MagicMock

from execution.order_manager import OrderManager
from execution.position_manager import PositionManager
from strategies.base_strategy import Signal
from collectors.delta_client import DeltaExchangeClient


class TestOrderManager:
    """Test order manager."""
    
    def test_init(self, mock_config):
        """Test order manager initialization."""
        client = Mock(spec=DeltaExchangeClient)
        manager = OrderManager(client, mock_config)
        
        assert manager.client == client
        assert manager.config == mock_config
        assert manager.active_orders == {}
        assert manager.order_history == []
    
    def test_place_order_from_signal(self, mock_config):
        """Test placing order from signal."""
        client = Mock(spec=DeltaExchangeClient)
        client.place_order.return_value = {'id': 'order123', 'status': 'open'}
        
        manager = OrderManager(client, mock_config)
        
        signal = Signal(
            symbol='BTCUSD',
            action='buy',
            size=0.1,
            price=50000.0,
            stop_loss=49000.0,
            take_profit=52000.0,
            confidence=0.8,
            reason='ML prediction'
        )
        
        order = manager.place_order_from_signal(signal, product_id=27)
        
        assert order is not None
        assert order['id'] == 'order123'
        assert len(manager.active_orders) == 1
        assert len(manager.order_history) == 1
    
    def test_place_order_hold_signal(self, mock_config):
        """Test placing order with hold signal."""
        client = Mock(spec=DeltaExchangeClient)
        manager = OrderManager(client, mock_config)
        
        signal = Signal(
            symbol='BTCUSD',
            action='hold',
            size=0,
            confidence=0.5,
            reason='No signal'
        )
        
        order = manager.place_order_from_signal(signal, product_id=27)
        
        assert order is None
        assert len(manager.active_orders) == 0
    
    def test_cancel_order(self, mock_config):
        """Test cancelling order."""
        client = Mock(spec=DeltaExchangeClient)
        client.cancel_order.return_value = {'id': 'order123', 'status': 'cancelled'}
        
        manager = OrderManager(client, mock_config)
        manager.active_orders['order123'] = {
            'order': {'id': 'order123'},
            'signal': Mock(),
            'timestamp': Mock()
        }
        
        result = manager.cancel_order('order123')
        
        assert result is True
        assert 'order123' not in manager.active_orders
    
    def test_get_active_orders(self, mock_config):
        """Test getting active orders."""
        client = Mock(spec=DeltaExchangeClient)
        client.get_active_orders.return_value = [
            {'id': 'order1', 'status': 'open'},
            {'id': 'order2', 'status': 'open'}
        ]
        
        manager = OrderManager(client, mock_config)
        orders = manager.get_active_orders()
        
        assert len(orders) == 2


class TestPositionManager:
    """Test position manager."""
    
    def test_init(self):
        """Test position manager initialization."""
        client = Mock(spec=DeltaExchangeClient)
        manager = PositionManager(client)
        
        assert manager.client == client
        assert manager.positions == {}
    
    def test_update_positions(self):
        """Test updating positions."""
        client = Mock(spec=DeltaExchangeClient)
        client.get_positions.return_value = [
            {
                'product_id': 27,
                'product': {'symbol': 'BTCUSD'},
                'size': '0.1',
                'entry_price': '50000.0',
                'mark_price': '50050.0',
                'liquidation_price': '45000.0',
                'unrealised_pnl': '5.0'
            }
        ]
        
        manager = PositionManager(client)
        positions = manager.update_positions()
        
        assert 'BTCUSD' in positions
        assert positions['BTCUSD']['size'] == 0.1
        assert positions['BTCUSD']['pnl'] == 5.0
    
    def test_get_position(self):
        """Test getting position for symbol."""
        client = Mock(spec=DeltaExchangeClient)
        client.get_positions.return_value = [
            {
                'product_id': 27,
                'product': {'symbol': 'BTCUSD'},
                'size': '0.1',
                'entry_price': '50000.0',
                'mark_price': '50050.0',
                'unrealised_pnl': '5.0'
            }
        ]
        
        manager = PositionManager(client)
        position = manager.get_position('BTCUSD')
        
        assert position is not None
        assert position['symbol'] == 'BTCUSD'
    
    def test_get_position_nonexistent(self):
        """Test getting non-existent position."""
        client = Mock(spec=DeltaExchangeClient)
        client.get_positions.return_value = []
        
        manager = PositionManager(client)
        position = manager.get_position('NONEXISTENT')
        
        assert position is None
    
    def test_close_position(self):
        """Test closing position."""
        client = Mock(spec=DeltaExchangeClient)
        client.close_position.return_value = {'status': 'closed'}
        
        manager = PositionManager(client)
        result = manager.close_position(product_id=27)
        
        assert result is True
        client.close_position.assert_called_once_with(27)
    
    def test_get_total_pnl(self):
        """Test getting total P&L."""
        client = Mock(spec=DeltaExchangeClient)
        client.get_positions.return_value = [
            {
                'product_id': 27,
                'product': {'symbol': 'BTCUSD'},
                'size': '0.1',
                'entry_price': '50000.0',
                'mark_price': '50050.0',
                'unrealised_pnl': '5.0'
            },
            {
                'product_id': 3136,
                'product': {'symbol': 'ETHUSD'},
                'size': '0.5',
                'entry_price': '3000.0',
                'mark_price': '3010.0',
                'unrealised_pnl': '5.0'
            }
        ]
        
        manager = PositionManager(client)
        total_pnl = manager.get_total_pnl()
        
        assert total_pnl == 10.0  # 5.0 + 5.0

