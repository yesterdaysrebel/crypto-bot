"""Trade logger for tracking all trades."""
import json
import csv
import sys
# CRITICAL: Import standard logging module first
# Remove our logging directory from sys.modules if it was imported
if 'logging' in sys.modules:
    if not hasattr(sys.modules['logging'], 'getLogger'):
        del sys.modules['logging']
# Now safely import standard logging
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Trade data structure."""
    timestamp: str
    symbol: str
    strategy: str
    action: str  # 'buy' or 'sell'
    size: float
    price: float
    order_type: str  # 'limit_order' or 'market_order'
    order_id: Optional[str] = None
    signal_confidence: Optional[float] = None
    signal_reason: Optional[str] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    commission: Optional[float] = None
    status: str = 'open'  # 'open', 'filled', 'cancelled', 'closed'
    entry_timestamp: Optional[str] = None
    exit_timestamp: Optional[str] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    duration: Optional[str] = None
    notes: Optional[str] = None


class TradeLogger:
    """Logger for tracking all trades."""
    
    def __init__(
        self,
        log_dir: str = "trade_logs",
        log_format: str = "json",  # 'json', 'csv', or 'both'
        enable_console: bool = True
    ):
        """
        Initialize trade logger.
        
        Args:
            log_dir: Directory to save trade logs
            log_format: Log format ('json', 'csv', or 'both')
            enable_console: Whether to log to console
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_format = log_format
        self.enable_console = enable_console
        
        # Create log files
        timestamp = datetime.now().strftime('%Y%m%d')
        if log_format in ['json', 'both']:
            self.json_log_file = self.log_dir / f"trades_{timestamp}.jsonl"
            self.json_log_file.touch()
            self.signals_json_log_file = self.log_dir / f"signals_{timestamp}.jsonl"
            self.signals_json_log_file.touch()
        
        if log_format in ['csv', 'both']:
            self.csv_log_file = self.log_dir / f"trades_{timestamp}.csv"
            if not self.csv_log_file.exists():
                self._initialize_csv_file()
            self.signals_csv_log_file = self.log_dir / f"signals_{timestamp}.csv"
            if not self.signals_csv_log_file.exists():
                self._initialize_signals_csv_file()
        
        # In-memory trade storage for quick access
        self.trades: List[Trade] = []
    
    def _initialize_csv_file(self):
        """Initialize CSV file with headers."""
        headers = [
            'timestamp', 'symbol', 'strategy', 'action', 'size', 'price',
            'order_type', 'order_id', 'signal_confidence', 'signal_reason',
            'stop_loss', 'take_profit', 'commission', 'status',
            'entry_timestamp', 'exit_timestamp', 'exit_price',
            'pnl', 'pnl_pct', 'duration', 'notes'
        ]
        
        with open(self.csv_log_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
    
    def _initialize_signals_csv_file(self):
        """Initialize signals CSV file with headers."""
        headers = [
            'timestamp', 'symbol', 'strategy', 'signal_action', 
            'signal_confidence', 'signal_reason', 'current_price'
        ]
        
        with open(self.signals_csv_log_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
    
    def log_order(
        self,
        symbol: str,
        strategy: str,
        action: str,
        size: float,
        price: float,
        order_type: str = 'limit_order',
        order_id: Optional[str] = None,
        signal_confidence: Optional[float] = None,
        signal_reason: Optional[str] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        commission: Optional[float] = None,
        notes: Optional[str] = None
    ) -> Trade:
        """
        Log a new order/trade entry.
        
        Args:
            symbol: Trading symbol
            strategy: Strategy name
            action: 'buy' or 'sell'
            size: Order size
            price: Order price
            order_type: Order type
            order_id: Order ID from exchange
            signal_confidence: Signal confidence score
            signal_reason: Reason for the signal
            stop_loss: Stop loss price
            take_profit: Take profit price
            commission: Commission paid
            notes: Additional notes
            
        Returns:
            Trade object
        """
        trade = Trade(
            timestamp=datetime.now().isoformat(),
            symbol=symbol,
            strategy=strategy,
            action=action,
            size=size,
            price=price,
            order_type=order_type,
            order_id=order_id,
            signal_confidence=signal_confidence,
            signal_reason=signal_reason,
            stop_loss=stop_loss,
            take_profit=take_profit,
            commission=commission,
            status='open',
            entry_timestamp=datetime.now().isoformat(),
            notes=notes
        )
        
        # Store in memory
        self.trades.append(trade)
        
        # Log to file
        self._write_trade(trade)
        
        # Console logging
        if self.enable_console:
            logger.info(
                f"ORDER: {action.upper()} {size} {symbol} @ ${price:.2f} "
                f"[Strategy: {strategy}] [Order ID: {order_id}]"
            )
        
        return trade
    
    def log_order_filled(
        self,
        order_id: str,
        filled_price: Optional[float] = None,
        filled_size: Optional[float] = None
    ):
        """Log order fill."""
        trade = self._find_trade_by_order_id(order_id)
        if trade:
            trade.status = 'filled'
            if filled_price:
                trade.price = filled_price
            if filled_size:
                trade.size = filled_size
            self._update_trade(trade)
            
            if self.enable_console:
                logger.info(f"ORDER FILLED: {order_id} @ ${filled_price:.2f}")
    
    def log_order_cancelled(self, order_id: str, reason: Optional[str] = None):
        """Log order cancellation."""
        trade = self._find_trade_by_order_id(order_id)
        if trade:
            trade.status = 'cancelled'
            if reason:
                trade.notes = f"{trade.notes or ''}; Cancelled: {reason}".strip('; ')
            self._update_trade(trade)
            
            if self.enable_console:
                logger.info(f"ORDER CANCELLED: {order_id} - {reason}")
    
    def log_position_closed(
        self,
        symbol: str,
        exit_price: float,
        pnl: Optional[float] = None,
        pnl_pct: Optional[float] = None,
        reason: Optional[str] = None
    ):
        """
        Log position closure.
        
        Args:
            symbol: Trading symbol
            exit_price: Exit price
            pnl: Profit/Loss
            pnl_pct: P&L percentage
            reason: Reason for closing
        """
        # Find open trades for this symbol
        open_trades = [t for t in self.trades if t.symbol == symbol and t.status in ['open', 'filled']]
        
        if not open_trades:
            logger.warning(f"No open trades found for {symbol}")
            return
        
        # Update all open trades for this symbol
        for trade in open_trades:
            trade.status = 'closed'
            trade.exit_timestamp = datetime.now().isoformat()
            trade.exit_price = exit_price
            
            if trade.entry_timestamp:
                entry_time = datetime.fromisoformat(trade.entry_timestamp)
                exit_time = datetime.now()
                duration = exit_time - entry_time
                trade.duration = str(duration)
            
            if pnl is not None:
                trade.pnl = pnl
            else:
                # Calculate P&L if not provided
                if trade.action == 'buy':
                    trade.pnl = (exit_price - trade.price) * trade.size
                else:  # sell
                    trade.pnl = (trade.price - exit_price) * trade.size
            
            if pnl_pct is not None:
                trade.pnl_pct = pnl_pct
            else:
                trade.pnl_pct = ((exit_price - trade.price) / trade.price) * 100 if trade.action == 'buy' else ((trade.price - exit_price) / trade.price) * 100
            
            if reason:
                trade.notes = f"{trade.notes or ''}; Closed: {reason}".strip('; ')
            
            self._update_trade(trade)
            
            if self.enable_console:
                logger.info(
                    f"POSITION CLOSED: {symbol} @ ${exit_price:.2f} "
                    f"P&L: ${trade.pnl:.2f} ({trade.pnl_pct:.2f}%) "
                    f"[Strategy: {trade.strategy}]"
                )
    
    def log_signal(
        self,
        symbol: str,
        strategy: str,
        signal_action: str,
        signal_confidence: float,
        signal_reason: str,
        current_price: float
    ):
        """
        Log a trading signal (before order placement).
        
        Args:
            symbol: Trading symbol
            strategy: Strategy name
            signal_action: Signal action ('buy', 'sell', 'hold')
            signal_confidence: Signal confidence
            signal_reason: Reason for signal
            current_price: Current market price
        """
        timestamp = datetime.now().isoformat()
        signal_data = {
            'timestamp': timestamp,
            'symbol': symbol,
            'strategy': strategy,
            'signal_action': signal_action,
            'signal_confidence': signal_confidence,
            'signal_reason': signal_reason,
            'current_price': current_price
        }
        
        # Write to JSON file
        if self.log_format in ['json', 'both']:
            with open(self.signals_json_log_file, 'a') as f:
                f.write(json.dumps(signal_data) + '\n')
        
        # Write to CSV file
        if self.log_format in ['csv', 'both']:
            with open(self.signals_csv_log_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    signal_data['timestamp'],
                    signal_data['symbol'],
                    signal_data['strategy'],
                    signal_data['signal_action'],
                    signal_data['signal_confidence'],
                    signal_data['signal_reason'],
                    signal_data['current_price']
                ])
        
        # Console logging
        if self.enable_console:
            logger.info(
                f"SIGNAL: {signal_action.upper()} {symbol} @ ${current_price:.2f} "
                f"[Strategy: {strategy}] [Confidence: {signal_confidence:.2f}] "
                f"[Reason: {signal_reason}]"
            )
    
    def _write_trade(self, trade: Trade):
        """Write trade to log files."""
        trade_dict = asdict(trade)
        
        # Write to JSON file
        if self.log_format in ['json', 'both']:
            with open(self.json_log_file, 'a') as f:
                f.write(json.dumps(trade_dict) + '\n')
        
        # Write to CSV file
        if self.log_format in ['csv', 'both']:
            with open(self.csv_log_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    trade_dict.get('timestamp'),
                    trade_dict.get('symbol'),
                    trade_dict.get('strategy'),
                    trade_dict.get('action'),
                    trade_dict.get('size'),
                    trade_dict.get('price'),
                    trade_dict.get('order_type'),
                    trade_dict.get('order_id'),
                    trade_dict.get('signal_confidence'),
                    trade_dict.get('signal_reason'),
                    trade_dict.get('stop_loss'),
                    trade_dict.get('take_profit'),
                    trade_dict.get('commission'),
                    trade_dict.get('status'),
                    trade_dict.get('entry_timestamp'),
                    trade_dict.get('exit_timestamp'),
                    trade_dict.get('exit_price'),
                    trade_dict.get('pnl'),
                    trade_dict.get('pnl_pct'),
                    trade_dict.get('duration'),
                    trade_dict.get('notes')
                ])
    
    def _update_trade(self, trade: Trade):
        """Update existing trade in logs."""
        # For simplicity, we append updates
        # In production, you might want to update the original entry
        self._write_trade(trade)
    
    def _find_trade_by_order_id(self, order_id: str) -> Optional[Trade]:
        """Find trade by order ID."""
        for trade in reversed(self.trades):  # Check most recent first
            if trade.order_id == order_id:
                return trade
        return None
    
    def get_trades(
        self,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Trade]:
        """
        Get trades with filters.
        
        Args:
            symbol: Filter by symbol
            strategy: Filter by strategy
            status: Filter by status
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            List of filtered trades
        """
        trades = self.trades
        
        if symbol:
            trades = [t for t in trades if t.symbol == symbol]
        if strategy:
            trades = [t for t in trades if t.strategy == strategy]
        if status:
            trades = [t for t in trades if t.status == status]
        if start_date:
            trades = [t for t in trades if datetime.fromisoformat(t.timestamp) >= start_date]
        if end_date:
            trades = [t for t in trades if datetime.fromisoformat(t.timestamp) <= end_date]
        
        return trades
    
    def get_trades_df(
        self,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Get trades as DataFrame.
        
        Args:
            symbol: Filter by symbol
            strategy: Filter by strategy
            status: Filter by status
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            DataFrame with trades
        """
        trades = self.get_trades(symbol, strategy, status, start_date, end_date)
        
        if not trades:
            return pd.DataFrame()
        
        trades_dict = [asdict(trade) for trade in trades]
        df = pd.DataFrame(trades_dict)
        
        # Convert timestamp columns
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        if 'entry_timestamp' in df.columns:
            df['entry_timestamp'] = pd.to_datetime(df['entry_timestamp'])
        if 'exit_timestamp' in df.columns:
            df['exit_timestamp'] = pd.to_datetime(df['exit_timestamp'])
        
        return df
    
    def load_trades_from_file(self, file_path: Optional[Path] = None) -> List[Trade]:
        """
        Load trades from log file.
        
        Args:
            file_path: Path to log file (defaults to latest JSON log)
            
        Returns:
            List of trades
        """
        if file_path is None:
            file_path = self.json_log_file
        
        if not file_path.exists():
            logger.warning(f"Log file not found: {file_path}")
            return []
        
        trades = []
        
        if file_path.suffix == '.jsonl':
            with open(file_path, 'r') as f:
                for line in f:
                    if line.strip():
                        trade_dict = json.loads(line)
                        trade = Trade(**trade_dict)
                        trades.append(trade)
        elif file_path.suffix == '.csv':
            df = pd.read_csv(file_path)
            for _, row in df.iterrows():
                trade_dict = row.to_dict()
                trade = Trade(**trade_dict)
                trades.append(trade)
        
        self.trades = trades
        return trades

