"""Script to analyze logged trades."""
import argparse
import logging
from datetime import datetime
from pathlib import Path

from trade_logging.trade_logger import TradeLogger
from trade_logging.trade_analyzer import TradeAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Analyze logged trades')
    parser.add_argument('--symbol', type=str, help='Filter by symbol')
    parser.add_argument('--strategy', type=str, help='Filter by strategy')
    parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--file', type=str, help='Specific log file to analyze')
    parser.add_argument('--export', type=str, help='Export trades to CSV file')
    
    args = parser.parse_args()
    
    # Initialize trade logger
    trade_logger = TradeLogger(log_dir="trade_logs")
    
    # Load trades from file if specified
    if args.file:
        log_file = Path(args.file)
        trade_logger.load_trades_from_file(log_file)
    else:
        # Load latest trades
        trade_logger.load_trades_from_file()
    
    # Parse date filters
    start_date = datetime.fromisoformat(args.start_date) if args.start_date else None
    end_date = datetime.fromisoformat(args.end_date) if args.end_date else None
    
    # Initialize analyzer
    analyzer = TradeAnalyzer(trade_logger)
    
    # Print summary
    print("\n" + "=" * 80)
    print("TRADE ANALYSIS")
    print("=" * 80)
    analyzer.print_summary(symbol=args.symbol, strategy=args.strategy)
    
    # Get detailed statistics
    if args.symbol or args.strategy:
        print(f"\nFiltered by: Symbol={args.symbol}, Strategy={args.strategy}")
    
    # Performance by strategy
    print("\n" + "-" * 80)
    print("PERFORMANCE BY STRATEGY")
    print("-" * 80)
    strategy_perf = analyzer.get_performance_by_strategy()
    if not strategy_perf.empty:
        print(strategy_perf.to_string(index=False))
    else:
        print("No strategy performance data")
    
    # Performance by symbol
    print("\n" + "-" * 80)
    print("PERFORMANCE BY SYMBOL")
    print("-" * 80)
    symbol_perf = analyzer.get_performance_by_symbol()
    if not symbol_perf.empty:
        print(symbol_perf.to_string(index=False))
    else:
        print("No symbol performance data")
    
    # Daily P&L
    print("\n" + "-" * 80)
    print("DAILY P&L (Last 10 Days)")
    print("-" * 80)
    daily_pnl = analyzer.get_daily_pnl()
    if not daily_pnl.empty:
        print(daily_pnl.tail(10).to_string(index=False))
    else:
        print("No daily P&L data")
    
    # Export trades
    if args.export:
        df = trade_logger.get_trades_df(
            symbol=args.symbol,
            strategy=args.strategy,
            start_date=start_date,
            end_date=end_date
        )
        if not df.empty:
            df.to_csv(args.export, index=False)
            print(f"\nTrades exported to {args.export}")
        else:
            print("\nNo trades to export")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()

