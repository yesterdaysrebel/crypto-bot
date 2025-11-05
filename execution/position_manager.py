"""Position management."""
import logging
from typing import Dict, Optional, List

from collectors.delta_client import DeltaExchangeClient

logger = logging.getLogger(__name__)

# Import trade logger if available
try:
    from trade_logging.trade_logger import TradeLogger
    TRADE_LOGGER_AVAILABLE = True
except ImportError:
    TRADE_LOGGER_AVAILABLE = False


class PositionManager:
    """Manages trading positions."""
    
    def __init__(
        self,
        client: DeltaExchangeClient,
        trade_logger: Optional['TradeLogger'] = None
    ):
        """
        Initialize position manager.
        
        Args:
            client: Delta Exchange client
            trade_logger: Optional trade logger for tracking trades
        """
        self.client = client
        self.positions = {}
        self.trade_logger = trade_logger
    
    def update_positions(self) -> Dict[str, Dict]:
        """
        Update positions from exchange.
        
        Returns:
            Dictionary of positions keyed by symbol
        """
        try:
            positions = self.client.get_positions()
            
            # Convert to dictionary keyed by symbol
            self.positions = {}
            for pos in positions:
                symbol = pos.get('product', {}).get('symbol', '')
                if symbol and float(pos.get('size', 0)) != 0:
                    self.positions[symbol] = {
                        'symbol': symbol,
                        'product_id': pos.get('product_id'),
                        'size': float(pos.get('size', 0)),
                        'entry_price': float(pos.get('entry_price', 0)),
                        'mark_price': float(pos.get('mark_price', 0)),
                        'liquidation_price': float(pos.get('liquidation_price', 0)),
                        'pnl': float(pos.get('unrealised_pnl', 0)),
                        'side': 'buy' if float(pos.get('size', 0)) > 0 else 'sell'
                    }
            
            return self.positions
        
        except Exception as e:
            logger.error(f"Error updating positions: {e}")
            return {}
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """
        Get position for a symbol.
        
        Args:
            symbol: Product symbol
            
        Returns:
            Position dictionary or None
        """
        self.update_positions()
        return self.positions.get(symbol)
    
    def get_all_positions(self) -> Dict[str, Dict]:
        """Get all positions."""
        self.update_positions()
        return self.positions
    
    def close_position(self, product_id: int, symbol: Optional[str] = None) -> bool:
        """
        Close a position.
        
        Args:
            product_id: Product ID
            symbol: Optional symbol for logging
            
        Returns:
            True if successful
        """
        try:
            # Get position before closing
            position = self.client.get_position(product_id)
            
            self.client.close_position(product_id)
            
            # Log trade closure
            if self.trade_logger and symbol and position:
                exit_price = float(position.get('mark_price', 0))
                pnl = float(position.get('unrealised_pnl', 0))
                pnl_pct = (pnl / (float(position.get('size', 1)) * float(position.get('entry_price', 1)))) * 100 if position.get('entry_price') else 0
                
                self.trade_logger.log_position_closed(
                    symbol=symbol,
                    exit_price=exit_price,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                    reason='Manual close'
                )
            
            logger.info(f"Position closed: {product_id}")
            return True
        except Exception as e:
            logger.error(f"Error closing position {product_id}: {e}")
            return False
    
    def get_position_pnl(self, symbol: str) -> float:
        """
        Get P&L for a position.
        
        Args:
            symbol: Product symbol
            
        Returns:
            P&L value
        """
        position = self.get_position(symbol)
        if position:
            return position.get('pnl', 0.0)
        return 0.0
    
    def get_total_pnl(self) -> float:
        """Get total P&L across all positions."""
        self.update_positions()
        return sum(pos.get('pnl', 0.0) for pos in self.positions.values())

