"""Example mean reversion strategy."""
from typing import Dict
import logging

from strategies.base_strategy import BaseStrategy, Signal

logger = logging.getLogger(__name__)


class MeanReversionStrategy(BaseStrategy):
    """Simple mean reversion strategy based on Bollinger Bands."""
    
    def __init__(self, name: str, config: Dict):
        """
        Initialize mean reversion strategy.
        
        Args:
            name: Strategy name
            config: Strategy configuration
        """
        super().__init__(name, config)
        self.bb_period = config.get('bb_period', 20)
        self.bb_std = config.get('bb_std', 2.0)
        self.position_size = config.get('position_size', 0.1)
    
    def generate_signal(self, data: Dict) -> Signal:
        """
        Generate signal based on mean reversion.
        
        Strategy: Buy when price is below lower Bollinger Band,
                  Sell when price is above upper Bollinger Band.
        """
        try:
            ohlc_df = data.get('ohlc')
            if ohlc_df is None or ohlc_df.empty or len(ohlc_df) < self.bb_period:
                return Signal(
                    symbol=data.get('symbol', ''),
                    action='hold',
                    size=0,
                    reason='Insufficient data'
                )
            
            # Calculate Bollinger Bands
            close = ohlc_df['close']
            sma = close.rolling(window=self.bb_period).mean()
            std = close.rolling(window=self.bb_period).std()
            upper_band = sma + (std * self.bb_std)
            lower_band = sma - (std * self.bb_std)
            
            current_price = float(close.iloc[-1])
            current_upper = float(upper_band.iloc[-1])
            current_lower = float(lower_band.iloc[-1])
            
            symbol = data.get('symbol', '')
            existing_position = self.get_position(symbol)
            
            # Generate signal
            if current_price <= current_lower:
                # Price below lower band - buy signal
                if not existing_position or existing_position.get('side') != 'buy':
                    return Signal(
                        symbol=symbol,
                        action='buy',
                        size=self.position_size,
                        price=current_price,
                        stop_loss=current_price * 0.98,  # 2% stop loss
                        take_profit=current_price * 1.04,  # 4% take profit
                        confidence=0.7,
                        reason=f'Price {current_price:.2f} below lower band {current_lower:.2f}'
                    )
            
            elif current_price >= current_upper:
                # Price above upper band - sell signal
                if not existing_position or existing_position.get('side') != 'sell':
                    return Signal(
                        symbol=symbol,
                        action='sell',
                        size=self.position_size,
                        price=current_price,
                        stop_loss=current_price * 1.02,  # 2% stop loss
                        take_profit=current_price * 0.96,  # 4% take profit
                        confidence=0.7,
                        reason=f'Price {current_price:.2f} above upper band {current_upper:.2f}'
                    )
            
            return Signal(
                symbol=symbol,
                action='hold',
                size=0,
                reason='Price within bands'
            )
        
        except Exception as e:
            logger.error(f"Error generating mean reversion signal: {e}")
            return Signal(
                symbol=data.get('symbol', ''),
                action='hold',
                size=0,
                reason=f'Error: {str(e)}'
            )
    
    def should_close_position(self, position: Dict, data: Dict) -> bool:
        """
        Close position if price returns to mean.
        """
        try:
            ohlc_df = data.get('ohlc')
            if ohlc_df is None or ohlc_df.empty:
                return False
            
            # Calculate Bollinger Bands
            close = ohlc_df['close']
            sma = close.rolling(window=self.bb_period).mean()
            current_price = float(close.iloc[-1])
            current_mean = float(sma.iloc[-1])
            
            side = position.get('side', '')
            entry_price = position.get('entry_price', 0)
            
            # Close if price returns to mean and we have profit
            if side == 'buy':
                if current_price >= current_mean and current_price > entry_price * 1.01:
                    return True
            elif side == 'sell':
                if current_price <= current_mean and current_price < entry_price * 0.99:
                    return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error checking position close: {e}")
            return False

