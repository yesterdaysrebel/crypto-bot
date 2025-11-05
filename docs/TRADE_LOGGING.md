# Trade Logging

The trade logging system tracks all trades, orders, and positions for monitoring and analysis.

## Features

- ✅ **Comprehensive Logging**: Tracks all trades, orders, and positions
- ✅ **Multiple Formats**: JSON and CSV logging
- ✅ **Real-time Tracking**: Logs trades as they happen
- ✅ **Trade Analysis**: Analyze logged trades for performance metrics
- ✅ **Filtering**: Filter trades by symbol, strategy, date range
- ✅ **Export**: Export trades to CSV for external analysis

## Quick Start

### Automatic Logging

Trades are automatically logged when running the bot:

```bash
python main.py
```

Trades are logged to `trade_logs/` directory with daily files:
- `trades_YYYYMMDD.jsonl` - JSON Lines format
- `trades_YYYYMMDD.csv` - CSV format

### Analyze Logged Trades

```bash
# View trade summary
python analyze_trades.py

# Filter by symbol
python analyze_trades.py --symbol BTCUSD

# Filter by strategy
python analyze_trades.py --strategy ML_BTCUSD

# Filter by date range
python analyze_trades.py --start-date 2024-01-01 --end-date 2024-06-01

# Export to CSV
python analyze_trades.py --export trades_export.csv

# Analyze specific log file
python analyze_trades.py --file trade_logs/trades_20240101.jsonl
```

## Programmatic Usage

### Using TradeLogger

```python
from logging.trade_logger import TradeLogger

# Initialize logger
trade_logger = TradeLogger(
    log_dir="trade_logs",
    log_format="both",  # 'json', 'csv', or 'both'
    enable_console=True
)

# Log an order
trade = trade_logger.log_order(
    symbol='BTCUSD',
    strategy='ML_BTCUSD',
    action='buy',
    size=0.1,
    price=50000.0,
    order_type='limit_order',
    order_id='order123',
    signal_confidence=0.8,
    signal_reason='ML prediction: 1',
    stop_loss=49000.0,
    take_profit=52000.0,
    commission=5.0
)

# Log order filled
trade_logger.log_order_filled('order123', filled_price=50000.0)

# Log position closed
trade_logger.log_position_closed(
    symbol='BTCUSD',
    exit_price=51000.0,
    pnl=100.0,
    pnl_pct=2.0,
    reason='Take profit hit'
)

# Get trades
trades = trade_logger.get_trades(symbol='BTCUSD', status='closed')

# Get trades as DataFrame
df = trade_logger.get_trades_df(symbol='BTCUSD', strategy='ML_BTCUSD')
```

### Using TradeAnalyzer

```python
from logging.trade_logger import TradeLogger
from logging.trade_analyzer import TradeAnalyzer

# Initialize
trade_logger = TradeLogger()
analyzer = TradeAnalyzer(trade_logger)

# Get summary
summary = analyzer.get_trade_summary(symbol='BTCUSD')
print(f"Total P&L: ${summary['total_pnl']:.2f}")
print(f"Win Rate: {summary['win_rate']:.2f}%")

# Performance by strategy
strategy_perf = analyzer.get_performance_by_strategy()
print(strategy_perf)

# Performance by symbol
symbol_perf = analyzer.get_performance_by_symbol()
print(symbol_perf)

# Daily P&L
daily_pnl = analyzer.get_daily_pnl()
print(daily_pnl)

# Print summary to console
analyzer.print_summary(symbol='BTCUSD')
```

## Log File Formats

### JSON Lines Format (.jsonl)

Each line is a JSON object:

```json
{"timestamp":"2024-01-01T12:00:00","symbol":"BTCUSD","strategy":"ML_BTCUSD","action":"buy","size":0.1,"price":50000.0,"order_type":"limit_order","order_id":"order123","signal_confidence":0.8,"status":"open"}
{"timestamp":"2024-01-01T13:00:00","symbol":"BTCUSD","strategy":"ML_BTCUSD","action":"sell","size":0.1,"price":51000.0,"order_type":"limit_order","status":"closed","pnl":100.0,"pnl_pct":2.0}
```

### CSV Format (.csv)

