"""Trade analyzer for analyzing logged trades."""
import pandas as pd
import numpy as np
from typing import Dict, Optional, List
from datetime import datetime
import sys
# CRITICAL: Import standard logging module first
if 'logging' in sys.modules:
    if not hasattr(sys.modules['logging'], 'getLogger'):
        del sys.modules['logging']
import logging

from .trade_logger import TradeLogger

logger = logging.getLogger(__name__)


class TradeAnalyzer:
    """Analyze logged trades."""
    
    def __init__(self, trade_logger: TradeLogger):
        """
        Initialize trade analyzer.
        
        Args:
            trade_logger: Trade logger instance
        """
        self.trade_logger = trade_logger
    
    def get_trade_summary(
        self,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """
        Get summary statistics for trades.
        
        Args:
            symbol: Filter by symbol
            strategy: Filter by strategy
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            Dictionary with summary statistics
        """
        df = self.trade_logger.get_trades_df(symbol, strategy, None, start_date, end_date)
        
        if df.empty:
            return {}
        
        summary = {
            'total_trades': len(df),
            'open_trades': len(df[df['status'] == 'open']),
            'closed_trades': len(df[df['status'] == 'closed'])
        }
        
        # Closed trades statistics
        closed_df = df[df['status'] == 'closed'].copy()
        
        if not closed_df.empty and 'pnl' in closed_df.columns:
            closed_df['pnl'] = pd.to_numeric(closed_df['pnl'], errors='coerce')
            closed_df['pnl_pct'] = pd.to_numeric(closed_df['pnl_pct'], errors='coerce')
            
            summary['winning_trades'] = len(closed_df[closed_df['pnl'] > 0])
            summary['losing_trades'] = len(closed_df[closed_df['pnl'] < 0])
            summary['win_rate'] = (summary['winning_trades'] / len(closed_df) * 100) if len(closed_df) > 0 else 0
            
            summary['total_pnl'] = closed_df['pnl'].sum()
            summary['total_pnl_pct'] = closed_df['pnl_pct'].sum()
            summary['avg_pnl'] = closed_df['pnl'].mean()
            summary['avg_pnl_pct'] = closed_df['pnl_pct'].mean()
            
            summary['avg_win'] = closed_df[closed_df['pnl'] > 0]['pnl'].mean() if summary['winning_trades'] > 0 else 0
            summary['avg_loss'] = closed_df[closed_df['pnl'] < 0]['pnl'].mean() if summary['losing_trades'] > 0 else 0
            
            summary['largest_win'] = closed_df['pnl'].max()
            summary['largest_loss'] = closed_df['pnl'].min()
            
            # Profit factor
            total_profit = closed_df[closed_df['pnl'] > 0]['pnl'].sum() if summary['winning_trades'] > 0 else 0
            total_loss = abs(closed_df[closed_df['pnl'] < 0]['pnl'].sum()) if summary['losing_trades'] > 0 else 0
            summary['profit_factor'] = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Strategy breakdown
        if 'strategy' in df.columns:
            strategy_stats = df.groupby('strategy').agg({
                'pnl': ['count', 'sum', 'mean'] if 'pnl' in df.columns else 'count'
            })
            summary['strategy_breakdown'] = strategy_stats.to_dict()
        
        # Symbol breakdown
        if 'symbol' in df.columns:
            symbol_stats = df.groupby('symbol').agg({
                'pnl': ['count', 'sum', 'mean'] if 'pnl' in df.columns else 'count'
            })
            summary['symbol_breakdown'] = symbol_stats.to_dict()
        
        return summary
    
    def get_performance_by_strategy(self) -> pd.DataFrame:
        """Get performance metrics by strategy."""
        df = self.trade_logger.get_trades_df()
        
        if df.empty or 'strategy' not in df.columns:
            return pd.DataFrame()
        
        closed_df = df[df['status'] == 'closed'].copy()
        
        if closed_df.empty or 'pnl' not in closed_df.columns:
            return pd.DataFrame()
        
        closed_df['pnl'] = pd.to_numeric(closed_df['pnl'], errors='coerce')
        closed_df['pnl_pct'] = pd.to_numeric(closed_df['pnl_pct'], errors='coerce')
        
        performance = closed_df.groupby('strategy').agg({
            'pnl': ['count', 'sum', 'mean'],
            'pnl_pct': 'mean'
        }).reset_index()
        
        performance.columns = ['strategy', 'total_trades', 'total_pnl', 'avg_pnl', 'avg_pnl_pct']
        
        # Calculate win rate
        win_rates = closed_df.groupby('strategy').apply(
            lambda x: len(x[x['pnl'] > 0]) / len(x) * 100 if len(x) > 0 else 0
        ).reset_index(name='win_rate')
        
        performance = performance.merge(win_rates, on='strategy')
        
        return performance
    
    def get_performance_by_symbol(self) -> pd.DataFrame:
        """Get performance metrics by symbol."""
        df = self.trade_logger.get_trades_df()
        
        if df.empty or 'symbol' not in df.columns:
            return pd.DataFrame()
        
        closed_df = df[df['status'] == 'closed'].copy()
        
        if closed_df.empty or 'pnl' not in closed_df.columns:
            return pd.DataFrame()
        
        closed_df['pnl'] = pd.to_numeric(closed_df['pnl'], errors='coerce')
        closed_df['pnl_pct'] = pd.to_numeric(closed_df['pnl_pct'], errors='coerce')
        
        performance = closed_df.groupby('symbol').agg({
            'pnl': ['count', 'sum', 'mean'],
            'pnl_pct': 'mean'
        }).reset_index()
        
        performance.columns = ['symbol', 'total_trades', 'total_pnl', 'avg_pnl', 'avg_pnl_pct']
        
        # Calculate win rate
        win_rates = closed_df.groupby('symbol').apply(
            lambda x: len(x[x['pnl'] > 0]) / len(x) * 100 if len(x) > 0 else 0
        ).reset_index(name='win_rate')
        
        performance = performance.merge(win_rates, on='symbol')
        
        return performance
    
    def get_daily_pnl(self) -> pd.DataFrame:
        """Get daily P&L breakdown."""
        df = self.trade_logger.get_trades_df()
        
        if df.empty or 'exit_timestamp' not in df.columns:
            return pd.DataFrame()
        
        closed_df = df[df['status'] == 'closed'].copy()
        
        if closed_df.empty or 'pnl' not in closed_df.columns:
            return pd.DataFrame()
        
        closed_df['pnl'] = pd.to_numeric(closed_df['pnl'], errors='coerce')
        closed_df['date'] = pd.to_datetime(closed_df['exit_timestamp']).dt.date
        
        daily_pnl = closed_df.groupby('date')['pnl'].sum().reset_index()
        daily_pnl.columns = ['date', 'pnl']
        daily_pnl['cumulative_pnl'] = daily_pnl['pnl'].cumsum()
        
        return daily_pnl
    
    def print_summary(
        self,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None
    ):
        """Print trade summary to console."""
        summary = self.get_trade_summary(symbol, strategy)
        
        if not summary:
            print("No trades found")
            return
        
        print("\n" + "=" * 80)
        print("TRADE SUMMARY")
        print("=" * 80)
        print(f"Total Trades: {summary.get('total_trades', 0)}")
        print(f"Open Trades: {summary.get('open_trades', 0)}")
        print(f"Closed Trades: {summary.get('closed_trades', 0)}")
        
        if summary.get('closed_trades', 0) > 0:
            print(f"\nWin Rate: {summary.get('win_rate', 0):.2f}%")
            print(f"Winning Trades: {summary.get('winning_trades', 0)}")
            print(f"Losing Trades: {summary.get('losing_trades', 0)}")
            print(f"\nTotal P&L: ${summary.get('total_pnl', 0):,.2f}")
            print(f"Total P&L %: {summary.get('total_pnl_pct', 0):.2f}%")
            print(f"Average P&L: ${summary.get('avg_pnl', 0):,.2f}")
            print(f"Average P&L %: {summary.get('avg_pnl_pct', 0):.2f}%")
            print(f"\nAverage Win: ${summary.get('avg_win', 0):,.2f}")
            print(f"Average Loss: ${summary.get('avg_loss', 0):,.2f}")
            print(f"Profit Factor: {summary.get('profit_factor', 0):.2f}")
            print(f"\nLargest Win: ${summary.get('largest_win', 0):,.2f}")
            print(f"Largest Loss: ${summary.get('largest_loss', 0):,.2f}")
        print("=" * 80)

