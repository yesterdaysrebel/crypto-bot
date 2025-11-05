"""Backtesting engine for trading strategies."""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

from strategies.base_strategy import BaseStrategy, Signal
from collectors.data_collector import DataCollector

logger = logging.getLogger(__name__)


class Backtester:
    """Backtesting engine for trading strategies."""
    
    def __init__(
        self,
        initial_capital: float = 10000.0,
        commission: float = 0.001,  # 0.1% commission
        slippage: float = 0.0005,  # 0.05% slippage
        use_limit_orders: bool = True
    ):
        """
        Initialize backtester.
        
        Args:
            initial_capital: Starting capital
            commission: Commission rate per trade
            slippage: Slippage rate per trade
            use_limit_orders: Whether to simulate limit orders (vs market orders)
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.use_limit_orders = use_limit_orders
        
        self.current_capital = initial_capital
        self.positions = {}  # symbol -> position dict
        self.orders = []  # List of executed orders
        self.equity_curve = []  # Capital over time
        self.trades = []  # List of completed trades
        
    def reset(self):
        """Reset backtester state."""
        self.current_capital = self.initial_capital
        self.positions = {}
        self.orders = []
        self.equity_curve = []
        self.trades = []
    
    def _execute_order(
        self,
        signal: Signal,
        current_price: float,
        timestamp: pd.Timestamp
    ) -> Optional[Dict]:
        """
        Execute an order based on signal and current price.
        
        Args:
            signal: Trading signal
            current_price: Current market price
            timestamp: Timestamp of the order
            
        Returns:
            Executed order dict or None if not executed
        """
        if signal.action == 'hold' or signal.size == 0:
            return None
        
        # Calculate execution price
        if self.use_limit_orders and signal.price:
            # Limit order: execute if price is favorable
            if signal.action == 'buy':
                if current_price <= signal.price:
                    execution_price = signal.price
                else:
                    # Price moved away, order not filled
                    return None
            else:  # sell
                if current_price >= signal.price:
                    execution_price = signal.price
                else:
                    return None
        else:
            # Market order: execute at current price with slippage
            if signal.action == 'buy':
                execution_price = current_price * (1 + self.slippage)
            else:
                execution_price = current_price * (1 - self.slippage)
        
        # Calculate order value
        order_value = signal.size * execution_price
        commission_cost = order_value * self.commission
        
        # Check if we have enough capital (for buy orders)
        if signal.action == 'buy':
            total_cost = order_value + commission_cost
            if total_cost > self.current_capital:
                logger.warning(f"Insufficient capital for {signal.symbol} buy order")
                return None
        
        # Create order
        order = {
            'timestamp': timestamp,
            'symbol': signal.symbol,
            'action': signal.action,
            'size': signal.size,
            'price': execution_price,
            'value': order_value,
            'commission': commission_cost,
            'stop_loss': signal.stop_loss,
            'take_profit': signal.take_profit,
            'signal': signal
        }
        
        # Update capital
        if signal.action == 'buy':
            self.current_capital -= (order_value + commission_cost)
        else:  # sell
            self.current_capital += (order_value - commission_cost)
        
        # Update position
        self._update_position(order)
        
        self.orders.append(order)
        return order
    
    def _update_position(self, order: Dict):
        """Update position based on executed order."""
        symbol = order['symbol']
        
        if symbol not in self.positions:
            self.positions[symbol] = {
                'symbol': symbol,
                'side': order['action'],
                'size': order['size'],
                'entry_price': order['price'],
                'entry_timestamp': order['timestamp'],
                'stop_loss': order.get('stop_loss'),
                'take_profit': order.get('take_profit'),
                'orders': [order]
            }
        else:
            position = self.positions[symbol]
            
            # Check if we're closing the position
            if position['side'] != order['action']:
                # Close position
                self._close_position(symbol, order['price'], order['timestamp'])
            else:
                # Add to position
                total_size = position['size'] + order['size']
                total_value = (position['size'] * position['entry_price'] + 
                              order['size'] * order['price'])
                position['entry_price'] = total_value / total_size
                position['size'] = total_size
                position['orders'].append(order)
    
    def _close_position(self, symbol: str, exit_price: float, exit_timestamp: pd.Timestamp):
        """Close a position and record trade."""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        
        # Calculate P&L
        entry_value = position['size'] * position['entry_price']
        exit_value = position['size'] * exit_price
        commission_cost = exit_value * self.commission
        
        if position['side'] == 'buy':
            pnl = exit_value - entry_value - commission_cost
        else:  # sell (short)
            pnl = entry_value - exit_value - commission_cost
        
        # Update capital
        self.current_capital += exit_value - commission_cost
        
        # Record trade
        trade = {
            'symbol': symbol,
            'side': position['side'],
            'entry_price': position['entry_price'],
            'exit_price': exit_price,
            'size': position['size'],
            'entry_timestamp': position['entry_timestamp'],
            'exit_timestamp': exit_timestamp,
            'pnl': pnl,
            'pnl_pct': (pnl / entry_value) * 100,
            'duration': exit_timestamp - position['entry_timestamp']
        }
        
        self.trades.append(trade)
        
        # Remove position
        del self.positions[symbol]
    
    def _check_stop_loss_take_profit(
        self,
        symbol: str,
        current_price: float,
        timestamp: pd.Timestamp
    ):
        """Check if position should be closed due to stop loss or take profit."""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        stop_loss = position.get('stop_loss')
        take_profit = position.get('take_profit')
        
        if not stop_loss and not take_profit:
            return
        
        should_close = False
        
        if position['side'] == 'buy':
            if stop_loss and current_price <= stop_loss:
                should_close = True
            if take_profit and current_price >= take_profit:
                should_close = True
        else:  # sell (short)
            if stop_loss and current_price >= stop_loss:
                should_close = True
            if take_profit and current_price <= take_profit:
                should_close = True
        
        if should_close:
            self._close_position(symbol, current_price, timestamp)
    
    def _calculate_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """Calculate current portfolio value."""
        portfolio_value = self.current_capital
        
        for symbol, position in self.positions.items():
            current_price = current_prices.get(symbol, position['entry_price'])
            position_value = position['size'] * current_price
            portfolio_value += position_value
        
        return portfolio_value
    
    def run(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,
        symbol: str,
        start_date: Optional[pd.Timestamp] = None,
        end_date: Optional[pd.Timestamp] = None
    ) -> Dict:
        """
        Run backtest on historical data.
        
        Args:
            strategy: Trading strategy to backtest
            data: Historical OHLC data
            symbol: Symbol being traded
            start_date: Start date for backtest
            end_date: End date for backtest
            
        Returns:
            Dictionary with backtest results
        """
        self.reset()
        
        # Filter data by date range
        if start_date:
            data = data[data.index >= start_date]
        if end_date:
            data = data[data.index <= end_date]
        
        if data.empty:
            logger.warning("No data available for backtest period")
            return {}
        
        logger.info(f"Running backtest for {symbol} from {data.index[0]} to {data.index[-1]}")
        logger.info(f"Initial capital: ${self.initial_capital:.2f}")
        
        # Track equity curve
        initial_portfolio_value = self.initial_capital
        
        # Iterate through historical data
        for i, (timestamp, row) in enumerate(data.iterrows()):
            current_price = float(row['close'])
            current_prices = {symbol: current_price}
            
            # Check stop loss / take profit for existing positions
            self._check_stop_loss_take_profit(symbol, current_price, timestamp)
            
            # Prepare market data for strategy
            market_data = {
                'symbol': symbol,
                'ohlc': data.iloc[:i+1],  # Historical data up to current point
                'orderbook': {},
                'ticker': {
                    'last_price': current_price,
                    'close': current_price
                },
                'timestamp': timestamp
            }
            
            # Update position in strategy
            if symbol in self.positions:
                position = self.positions[symbol].copy()
                position['entry_price'] = self.positions[symbol]['entry_price']
                position['mark_price'] = current_price
                strategy.update_position(symbol, position)
            
            # Generate signal
            try:
                signal = strategy.generate_signal(market_data)
            except Exception as e:
                logger.error(f"Error generating signal at {timestamp}: {e}")
                signal = Signal(symbol=symbol, action='hold', size=0)
            
            # Check if we should close existing position
            if symbol in self.positions:
                position = self.positions[symbol]
                try:
                    if strategy.should_close_position(position, market_data):
                        self._close_position(symbol, current_price, timestamp)
                except Exception as e:
                    logger.error(f"Error checking position close at {timestamp}: {e}")
            
            # Execute new order if signal is not hold
            if signal.action != 'hold' and signal.size > 0:
                # Check if we already have a position
                if symbol not in self.positions:
                    self._execute_order(signal, current_price, timestamp)
            
            # Record equity curve
            portfolio_value = self._calculate_portfolio_value(current_prices)
            self.equity_curve.append({
                'timestamp': timestamp,
                'capital': self.current_capital,
                'portfolio_value': portfolio_value,
                'equity': portfolio_value
            })
        
        # Close any remaining positions at the end
        final_price = float(data.iloc[-1]['close'])
        for symbol_pos in list(self.positions.keys()):
            self._close_position(symbol_pos, final_price, data.index[-1])
        
        # Calculate final metrics
        final_portfolio_value = self._calculate_portfolio_value({symbol: final_price})
        
        # Convert equity curve to DataFrame with proper index
        equity_df = pd.DataFrame(self.equity_curve)
        if 'timestamp' in equity_df.columns:
            equity_df['timestamp'] = pd.to_datetime(equity_df['timestamp'])
            equity_df.set_index('timestamp', inplace=True)
        
        return {
            'symbol': symbol,
            'start_date': data.index[0],
            'end_date': data.index[-1],
            'initial_capital': self.initial_capital,
            'final_capital': self.current_capital,
            'final_portfolio_value': final_portfolio_value,
            'total_return': final_portfolio_value - self.initial_capital,
            'total_return_pct': ((final_portfolio_value - self.initial_capital) / self.initial_capital) * 100,
            'trades': self.trades,
            'orders': self.orders,
            'equity_curve': equity_df,
            'positions': self.positions
        }

