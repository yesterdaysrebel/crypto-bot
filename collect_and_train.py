#!/usr/bin/env python3
"""Data collection and ML training script - NO ORDER PLACEMENT."""
import sys
# Ensure we use standard logging module, not our directory
if 'logging' in sys.modules:
    # Check if it's our directory (not standard logging)
    if not hasattr(sys.modules['logging'], 'getLogger'):
        del sys.modules['logging']

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, skip .env loading
    pass

# Now import standard logging
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_collection.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

from config.config import Config
from collectors.delta_client import DeltaExchangeClient
from collectors.data_collector import DataCollector
from features.feature_engineering import FeatureEngineer
from features.ml_models import MLPredictor


def list_available_products(config: Config, search_term: str = None, show_raw: bool = False):
    """
    List available products from Delta Exchange.
    
    Args:
        config: Configuration object
        search_term: Optional search term to filter products
        show_raw: If True, print raw JSON response for first product
    """
    logger.info("=" * 80)
    logger.info("AVAILABLE PRODUCTS ON DELTA EXCHANGE")
    logger.info("=" * 80)
    
    try:
        client = DeltaExchangeClient(
            api_key=config.delta.api_key,
            api_secret=config.delta.api_secret,
            base_url=config.delta.base_url
        )
        
        products = client.get_products()
        
        logger.info(f"Total products from API: {len(products)}")
        
        if show_raw and products:
            import json
            logger.info("\n" + "=" * 80)
            logger.info("RAW API RESPONSE (First Product):")
            logger.info("=" * 80)
            logger.info(json.dumps(products[0], indent=2))
            logger.info("=" * 80 + "\n")
        
        if search_term:
            products = [p for p in products if search_term.upper() in p.get('symbol', '').upper()]
            logger.info(f"Filtered products matching '{search_term}': {len(products)}")
        
        if not products:
            logger.warning(f"No products found matching '{search_term}'")
            return
        
        logger.info(f"\nFound {len(products)} products:\n")
        
        # Group by underlying asset
        logger.info(f"{'Symbol':<30} | {'Contract Type':<20} | {'Description'}")
        logger.info("-" * 100)
        for product in products[:50]:  # Show first 50
            symbol = product.get('symbol', 'N/A')
            description = product.get('description', 'N/A')[:50]  # Truncate long descriptions
            contract_type = product.get('contract_type', 'N/A')
            logger.info(f"  {symbol:<30} | {contract_type:<20} | {description}")
        
        if len(products) > 50:
            logger.info(f"\n... and {len(products) - 50} more products")
        
        logger.info("\n" + "=" * 80)
        logger.info("TIP: Use the exact symbol (including dots/prefixes) when collecting data")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Error fetching products: {e}", exc_info=True)


