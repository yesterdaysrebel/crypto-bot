# Backtesting Framework

The backtesting framework allows you to test trading strategies on historical data before risking real money.

## Features

- ✅ **Historical Data Testing**: Test strategies on past market data
- ✅ **Realistic Simulation**: Includes commission, slippage, and limit orders
- ✅ **Performance Metrics**: Comprehensive performance analysis
- ✅ **Visual Reports**: Equity curves, drawdown charts, and trade analysis
- ✅ **Multiple Strategies**: Compare different strategies
- ✅ **Risk Metrics**: Sharpe ratio, Calmar ratio, max drawdown

## Quick Start

### Basic Backtest

```bash
# Backtest ML strategy on BTCUSD
python backtest.py --symbol BTCUSD --strategy ml

# Backtest mean reversion strategy
python backtest.py --symbol BTCUSD --strategy mean_reversion

# Specify date range
python backtest.py --symbol BTCUSD --strategy ml --start-date 2024-01-01 --end-date 2024-03-01

# Custom initial capital
python backtest.py --symbol BTCUSD --strategy ml --capital 50000

# Use test data (no API calls)
python backtest.py --symbol BTCUSD --strategy ml --test-data
```

## Usage Examples

### Example 1: Basic ML Strategy Backtest

```bash
python backtest.py --symbol BTCUSD --strategy ml
```

This will:
1. Load historical data for BTCUSD
2. Train ML model on historical data
3. Run backtest simulation
4. Generate performance report
5. Create visualization plots

### Example 2: Date Range Backtest

```bash
python backtest.py \
    --symbol ETHUSD \
    --strategy mean_reversion \
    --start-date 2024-01-01 \
    --end-date 2024-06-01 \
    --capital 100000
```

### Example 3: Compare Strategies

```bash
# Test ML strategy
python backtest.py --symbol BTCUSD --strategy ml --start-date 2024-01-01 --end-date 2024-06-01

# Test mean reversion strategy
python backtest.py --symbol BTCUSD --strategy mean_reversion --start-date 2024-01-01 --end-date 2024-06-01

# Compare results
```

## Programmatic Usage

### Using Backtester Class

```python
from backtesting.backtester import Backtester
from strategies.ml_strategy import MLStrategy
from features.ml_models import MLPredictor
import pandas as pd

# Load historical data
ohlc_df = pd.read_csv('data/BTCUSD_1h_ohlc.csv', index_col='time', parse_dates=True)

# Initialize strategy
predictor = MLPredictor(model_path='models')
# ... train model ...

strategy = MLStrategy(
    name='ML_BTCUSD',
    config={'confidence_threshold': 0.6, 'position_size': 0.1},
    predictor=predictor
)

# Initialize backtester
backtester = Backtester(
    initial_capital=10000.0,
    commission=0.001,  # 0.1%
    slippage=0.0005,   # 0.05%
    use_limit_orders=True
)

# Run backtest
results = backtester.run(
    strategy=strategy,
    data=ohlc_df,
    symbol='BTCUSD',
    start_date=pd.Timestamp('2024-01-01'),
    end_date=pd.Timestamp('2024-06-01')
)

# Analyze results
from backtesting.performance import PerformanceAnalyzer
analyzer = PerformanceAnalyzer(results)
metrics = analyzer.calculate_metrics()

print(f"Total Return: {metrics['total_return_pct']:.2f}%")
print(f"Win Rate: {metrics['win_rate']:.2f}%")
print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
```

## Performance Metrics

The backtesting framework calculates comprehensive metrics:

### Return Metrics
- **Total Return**: Absolute and percentage return
- **Annualized Return**: Return normalized to annual basis
- **Cumulative Returns**: Returns over time

### Trade Statistics
- **Total Trades**: Number of completed trades
- **Win Rate**: Percentage of winning trades
- **Average Win/Loss**: Average profit/loss per trade
- **Profit Factor**: Ratio of gross profit to gross loss
- **Largest Win/Loss**: Best and worst trades

