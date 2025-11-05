"""Base strategy class for trading strategies."""
from abc import ABC, abstractmethod
from typing import Dict, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    """Trading signal."""
    symbol: str
    action: str  # "buy", "sell", "hold"
    size: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    confidence: float = 0.0
    reason: str = ""


class BaseStrategy(ABC):
    """Base class for trading strategies."""
    
    def __init__(self, name: str, config: Dict):
        """
        Initialize strategy.
        
        Args:
            name: Strategy name
            config: Strategy configuration
        """
        self.name = name
        self.config = config
        self.is_active = True
        self.positions = {}
    
    @abstractmethod
    def generate_signal(self, data: Dict) -> Signal:
        """
        Generate trading signal based on market data.
        
        Args:
            data: Market data dictionary with keys like 'ohlc', 'orderbook', 'ticker', etc.
            
        Returns:
            Trading signal
        """
    
    @abstractmethod
    def should_close_position(self, position: Dict, data: Dict) -> bool:
        """
        Check if a position should be closed.
        
        Args:
            position: Current position
            data: Market data
            
        Returns:
            True if position should be closed
        """
    
    def update_position(self, symbol: str, position: Dict):
        """Update position tracking."""
        self.positions[symbol] = position
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get current position for symbol."""
        return self.positions.get(symbol)
    
    def activate(self):
        """Activate strategy."""
        self.is_active = True
        logger.info(f"Strategy {self.name} activated")
    
    def deactivate(self):
        """Deactivate strategy."""
        self.is_active = False
        logger.info(f"Strategy {self.name} deactivated")