def collect_data(config: Config, symbols: list = None, hours: int = 720):
    """
    Collect historical data for specified symbols.
    
    Args:
        config: Configuration object
        symbols: List of symbols to collect (default: from config)
        hours: Number of hours of historical data to collect (default: 30 days)
    
    Returns:
        Dictionary mapping symbols to DataFrames
    """
    logger.info("=" * 80)
    logger.info("DATA COLLECTION MODE - NO ORDERS WILL BE PLACED")
    logger.info("=" * 80)
    
    # Initialize client
    client = DeltaExchangeClient(
        api_key=config.delta.api_key,
        api_secret=config.delta.api_secret,
        base_url=config.delta.base_url
    )
    
    # Initialize data collector
    collector = DataCollector(client, config)
    
    # Use symbols from config if not provided
    if symbols is None:
        symbols = config.trading.products
    
    logger.info(f"Collecting data for symbols: {symbols}")
    logger.info(f"Timeframe: {config.trading.default_timeframe}")
    logger.info(f"Hours of data: {hours} (~{hours/24:.1f} days)")
    
    collected_data = {}
    
    for symbol in symbols:
        logger.info(f"\n{'='*60}")
        logger.info(f"Collecting data for {symbol}")
        logger.info(f"{'='*60}")
        
        try:
            # Check if we have existing data
            existing_df = collector.load_historical_data(
                symbol=symbol,
                resolution=config.trading.default_timeframe
            )
            
            if not existing_df.empty:
                logger.info(f"Found existing data: {len(existing_df)} data points")
                logger.info(f"Date range: {existing_df.index[0]} to {existing_df.index[-1]}")
                
                # Update with new data
                logger.info("Updating with latest data from API...")
                updated_df = collector.update_historical_data(
                    symbol=symbol,
                    resolution=config.trading.default_timeframe
                )
                
                if not updated_df.empty:
                    logger.info(f"✓ Updated data: {len(updated_df)} total data points")
                    logger.info(f"  New date range: {updated_df.index[0]} to {updated_df.index[-1]}")
                    collected_data[symbol] = updated_df
                else:
                    logger.warning(f"⚠ Failed to update data for {symbol}, using existing")
                    collected_data[symbol] = existing_df
            else:
                # Collect fresh data
                logger.info(f"No existing data found. Collecting {hours} hours of data...")
                df = collector.collect_ohlc(
                    symbol=symbol,
                    resolution=config.trading.default_timeframe,
                    hours=hours,
                    save=True
                )
                
                if not df.empty:
                    logger.info(f"✓ Collected {len(df)} data points")
                    logger.info(f"  Date range: {df.index[0]} to {df.index[-1]}")
                    collected_data[symbol] = df
                else:
                    logger.error(f"✗ Failed to collect data for {symbol}")
                    logger.error(f"  This symbol may not exist or may not have OHLC data available.")
                    logger.error(f"")
                    logger.error(f"  To find the correct symbol:")
                    logger.error(f"    python collect_and_train.py --list-products")
                    logger.error(f"  Or search for specific assets:")
                    logger.error(f"    python collect_and_train.py --list-products SOL")
                    logger.error(f"")
                    logger.error(f"  Common issues:")
                    logger.error(f"    - Symbol format may require a dot prefix (e.g., .DESOLUSD)")
                    logger.error(f"    - Symbol may be case-sensitive")
                    logger.error(f"    - Historical data may not be available for new products")
        
        except Exception as e:
            logger.error(f"Error collecting data for {symbol}: {e}", exc_info=True)
    
    return collected_data


def train_ml_models(config: Config, collected_data: dict, model_type: str = "random_forest"):
    """
    Train ML models on collected data.
    
    Args:
        config: Configuration object
        collected_data: Dictionary mapping symbols to DataFrames
        model_type: Type of model to train ("random_forest" or "gradient_boosting")
    
    Returns:
        Dictionary mapping symbols to trained predictors
    """
    logger.info("\n" + "=" * 80)
    logger.info("ML MODEL TRAINING")
    logger.info("=" * 80)
    
    feature_engineer = FeatureEngineer()
    trained_predictors = {}
    
    for symbol, ohlc_df in collected_data.items():
        if ohlc_df.empty or len(ohlc_df) < 50:
            logger.warning(f"⚠ Insufficient data for {symbol} ({len(ohlc_df)} points), skipping training")
            continue
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Training ML model for {symbol}")
        logger.info(f"{'='*60}")
        
        try:
            # Prepare features
            logger.info("Preparing features...")
            features = feature_engineer.prepare_features(ohlc_df)
            labels = feature_engineer.create_labels(ohlc_df)
            
            # Align indices
            common_idx = features.index.intersection(labels.index)
            features = features.loc[common_idx]
            labels = labels.loc[common_idx]
            
            logger.info(f"✓ Prepared {len(features)} feature vectors")
            logger.info(f"  Features: {list(features.columns)}")
            
            if len(features) < 50:
                logger.warning(f"⚠ Insufficient data for training ({len(features)} samples), need at least 50")
                continue
            
            # Initialize predictor
            model_path = Path(config.ml.model_path) / symbol
            predictor = MLPredictor(
                model_path=str(model_path),
                model_type=model_type
            )
            
            # Train model
            logger.info(f"Training {model_type} model...")
            metrics = predictor.train(features, labels, retrain=True)
            
            if 'error' in metrics:
                logger.error(f"✗ Training failed: {metrics.get('error')}")
                continue
            
            logger.info(f"✓ Model trained successfully!")
            logger.info(f"  Training Accuracy: {metrics.get('train_accuracy', 0):.2%}")
            logger.info(f"  Test Accuracy: {metrics.get('test_accuracy', 0):.2%}")
            logger.info(f"  Model saved to: {model_path}")
            
            trained_predictors[symbol] = predictor
            
            # Model is automatically saved by train() method
        
        except Exception as e:
            logger.error(f"Error training model for {symbol}: {e}", exc_info=True)
    
    return trained_predictors