### Risk Metrics
- **Max Drawdown**: Largest peak-to-trough decline
- **Sharpe Ratio**: Risk-adjusted return measure
- **Calmar Ratio**: Return to max drawdown ratio
- **Volatility**: Standard deviation of returns

## Reports

The framework generates comprehensive reports:

### Text Report
- Summary statistics
- Performance metrics
- Trade statistics
- Risk metrics

### Visual Reports
- **Equity Curve**: Portfolio value over time
- **Drawdown Chart**: Drawdown periods visualization
- **Trades Plot**: Entry/exit points and P&L

Reports are saved to `backtest_reports/` directory.

## Configuration

### Backtester Parameters

```python
Backtester(
    initial_capital=10000.0,  # Starting capital
    commission=0.001,          # 0.1% commission per trade
    slippage=0.0005,           # 0.05% slippage
    use_limit_orders=True      # Use limit orders (vs market)
)
```

### Commission and Slippage

- **Commission**: Fee charged per trade (default: 0.1%)
- **Slippage**: Price movement between signal and execution (default: 0.05%)
- **Limit Orders**: Simulates limit orders (price may not fill if moved away)

## Strategy Testing

### Testing Custom Strategies

Any strategy that extends `BaseStrategy` can be backtested:

```python
from strategies.base_strategy import BaseStrategy, Signal

class MyStrategy(BaseStrategy):
    def generate_signal(self, data):
        # Your strategy logic
        return Signal(symbol='BTCUSD', action='buy', size=0.1)
    
    def should_close_position(self, position, data):
        # Your exit logic
        return False

# Use in backtest
backtester.run(strategy=MyStrategy(...), data=ohlc_df, symbol='BTCUSD')
```

## Best Practices

### 1. **Use Sufficient Data**
- At least 3-6 months of historical data
- More data = more reliable results

### 2. **Realistic Parameters**
- Include commission and slippage
- Use realistic position sizes
- Consider market impact

### 3. **Multiple Time Periods**
- Test on different market conditions
- Bull markets, bear markets, sideways
- Different volatility periods

### 4. **Out-of-Sample Testing**
- Train on historical data
- Test on later period
- Avoid overfitting

### 5. **Compare Strategies**
- Test multiple strategies
- Compare performance metrics
- Choose best for your goals

## Limitations

### 1. **Historical Bias**
- Past performance ≠ future results
- Market conditions change
- Use as guide, not guarantee

### 2. **Execution Assumptions**
- Assumes perfect execution
- Real market may differ
- Slippage may be higher

### 3. **Data Quality**
- Depends on historical data quality
- Missing data points
- Data feed differences

### 4. **Market Impact**
- Large orders may move price
- Not modeled in backtest
- More relevant for large capital

## Troubleshooting

### No Trades Generated
- Check strategy logic
- Verify signal generation
- Check data quality

### Negative Returns
- Review strategy parameters
- Check stop loss/take profit
- Test different time periods

### High Drawdown
- Adjust position sizing
- Review risk management
- Consider strategy modifications

## Advanced Usage

### Custom Performance Analysis

```python
from backtesting.performance import PerformanceAnalyzer

analyzer = PerformanceAnalyzer(results)

# Get trade statistics
trades_df = analyzer.get_trade_statistics()

# Get drawdown analysis
drawdown_df = analyzer.get_drawdown_analysis()

# Get monthly returns
monthly_returns = analyzer.get_monthly_returns()
```

### Custom Reports

```python
from backtesting.report import ReportGenerator

generator = ReportGenerator(results)

# Generate text report
report = generator.generate_text_report('my_report.txt')

# Generate specific plots
generator.generate_equity_curve_plot('equity.png')
generator.generate_drawdown_plot('drawdown.png')
```

## Integration with Main Bot

The backtesting framework can be integrated with the main trading bot:

```python
# In main.py, add backtesting option
if args.backtest:
    from backtesting.backtester import Backtester
    # Run backtest instead of live trading
```

## Summary

The backtesting framework provides:
- ✅ Historical strategy testing
- ✅ Realistic market simulation
- ✅ Comprehensive performance metrics
- ✅ Visual reports and analysis
- ✅ Easy integration with strategies

Use it to validate strategies before risking real capital!

