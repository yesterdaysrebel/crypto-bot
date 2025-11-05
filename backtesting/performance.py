"""Performance analysis for backtesting results."""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class PerformanceAnalyzer:
    """Analyze backtesting performance metrics."""
    
    def __init__(self, results: Dict):
        """
        Initialize performance analyzer.
        
        Args:
            results: Backtest results dictionary
        """
        self.results = results
        self.equity_curve = results.get('equity_curve', pd.DataFrame())
        self.trades = results.get('trades', [])
    
    def calculate_metrics(self) -> Dict:
        """
        Calculate comprehensive performance metrics.
        
        Returns:
            Dictionary of performance metrics
        """
        if self.equity_curve.empty:
            return {}
        
        metrics = {}
        
        # Basic metrics
        metrics['total_return'] = self.results.get('total_return', 0)
        metrics['total_return_pct'] = self.results.get('total_return_pct', 0)
        metrics['initial_capital'] = self.results.get('initial_capital', 0)
        metrics['final_portfolio_value'] = self.results.get('final_portfolio_value', 0)
        
        # Trade metrics
        if self.trades:
            trades_df = pd.DataFrame(self.trades)
            metrics['total_trades'] = len(self.trades)
            metrics['winning_trades'] = len(trades_df[trades_df['pnl'] > 0])
            metrics['losing_trades'] = len(trades_df[trades_df['pnl'] < 0])
            metrics['win_rate'] = (metrics['winning_trades'] / metrics['total_trades']) * 100 if metrics['total_trades'] > 0 else 0
            
            # Average P&L
            metrics['avg_win'] = trades_df[trades_df['pnl'] > 0]['pnl'].mean() if metrics['winning_trades'] > 0 else 0
            metrics['avg_loss'] = trades_df[trades_df['pnl'] < 0]['pnl'].mean() if metrics['losing_trades'] > 0 else 0
            metrics['avg_trade_pnl'] = trades_df['pnl'].mean()
            metrics['avg_trade_pnl_pct'] = trades_df['pnl_pct'].mean()
            
            # Profit factor
            total_profit = trades_df[trades_df['pnl'] > 0]['pnl'].sum() if metrics['winning_trades'] > 0 else 0
            total_loss = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum()) if metrics['losing_trades'] > 0 else 0
            metrics['profit_factor'] = total_profit / total_loss if total_loss > 0 else float('inf')
            
            # Largest win/loss
            metrics['largest_win'] = trades_df['pnl'].max()
            metrics['largest_loss'] = trades_df['pnl'].min()
            
            # Average trade duration
            if 'duration' in trades_df.columns:
                metrics['avg_trade_duration'] = trades_df['duration'].mean()
        else:
            metrics['total_trades'] = 0
            metrics['winning_trades'] = 0
            metrics['losing_trades'] = 0
            metrics['win_rate'] = 0
        
        # Equity curve metrics
        if not self.equity_curve.empty:
            # Handle both index and timestamp column
            if 'timestamp' in self.equity_curve.columns:
                equity_series = self.equity_curve.set_index('timestamp')['equity']
            else:
                equity_series = self.equity_curve['equity']
            
            # Ensure index is datetime
            if not isinstance(equity_series.index, pd.DatetimeIndex):
                try:
                    equity_series.index = pd.to_datetime(equity_series.index)
                except (ValueError, TypeError):
                    # If index can't be converted to datetime, create a new one
                    # Assume hourly data starting from first timestamp
                    if 'timestamp' in self.equity_curve.columns:
                        equity_series.index = pd.to_datetime(self.equity_curve['timestamp'])
                    else:
                        # Create a dummy datetime index
                        equity_series.index = pd.date_range(start='2024-01-01', periods=len(equity_series), freq='1h')
            
            equity = equity_series
            
            # Drawdown
            running_max = equity.expanding().max()
            drawdown = equity - running_max
            drawdown_pct = (drawdown / running_max) * 100
            
            metrics['max_drawdown'] = drawdown.min()
            metrics['max_drawdown_pct'] = drawdown_pct.min()
            
            # Sharpe ratio (annualized)
            returns = equity.pct_change().dropna()
            if len(returns) > 0 and returns.std() > 0:
                # Assuming hourly data, scale to annual
                # 24 hours * 365.25 days = 8766 hours per year
                periods_per_year = 8766
                sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(periods_per_year)
                metrics['sharpe_ratio'] = sharpe_ratio
            else:
                metrics['sharpe_ratio'] = 0
            
            # Calmar ratio
            # Calculate days from equity curve
            start_date = equity.index[0]
            end_date = equity.index[-1]
            try:
                # Convert to Timestamps if needed
                if not isinstance(start_date, pd.Timestamp):
                    start_date = pd.to_datetime(start_date)
                if not isinstance(end_date, pd.Timestamp):
                    end_date = pd.to_datetime(end_date)
                
                # Calculate timedelta
                time_diff = end_date - start_date
                if hasattr(time_diff, 'days'):
                    days = time_diff.days
                elif hasattr(time_diff, 'total_seconds'):
                    days = time_diff.total_seconds() / 86400.0  # Convert seconds to days
                else:
                    days = len(equity) / 24.0  # Fallback: assume hourly data
            except (TypeError, ValueError, AttributeError):
                days = len(equity) / 24.0  # Fallback: assume hourly data
            
            annual_return = metrics['total_return_pct'] / (days / 365.25) if days > 0 else 0
            metrics['calmar_ratio'] = annual_return / abs(metrics['max_drawdown_pct']) if metrics['max_drawdown_pct'] != 0 else 0
            
            # Volatility (annualized)
            if len(returns) > 0:
                periods_per_year = 8766  # Hours per year
                metrics['volatility'] = returns.std() * np.sqrt(periods_per_year) * 100
            else:
                metrics['volatility'] = 0
        
        # Period metrics
        if not self.equity_curve.empty:
            # Handle both index and timestamp column
            if 'timestamp' in self.equity_curve.columns:
                start_date = pd.to_datetime(self.equity_curve['timestamp'].iloc[0])
                end_date = pd.to_datetime(self.equity_curve['timestamp'].iloc[-1])
            else:
                start_date = pd.to_datetime(self.equity_curve.index[0])
                end_date = pd.to_datetime(self.equity_curve.index[-1])
            
            # Calculate days
            try:
                # Ensure both are Timestamps
                if not isinstance(start_date, pd.Timestamp):
                    start_date = pd.to_datetime(start_date)
                if not isinstance(end_date, pd.Timestamp):
                    end_date = pd.to_datetime(end_date)
                
                # Calculate timedelta
                time_diff = end_date - start_date
                if hasattr(time_diff, 'days'):
                    days = time_diff.days
                elif hasattr(time_diff, 'total_seconds'):
                    days = time_diff.total_seconds() / 86400.0  # Convert seconds to days
                else:
                    days = len(self.equity_curve) / 24.0  # Fallback: assume hourly data
            except (TypeError, ValueError, AttributeError):
                # Fallback: assume hourly data, calculate days
                days = len(self.equity_curve) / 24.0
            
            metrics['backtest_days'] = int(days)
            metrics['annualized_return_pct'] = (metrics['total_return_pct'] / days * 365.25) if days > 0 else 0
        
        return metrics
    
    def get_trade_statistics(self) -> pd.DataFrame:
        """Get detailed trade statistics."""
        if not self.trades:
            return pd.DataFrame()
        
        trades_df = pd.DataFrame(self.trades)
        
        # Add additional statistics
        trades_df['cumulative_pnl'] = trades_df['pnl'].cumsum()
        trades_df['cumulative_return_pct'] = (trades_df['cumulative_pnl'] / self.results['initial_capital']) * 100
        
        return trades_df
    
    def get_drawdown_analysis(self) -> pd.DataFrame:
        """Analyze drawdown periods."""
        if self.equity_curve.empty:
            return pd.DataFrame()
        
        equity = self.equity_curve['equity']
        running_max = equity.expanding().max()
        drawdown = equity - running_max
        drawdown_pct = (drawdown / running_max) * 100
        
        df = pd.DataFrame({
            'equity': equity,
            'running_max': running_max,
            'drawdown': drawdown,
            'drawdown_pct': drawdown_pct
        })
        
        return df
    
    def get_monthly_returns(self) -> pd.DataFrame:
        """Get monthly returns."""
        if self.equity_curve.empty:
            return pd.DataFrame()
        
        equity = self.equity_curve.set_index('timestamp')['equity'] if 'timestamp' in self.equity_curve.columns else self.equity_curve['equity']
        equity.index = pd.to_datetime(equity.index)
        
        monthly_returns = equity.resample('M').last().pct_change() * 100
        
        return pd.DataFrame({
            'month': monthly_returns.index,
            'return_pct': monthly_returns.values
        }).dropna()