def main():
    """Main function for data collection and ML training."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Collect market data and train ML models (NO ORDER PLACEMENT)"
    )
    parser.add_argument(
        '--symbols',
        nargs='+',
        help='Symbols to collect data for (default: from config)'
    )
    parser.add_argument(
        '--hours',
        type=int,
        default=720,
        help='Number of hours of historical data to collect (default: 720 = 30 days)'
    )
    parser.add_argument(
        '--model-type',
        choices=['random_forest', 'gradient_boosting'],
        default='random_forest',
        help='Type of ML model to train (default: random_forest)'
    )
    parser.add_argument(
        '--skip-training',
        action='store_true',
        help='Skip ML training, only collect data'
    )
    parser.add_argument(
        '--skip-collection',
        action='store_true',
        help='Skip data collection, only train on existing data'
    )
    parser.add_argument(
        '--list-products',
        nargs='?',
        const='',
        help='List available products (optionally filter by search term, e.g., --list-products SOL)'
    )
    parser.add_argument(
        '--show-raw',
        action='store_true',
        help='Show raw API response when listing products (for debugging)'
    )
    
    args = parser.parse_args()
    
    # Handle list-products option
    if args.list_products is not None:
        logger.info("Loading configuration...")
        config = Config()
        list_available_products(
            config, 
            args.list_products if args.list_products else None,
            show_raw=args.show_raw
        )
        return
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = Config()
        
        # Check if API credentials are set
        if not config.delta.api_key or not config.delta.api_secret:
            logger.error("=" * 80)
            logger.error("ERROR: Delta Exchange API credentials not set!")
            logger.error("=" * 80)
            logger.error("Please use one of the following methods:")
            logger.error("")
            logger.error("Method 1: Environment Variables (Recommended)")
            logger.error("  export DELTA_API_KEY=your_api_key_here")
            logger.error("  export DELTA_API_SECRET=your_api_secret_here")
            logger.error("")
            logger.error("Method 2: .env file (requires python-dotenv)")
            logger.error("  pip install python-dotenv")
            logger.error("  Create .env file with:")
            logger.error("    DELTA_API_KEY=your_api_key_here")
            logger.error("    DELTA_API_SECRET=your_api_secret_here")
            logger.error("")
            logger.error("See env.example for a template.")
            logger.error("=" * 80)
            sys.exit(1)
        
        config.validate()
        logger.info("✓ Configuration loaded")
        
        # Collect data
        collected_data = {}
        if not args.skip_collection:
            collected_data = collect_data(
                config=config,
                symbols=args.symbols,
                hours=args.hours
            )
        else:
            logger.info("Skipping data collection (--skip-collection flag set)")
            # Load existing data
            collector = DataCollector(
                DeltaExchangeClient(
                    api_key=config.delta.api_key,
                    api_secret=config.delta.api_secret,
                    base_url=config.delta.base_url
                ),
                config
            )
            symbols = args.symbols or config.trading.products
            for symbol in symbols:
                df = collector.load_historical_data(
                    symbol=symbol,
                    resolution=config.trading.default_timeframe
                )
                if not df.empty:
                    collected_data[symbol] = df
                    logger.info(f"Loaded existing data for {symbol}: {len(df)} points")
        
        if not collected_data:
            logger.error("No data collected or loaded. Exiting.")
            return
        
        # Train models
        if not args.skip_training:
            trained_predictors = train_ml_models(
                config=config,
                collected_data=collected_data,
                model_type=args.model_type
            )
            
            if trained_predictors:
                logger.info(f"\n{'='*80}")
                logger.info("SUMMARY")
                logger.info(f"{'='*80}")
                logger.info(f"✓ Successfully trained {len(trained_predictors)} models:")
                for symbol in trained_predictors.keys():
                    logger.info(f"  - {symbol}")
            else:
                logger.warning("No models were trained successfully")
        else:
            logger.info("Skipping ML training (--skip-training flag set)")
        
        logger.info("\n" + "=" * 80)
        logger.info("DATA COLLECTION AND TRAINING COMPLETE")
        logger.info("=" * 80)
        logger.info("⚠ REMINDER: No orders were placed during this run")
        logger.info("=" * 80)
    
    except KeyboardInterrupt:
        logger.info("\n\nInterrupted by user. Exiting...")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

