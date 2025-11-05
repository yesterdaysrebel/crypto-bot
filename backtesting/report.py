"""Report generation for backtesting results."""
import pandas as pd
from typing import Dict, Optional
from pathlib import Path
import logging

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("matplotlib not available. Plot generation will be disabled.")

from .performance import PerformanceAnalyzer

if not 'logger' in locals():
    logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate backtesting reports."""
    
    def __init__(self, results: Dict, output_dir: str = "backtest_reports"):
        """
        Initialize report generator.
        
        Args:
            results: Backtest results dictionary
            output_dir: Directory to save reports
        """
        self.results = results
        self.analyzer = PerformanceAnalyzer(results)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_text_report(self, filename: Optional[str] = None) -> str:
        """
        Generate text report.
        
        Args:
            filename: Optional filename to save report
            
        Returns:
            Report as string
        """
        metrics = self.analyzer.calculate_metrics()
        
        report = []
        report.append("=" * 80)
        report.append("BACKTEST REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Basic information
        report.append(f"Symbol: {self.results.get('symbol', 'N/A')}")
        report.append(f"Period: {self.results.get('start_date', 'N/A')} to {self.results.get('end_date', 'N/A')}")
        report.append(f"Backtest Days: {metrics.get('backtest_days', 0)}")
        report.append("")
        
        # Performance metrics
        report.append("-" * 80)
        report.append("PERFORMANCE METRICS")
        report.append("-" * 80)
        report.append(f"Initial Capital: ${metrics.get('initial_capital', 0):,.2f}")
        report.append(f"Final Portfolio Value: ${metrics.get('final_portfolio_value', 0):,.2f}")
        report.append(f"Total Return: ${metrics.get('total_return', 0):,.2f}")
        report.append(f"Total Return %: {metrics.get('total_return_pct', 0):.2f}%")
        report.append(f"Annualized Return %: {metrics.get('annualized_return_pct', 0):.2f}%")
        report.append("")
        
        # Trade statistics
        report.append("-" * 80)
        report.append("TRADE STATISTICS")
        report.append("-" * 80)
        report.append(f"Total Trades: {metrics.get('total_trades', 0)}")
        report.append(f"Winning Trades: {metrics.get('winning_trades', 0)}")
        report.append(f"Losing Trades: {metrics.get('losing_trades', 0)}")
        report.append(f"Win Rate: {metrics.get('win_rate', 0):.2f}%")
        report.append(f"Average Win: ${metrics.get('avg_win', 0):,.2f}")
        report.append(f"Average Loss: ${metrics.get('avg_loss', 0):,.2f}")
        report.append(f"Average Trade P&L: ${metrics.get('avg_trade_pnl', 0):,.2f}")
        report.append(f"Average Trade P&L %: {metrics.get('avg_trade_pnl_pct', 0):.2f}%")
        report.append(f"Profit Factor: {metrics.get('profit_factor', 0):.2f}")
        report.append(f"Largest Win: ${metrics.get('largest_win', 0):,.2f}")
        report.append(f"Largest Loss: ${metrics.get('largest_loss', 0):,.2f}")
        report.append("")
        
        # Risk metrics
        report.append("-" * 80)
        report.append("RISK METRICS")
        report.append("-" * 80)
        report.append(f"Max Drawdown: ${metrics.get('max_drawdown', 0):,.2f}")
        report.append(f"Max Drawdown %: {metrics.get('max_drawdown_pct', 0):.2f}%")
        report.append(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
        report.append(f"Calmar Ratio: {metrics.get('calmar_ratio', 0):.2f}")
        report.append(f"Volatility: {metrics.get('volatility', 0):.2f}%")
        report.append("")
        
        report_text = "\n".join(report)
        
        if filename:
            filepath = self.output_dir / filename
            filepath.write_text(report_text)
            logger.info(f"Text report saved to {filepath}")
        
        return report_text
    
    def generate_equity_curve_plot(self, filename: Optional[str] = None) -> None:
        """Generate equity curve plot."""
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("matplotlib not available. Skipping plot generation.")
            return
        
        if self.results['equity_curve'].empty:
            logger.warning("No equity curve data to plot")
            return
        
        equity_df = self.results['equity_curve']
        if 'timestamp' in equity_df.columns:
            equity_df = equity_df.set_index('timestamp')
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        ax.plot(equity_df.index, equity_df['equity'], label='Equity Curve', linewidth=2)
        ax.axhline(y=self.results['initial_capital'], color='r', linestyle='--', label='Initial Capital')
        
        ax.set_xlabel('Date')
        ax.set_ylabel('Portfolio Value ($)')
        ax.set_title(f'Equity Curve - {self.results.get("symbol", "N/A")}')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        if filename:
            filepath = self.output_dir / filename
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            logger.info(f"Equity curve plot saved to {filepath}")
        else:
            plt.show()
        
        plt.close()
    
    def generate_drawdown_plot(self, filename: Optional[str] = None) -> None:
        """Generate drawdown plot."""
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("matplotlib not available. Skipping plot generation.")
            return
        
        drawdown_df = self.analyzer.get_drawdown_analysis()
        
        if drawdown_df.empty:
            logger.warning("No drawdown data to plot")
            return
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        
        # Equity curve
        ax1.plot(drawdown_df.index, drawdown_df['equity'], label='Equity', linewidth=2)
        ax1.plot(drawdown_df.index, drawdown_df['running_max'], label='Running Max', linestyle='--', alpha=0.7)
        ax1.set_ylabel('Portfolio Value ($)')
        ax1.set_title('Equity Curve and Drawdown')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Drawdown
        ax2.fill_between(drawdown_df.index, 0, drawdown_df['drawdown_pct'], 
                        color='red', alpha=0.3, label='Drawdown %')
        ax2.plot(drawdown_df.index, drawdown_df['drawdown_pct'], color='red', linewidth=1)
        ax2.set_xlabel('Date')
        ax2.set_ylabel('Drawdown (%)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Format x-axis dates
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax2.xaxis.set_major_locator(mdates.MonthLocator())
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        if filename:
            filepath = self.output_dir / filename
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            logger.info(f"Drawdown plot saved to {filepath}")
        else:
            plt.show()
        
        plt.close()
    
    def generate_trades_plot(self, filename: Optional[str] = None) -> None:
        """Generate trades plot showing entry/exit points."""
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("matplotlib not available. Skipping plot generation.")
            return
        
        if not self.results.get('trades'):
            logger.warning("No trades to plot")
            return
        
        trades_df = pd.DataFrame(self.results['trades'])
        
        # This would need OHLC data to plot properly
        # For now, just plot cumulative P&L
        trades_df['cumulative_pnl'] = trades_df['pnl'].cumsum()
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        ax.plot(trades_df['exit_timestamp'], trades_df['cumulative_pnl'], 
               marker='o', linewidth=2, label='Cumulative P&L')
        ax.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        
        ax.set_xlabel('Date')
        ax.set_ylabel('Cumulative P&L ($)')
        ax.set_title('Cumulative P&L Over Time')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        if filename:
            filepath = self.output_dir / filename
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            logger.info(f"Trades plot saved to {filepath}")
        else:
            plt.show()
        
        plt.close()
    
    def generate_full_report(self, symbol: str, strategy_name: str) -> None:
        """
        Generate full backtest report with all plots.
        
        Args:
            symbol: Trading symbol
            strategy_name: Name of the strategy
        """
        timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        prefix = f"{symbol}_{strategy_name}_{timestamp}"
        
        # Generate text report
        self.generate_text_report(f"{prefix}_report.txt")
        
        # Generate plots
        self.generate_equity_curve_plot(f"{prefix}_equity_curve.png")
        self.generate_drawdown_plot(f"{prefix}_drawdown.png")
        self.generate_trades_plot(f"{prefix}_trades.png")
        
        logger.info(f"Full backtest report generated: {prefix}")

