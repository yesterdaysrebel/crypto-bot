#!/usr/bin/env python3
"""Run 90-day backtest."""
# IMPORT STANDARD LOGGING FIRST - before any other imports
import sys
if 'logging' in sys.modules:
    # Check if it's our directory (not standard logging)
    if not hasattr(sys.modules['logging'], 'getLogger'):
        del sys.modules['logging']
# Import standard logging
import logging as std_logging

# Now continue with other imports
import subprocess
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Install matplotlib
print("Installing matplotlib...")
try:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'matplotlib', '--quiet'])
    print("✓ matplotlib installed")
except:
    print("⚠ matplotlib installation may have failed, continuing anyway...")

# Import after installation
try:
    import matplotlib
    print("✓ matplotlib imported successfully")
except ImportError:
    print("⚠ matplotlib not available, plots will be skipped")

# Now run the backtest
print("\n" + "=" * 80)
print("Running 90-Day Backtest")
print("=" * 80)

# Import backtesting components
from backtesting.backtester import Backtester
from backtesting.performance import PerformanceAnalyzer
from backtesting.report import ReportGenerator
from strategies.mean_reversion_strategy import MeanReversionStrategy

# Generate 90 days of test data (90 days * 24 hours = 2160 periods)
print("\nGenerating 90 days of test data...")
end_date = datetime.now()
start_date = end_date - timedelta(days=90)
dates = pd.date_range(start=start_date, end=end_date, freq='1h')
periods = len(dates)

np.random.seed(42)
base_price = 50000
prices = []
current_price = base_price

for _ in range(periods):
    change = np.random.normal(0, 0.01)
    current_price *= (1 + change)
    prices.append(current_price)

ohlc_df = pd.DataFrame({
    'open': prices,
    'high': [p * 1.01 for p in prices],
    'low': [p * 0.99 for p in prices],
    'close': [p * 1.002 for p in prices],
    'volume': np.random.uniform(1000, 10000, periods)
}, index=dates)

# Ensure high >= close >= low and high >= open >= low
ohlc_df['high'] = ohlc_df[['open', 'high', 'low', 'close']].max(axis=1)
ohlc_df['low'] = ohlc_df[['open', 'high', 'low', 'close']].min(axis=1)

print(f"✓ Generated {len(ohlc_df)} data points ({periods // 24} days)")
print(f"  Date range: {ohlc_df.index[0]} to {ohlc_df.index[-1]}")

# Initialize strategy
print("\nInitializing Mean Reversion strategy...")
strategy_config = {
    'bb_period': 20,
    'bb_std': 2.0,
    'position_size': 0.1  # 10% of capital (size will be calculated)
}

strategy = MeanReversionStrategy(
    name='MeanRev_SOLUSDT',
    config=strategy_config
)
print("✓ Strategy initialized")

# Initialize backtester
print("\nInitializing backtester...")
backtester = Backtester(
    initial_capital=100.0,
    commission=0.001,  # 0.1%
    slippage=0.0005,   # 0.05%
    use_limit_orders=True
)
print("✓ Backtester initialized")

# Run backtest
print("\nRunning backtest (this may take a moment)...")
results = backtester.run(
    strategy=strategy,
    data=ohlc_df,
    symbol='SOLUSD',
    start_date=ohlc_df.index[0],
    end_date=ohlc_df.index[-1]
)

print("✓ Backtest completed")

# Analyze results
print("\nAnalyzing results...")
analyzer = PerformanceAnalyzer(results)
metrics = analyzer.calculate_metrics()

# Print summary
print("\n" + "=" * 80)
print("BACKTEST SUMMARY - 90 DAYS")
print("=" * 80)
print(f"Symbol: {results.get('symbol', 'SOLUSDT')}")
print(f"Strategy: Mean Reversion")
print(f"Period: {results.get('start_date', 'N/A')} to {results.get('end_date', 'N/A')}")
print(f"Days: {(results.get('end_date', pd.Timestamp.now()) - results.get('start_date', pd.Timestamp.now())).days}")

print(f"\n💰 PERFORMANCE")
print(f"Initial Capital: ${metrics.get('initial_capital', 0):,.2f}")
print(f"Final Portfolio Value: ${metrics.get('final_portfolio_value', 0):,.2f}")
print(f"Total Return: ${metrics.get('total_return', 0):,.2f}")
print(f"Total Return %: {metrics.get('total_return_pct', 0):.2f}%")
print(f"Annualized Return: {metrics.get('annualized_return_pct', 0):.2f}%")

print(f"\n📊 TRADING STATISTICS")
print(f"Total Trades: {metrics.get('total_trades', 0)}")
print(f"Winning Trades: {metrics.get('winning_trades', 0)}")
print(f"Losing Trades: {metrics.get('losing_trades', 0)}")
print(f"Win Rate: {metrics.get('win_rate', 0):.2f}%")
print(f"Average Win: ${metrics.get('avg_win', 0):,.2f}")
print(f"Average Loss: ${metrics.get('avg_loss', 0):,.2f}")
print(f"Average Trade P&L: ${metrics.get('avg_trade_pnl', 0):,.2f}")
print(f"Profit Factor: {metrics.get('profit_factor', 0):.2f}")
print(f"Largest Win: ${metrics.get('largest_win', 0):,.2f}")
print(f"Largest Loss: ${metrics.get('largest_loss', 0):,.2f}")

print(f"\n⚠️  RISK METRICS")
print(f"Max Drawdown: ${metrics.get('max_drawdown', 0):,.2f}")
print(f"Max Drawdown %: {metrics.get('max_drawdown_pct', 0):.2f}%")
print(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
print(f"Calmar Ratio: {metrics.get('calmar_ratio', 0):.2f}")
print(f"Volatility: {metrics.get('volatility', 0):.2f}%")
print("=" * 80)

# Generate report
print("\nGenerating report...")
try:
    report_generator = ReportGenerator(results)
    report_generator.generate_full_report('SOLUSDT', 'MeanReversion')
    print("✓ Report generated in backtest_reports/ directory")
except Exception as e:
    print(f"⚠ Report generation had issues: {e}")

print("\n✓ Backtest completed successfully!")

