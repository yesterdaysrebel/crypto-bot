"""Order management and execution."""
import logging
from typing import Dict, Optional, List
from datetime import datetime

from collectors.delta_client import DeltaExchangeClient
from strategies.base_strategy import Signal

logger = logging.getLogger(__name__)

# Import trade logger if available
try:
    from trade_logging.trade_logger import TradeLogger
    TRADE_LOGGER_AVAILABLE = True
except ImportError:
    TRADE_LOGGER_AVAILABLE = False


class OrderManager:
    """Manages order placement and execution."""
    
    def __init__(
        self,
        client: DeltaExchangeClient,
        config,
        trade_logger: Optional['TradeLogger'] = None
    ):
        """
        Initialize order manager.
        
        Args:
            client: Delta Exchange client
            config: Configuration object
            trade_logger: Optional trade logger for tracking trades
        """
        self.client = client
        self.config = config
        self.active_orders = {}
        self.order_history = []
        self.trade_logger = trade_logger
    
    def place_order_from_signal(self, signal: Signal, product_id: int) -> Optional[Dict]:
        """
        Place an order based on a trading signal.
        
        Args:
            signal: Trading signal
            product_id: Product ID
            
        Returns:
            Order response or None if failed
        """
        try:
            if signal.action == 'hold' or signal.size == 0:
                return None
            
            # Determine order type and parameters
            order_type = "limit_order" if signal.price else "market_order"
            side = signal.action
            
            # Calculate order size based on risk management
            max_position_size = self.config.trading.max_position_size
            risk_per_trade = self.config.trading.risk_per_trade
            
            # Adjust size based on risk
            if signal.price:
                risk_amount = max_position_size * risk_per_trade
                if signal.stop_loss and signal.action == 'buy':
                    risk_per_share = abs(signal.price - signal.stop_loss)
                    if risk_per_share > 0:
                        size = min(risk_amount / risk_per_share, signal.size)
                    else:
                        size = signal.size
                else:
                    size = signal.size
            else:
                size = signal.size
            
            # Place order
            order = self.client.place_order(
                product_id=product_id,
                size=size,
                side=side,
                order_type=order_type,
                limit_price=signal.price,
                reduce_only=False,
                time_in_force="gtc"
            )
            
            # Track order
            order_id = order.get('id')
            if order_id:
                self.active_orders[order_id] = {
                    'order': order,
                    'signal': signal,
                    'timestamp': datetime.now()
                }
                self.order_history.append({
                    'order_id': order_id,
                    'signal': signal,
                    'timestamp': datetime.now()
                })
            
            # Log trade
            if self.trade_logger:
                strategy_name = signal.reason.split(':')[0] if ':' in signal.reason else 'Unknown'
                self.trade_logger.log_order(
                    symbol=signal.symbol,
                    strategy=strategy_name,
                    action=side,
                    size=size,
                    price=signal.price or order.get('price', 0),
                    order_type=order_type,
                    order_id=order_id,
                    signal_confidence=signal.confidence,
                    signal_reason=signal.reason,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    commission=order.get('commission', 0)
                )
            
            logger.info(f"Order placed: {side} {size} {signal.symbol} at {signal.price}")
            return order
        
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.
        
        Args:
            order_id: Order ID
            
        Returns:
            True if successful
        """
        try:
            self.client.cancel_order(order_id)
            if order_id in self.active_orders:
                del self.active_orders[order_id]
            logger.info(f"Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    def get_active_orders(self, product_id: Optional[int] = None) -> List[Dict]:
        """
        Get active orders.
        
        Args:
            product_id: Optional product ID filter
            
        Returns:
            List of active orders
        """
        try:
            orders = self.client.get_active_orders(product_id)
            
            # Update tracked orders
            order_ids = {o.get('id') for o in orders}
            self.active_orders = {
                k: v for k, v in self.active_orders.items()
                if k in order_ids
            }
            
            return orders
        except Exception as e:
            logger.error(f"Error getting active orders: {e}")
            return []
    
    def cancel_all_orders(self, product_id: Optional[int] = None) -> int:
        """
        Cancel all active orders.
        
        Args:
            product_id: Optional product ID filter
            
        Returns:
            Number of orders cancelled
        """
        orders = self.get_active_orders(product_id)
        cancelled = 0
        
        for order in orders:
            order_id = order.get('id')
            if order_id and self.cancel_order(order_id):
                cancelled += 1
        
        return cancelled