Standard CSV with headers:

```csv
timestamp,symbol,strategy,action,size,price,order_type,order_id,signal_confidence,status,pnl,pnl_pct
2024-01-01T12:00:00,BTCUSD,ML_BTCUSD,buy,0.1,50000.0,limit_order,order123,0.8,open,,
2024-01-01T13:00:00,BTCUSD,ML_BTCUSD,sell,0.1,51000.0,limit_order,order123,0.8,closed,100.0,2.0
```

## Trade Data Structure

Each trade contains:

```python
{
    'timestamp': '2024-01-01T12:00:00',
    'symbol': 'BTCUSD',
    'strategy': 'ML_BTCUSD',
    'action': 'buy',  # or 'sell'
    'size': 0.1,
    'price': 50000.0,
    'order_type': 'limit_order',  # or 'market_order'
    'order_id': 'order123',
    'signal_confidence': 0.8,
    'signal_reason': 'ML prediction: 1',
    'stop_loss': 49000.0,
    'take_profit': 52000.0,
    'commission': 5.0,
    'status': 'open',  # 'open', 'filled', 'cancelled', 'closed'
    'entry_timestamp': '2024-01-01T12:00:00',
    'exit_timestamp': '2024-01-01T13:00:00',
    'exit_price': 51000.0,
    'pnl': 100.0,
    'pnl_pct': 2.0,
    'duration': '1:00:00',
    'notes': 'Take profit hit'
}
```

## Integration

The trade logger is automatically integrated with:

- **OrderManager**: Logs all orders placed
- **PositionManager**: Logs position closures
- **Main Bot**: Logs signals and trades

## Performance Metrics

The analyzer provides:

### Summary Statistics
- Total trades
- Open/closed trades
- Win rate
- Total P&L
- Average P&L
- Profit factor
- Largest win/loss

### Breakdowns
- Performance by strategy
- Performance by symbol
- Daily P&L
- Cumulative P&L

## Best Practices

### 1. **Regular Analysis**
- Review trades daily
- Identify patterns
- Adjust strategies

### 2. **Data Retention**
- Keep logs for analysis
- Archive old logs
- Backup important data

### 3. **Performance Monitoring**
- Track win rate
- Monitor P&L trends
- Compare strategies

### 4. **Debugging**
- Use logs to debug issues
- Track order execution
- Verify signal logic

## Example Output

```
================================================================================
TRADE ANALYSIS
================================================================================
Total Trades: 45
Open Trades: 2
Closed Trades: 43

Win Rate: 60.47%
Winning Trades: 26
Losing Trades: 17

Total P&L: $1,250.00
Total P&L %: 12.50%
Average P&L: $29.07
Average P&L %: 0.29%

Average Win: $75.00
Average Loss: -$45.00
Profit Factor: 1.67

Largest Win: $200.00
Largest Loss: -$100.00
================================================================================

--------------------------------------------------------------------------------
PERFORMANCE BY STRATEGY
--------------------------------------------------------------------------------
strategy    total_trades  total_pnl  avg_pnl  avg_pnl_pct  win_rate
ML_BTCUSD   25            625.00     25.00    0.50         65.00
ML_ETHUSD   20            625.00     31.25    0.62         55.00
--------------------------------------------------------------------------------

--------------------------------------------------------------------------------
PERFORMANCE BY SYMBOL
--------------------------------------------------------------------------------
symbol  total_trades  total_pnl  avg_pnl  avg_pnl_pct  win_rate
BTCUSD  25           625.00     25.00    0.50         65.00
ETHUSD  20           625.00     31.25    0.62         55.00
--------------------------------------------------------------------------------
```

## Troubleshooting

### No Trades Logged
- Check bot is running
- Verify log directory exists
- Check file permissions

### Missing Data
- Check log file format
- Verify trade logger is initialized
- Check for errors in logs

### Analysis Issues
- Ensure log files are readable
- Check date format
- Verify data types

## Summary

The trade logging system provides:
- ✅ Comprehensive trade tracking
- ✅ Multiple log formats
- ✅ Performance analysis
- ✅ Easy filtering and export
- ✅ Integration with trading bot

Use it to monitor and improve your trading strategies!

