"""Backtesting script for trading strategies."""
# IMPORT STANDARD LOGGING FIRST - before any other imports
import sys
if 'logging' in sys.modules:
    # Check if it's our directory (not standard logging)
    if not hasattr(sys.modules['logging'], 'getLogger'):
        del sys.modules['logging']
# Import standard logging
import logging

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from config.config import Config
from collectors.data_collector import DataCollector
from collectors.delta_client import DeltaExchangeClient
from backtesting.backtester import Backtester
from backtesting.performance import PerformanceAnalyzer
from backtesting.report import ReportGenerator
from strategies.ml_strategy import MLStrategy
from features.ml_models import MLPredictor
from features.feature_engineering import FeatureEngineer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backtest.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def run_backtest(
    symbol: str,
    strategy_name: str,
    start_date: str = None,
    end_date: str = None,
    initial_capital: float = 10000.0,
    commission: float = 0.001,
    use_test_data: bool = False
):
    """
    Run backtest for a strategy.
    
    Args:
        symbol: Trading symbol
        strategy_name: Name of strategy ('ml' or 'mean_reversion')
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        initial_capital: Starting capital
        commission: Commission rate
        use_test_data: Use test data instead of API
    """
    logger.info(f"Starting backtest for {symbol} with {strategy_name} strategy")
    
    # Load configuration
    config = Config()
    
    # Initialize data collector
    if use_test_data:
        # For testing, create mock client
        client = None
        data_collector = None
        logger.info("Using test data mode")
    else:
        try:
            client = DeltaExchangeClient(
                api_key=config.delta.api_key,
                api_secret=config.delta.api_secret,
                base_url=config.delta.base_url
            )
            data_collector = DataCollector(client, config)
        except Exception as e:
            logger.error(f"Failed to initialize API client: {e}")
            logger.info("Falling back to test data mode")
            client = None
            data_collector = None
    
    # Load historical data
    if data_collector:
        # Try to load from disk first
        ohlc_df = data_collector.load_historical_data(symbol, resolution=config.trading.default_timeframe)
        
        # If not enough data, fetch from API
        if ohlc_df.empty or len(ohlc_df) < 100:
            logger.info(f"Fetching historical data for {symbol}")
            ohlc_df = data_collector.collect_ohlc(
                symbol=symbol,
                resolution=config.trading.default_timeframe,
                hours=720,  # 30 days
                save=True
            )
    else:
        # Generate test data (90 days = 2160 hours)
        logger.info("Generating test OHLC data (90 days)")
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        dates = pd.date_range(start=start_date, end=end_date, freq='1h')
        periods = len(dates)
        
        import numpy as np
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
    
    if ohlc_df.empty:
        logger.error("No data available for backtest")
        return
    
    # Filter by date range
    if start_date:
        start = pd.Timestamp(start_date)
        ohlc_df = ohlc_df[ohlc_df.index >= start]
    if end_date:
        end = pd.Timestamp(end_date)
        ohlc_df = ohlc_df[ohlc_df.index <= end]
    
    if ohlc_df.empty:
        logger.error("No data in specified date range")
        return
    
    logger.info(f"Backtesting on {len(ohlc_df)} data points from {ohlc_df.index[0]} to {ohlc_df.index[-1]}")
    
    # Initialize strategy
    if strategy_name == 'ml':
        # ML Strategy
        predictor = MLPredictor(
            model_path=config.ml.model_path,
            model_type="random_forest"
        )
        
        # Train model on historical data
        feature_engineer = FeatureEngineer()
        features = feature_engineer.prepare_features(ohlc_df)
        labels = feature_engineer.create_labels(ohlc_df)
        
        common_idx = features.index.intersection(labels.index)
        features_train = features.loc[common_idx]
        labels_train = labels.loc[common_idx]
        
        if len(features_train) > 50:
            logger.info("Training ML model...")
            predictor.train(features_train, labels_train)
        
        strategy_config = {
            'confidence_threshold': config.ml.prediction_threshold,
            'position_size': initial_capital * 0.1,
            'stop_loss_pct': 0.02,
            'take_profit_pct': 0.04
        }
        
        strategy = MLStrategy(
            name=f"ML_{symbol}",
            config=strategy_config,
            predictor=predictor
        )
    elif strategy_name == 'mean_reversion':
        # Mean reversion strategy
        from strategies.mean_reversion_strategy import MeanReversionStrategy
        
        strategy_config = {
            'bb_period': 20,
            'bb_std': 2.0,
            'position_size': initial_capital * 0.1
        }
        
        strategy = MeanReversionStrategy(
            name=f"MeanRev_{symbol}",
            config=strategy_config
        )
    else:
        logger.error(f"Unknown strategy: {strategy_name}")
        return
    
    # Initialize backtester
    backtester = Backtester(
        initial_capital=initial_capital,
        commission=commission,
        slippage=0.0005,
        use_limit_orders=True
    )
    
    # Run backtest
    logger.info("Running backtest...")
    results = backtester.run(
        strategy=strategy,
        data=ohlc_df,
        symbol=symbol,
        start_date=pd.Timestamp(start_date) if start_date else None,
        end_date=pd.Timestamp(end_date) if end_date else None
    )
    
    # Analyze results
    logger.info("Analyzing results...")
    analyzer = PerformanceAnalyzer(results)
    metrics = analyzer.calculate_metrics()
    
    # Print summary
    print("\n" + "=" * 80)
    print("BACKTEST SUMMARY")
    print("=" * 80)
    print(f"Symbol: {symbol}")
    print(f"Strategy: {strategy_name}")
    print(f"Period: {results['start_date']} to {results['end_date']}")
    print(f"\nInitial Capital: ${metrics['initial_capital']:,.2f}")
    print(f"Final Portfolio Value: ${metrics['final_portfolio_value']:,.2f}")
    print(f"Total Return: ${metrics['total_return']:,.2f} ({metrics['total_return_pct']:.2f}%)")
    print(f"Annualized Return: {metrics['annualized_return_pct']:.2f}%")
    print(f"\nTotal Trades: {metrics['total_trades']}")
    print(f"Win Rate: {metrics['win_rate']:.2f}%")
    print(f"Profit Factor: {metrics['profit_factor']:.2f}")
    print(f"Max Drawdown: {metrics['max_drawdown_pct']:.2f}%")
    print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print("=" * 80)
    
    # Generate report
    logger.info("Generating report...")
    report_generator = ReportGenerator(results)
    report_generator.generate_full_report(symbol, strategy_name)
    
    return results, metrics


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Backtest trading strategies')
    parser.add_argument('--symbol', type=str, default='BTCUSD', help='Trading symbol')
    parser.add_argument('--strategy', type=str, default='ml', choices=['ml', 'mean_reversion'],
                       help='Strategy to backtest')
    parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--capital', type=float, default=10000.0, help='Initial capital')
    parser.add_argument('--commission', type=float, default=0.001, help='Commission rate')
    parser.add_argument('--test-data', action='store_true', help='Use test data instead of API')
    
    args = parser.parse_args()
    
    try:
        run_backtest(
            symbol=args.symbol,
            strategy_name=args.strategy,
            start_date=args.start_date,
            end_date=args.end_date,
            initial_capital=args.capital,
            commission=args.commission,
            use_test_data=args.test_data
        )
    except Exception as e:
        logger.error(f"Backtest failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

