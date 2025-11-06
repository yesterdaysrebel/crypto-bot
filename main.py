"""Main trading bot orchestrator."""
import asyncio
import logging
import signal
import sys
from typing import Dict, List
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

from config.config import Config
from collectors.delta_client import DeltaExchangeClient
from collectors.data_collector import DataCollector
from execution.order_manager import OrderManager
from execution.position_manager import PositionManager
from strategies.base_strategy import BaseStrategy
from strategies.ml_strategy import MLStrategy
from features.ml_models import MLPredictor
from features.feature_engineering import FeatureEngineer
from trade_logging.trade_logger import TradeLogger
from trade_logging.trade_analyzer import TradeAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class TradingBot:
    """Main trading bot orchestrator."""
    
    def __init__(self, config: Config):
        """
        Initialize trading bot.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.config.validate()
        
        # Initialize clients
        self.client = DeltaExchangeClient(
            api_key=config.delta.api_key,
            api_secret=config.delta.api_secret,
            base_url=config.delta.base_url
        )
        
        # Initialize trade logger
        self.trade_logger = TradeLogger(
            log_dir="trade_logs",
            log_format="both",  # JSON and CSV
            enable_console=True
        )
        self.trade_analyzer = TradeAnalyzer(self.trade_logger)
        
        # Initialize managers
        self.data_collector = DataCollector(self.client, config)
        self.order_manager = OrderManager(self.client, config, self.trade_logger)
        self.position_manager = PositionManager(self.client, self.trade_logger)
        
        # Initialize strategies
        self.strategies: List[BaseStrategy] = []
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=5)
        
        # Product mapping
        self.product_map: Dict[str, int] = {}
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info("Received shutdown signal, stopping bot...")
        self.stop()
    
    def initialize_products(self):
        """Initialize product mapping."""
        try:
            logger.info("Initializing product mapping...")
            products = self.client.get_products()
            for product in products:
                symbol = product.get('symbol')
                product_id = product.get('id')
                if symbol and product_id:
                    self.product_map[symbol] = product_id
            logger.info(f"Initialized {len(self.product_map)} products")
            if self.config.trading.products:
                logger.info(f"Trading products configured: {self.config.trading.products}")
                for symbol in self.config.trading.products:
                    if symbol in self.product_map:
                        logger.info(f"  ✓ {symbol} -> Product ID: {self.product_map[symbol]}")
                    else:
                        logger.warning(f"  ✗ {symbol} not found in product list")
        except Exception as e:
            logger.error(f"Error initializing products: {e}", exc_info=True)
    
    def initialize_strategies(self):
        """Initialize trading strategies."""
        try:
            logger.info("Initializing trading strategies...")
            
            # Initialize ML predictor
            ml_predictor = MLPredictor(
                model_path=self.config.ml.model_path,
                model_type="random_forest"
            )
            
            # Try to load existing model
            if not ml_predictor.load_model():
                logger.info("No existing model found, will train on first run")
            else:
                logger.info("ML model loaded successfully")
            
            # Create ML strategy for each product
            logger.info(f"Creating strategies for {len(self.config.trading.products)} products: {self.config.trading.products}")
            for symbol in self.config.trading.products:
                if symbol in self.product_map:
                    strategy_config = {
                        'confidence_threshold': self.config.ml.prediction_threshold,
                        'position_size': self.config.trading.max_position_size * 0.1,
                        'stop_loss_pct': 0.02,
                        'take_profit_pct': 0.04
                    }
                    strategy = MLStrategy(
                        name=f"ML_{symbol}",
                        config=strategy_config,
                        predictor=ml_predictor
                    )
                    self.strategies.append(strategy)
                    logger.info(f"  ✓ Initialized strategy: {strategy.name} "
                               f"(confidence_threshold: {strategy_config['confidence_threshold']:.2f}, "
                               f"position_size: {strategy_config['position_size']:.4f})")
                else:
                    logger.warning(f"  ✗ Product {symbol} not found in product map, skipping strategy creation")
            
            logger.info(f"Successfully initialized {len(self.strategies)} strategies")
        except Exception as e:
            logger.error(f"Error initializing strategies: {e}", exc_info=True)
    
    def collect_market_data(self, symbol: str) -> Dict:
        """Collect market data for a symbol."""
        try:
            # Try to load existing data first, then update with new data
            ohlc_df = self.data_collector.update_historical_data(
                symbol=symbol,
                resolution=self.config.trading.default_timeframe
            )
            
            # If no historical data, collect fresh
            if ohlc_df.empty:
                logger.info(f"  No existing data found, collecting fresh OHLC data for {symbol}...")
                ohlc_df = self.data_collector.collect_ohlc(
                    symbol=symbol,
                    resolution=self.config.trading.default_timeframe,
                    hours=24,
                    save=True
                )
            
            if ohlc_df.empty:
                logger.warning(f"  Failed to collect OHLC data for {symbol}")
                return {}
            
            # Collect orderbook
            try:
                orderbook = self.data_collector.collect_orderbook(symbol)
            except Exception as e:
                logger.debug(f"  Could not collect orderbook for {symbol}: {e}")
                orderbook = {}
            
            # Collect ticker
            try:
                ticker_df = self.data_collector.get_ticker_data([symbol])
                ticker = ticker_df.iloc[0].to_dict() if not ticker_df.empty else {}
            except Exception as e:
                logger.debug(f"  Could not collect ticker for {symbol}: {e}")
                ticker = {}
            
            return {
                'symbol': symbol,
                'ohlc': ohlc_df,
                'orderbook': orderbook,
                'ticker': ticker,
                'timestamp': datetime.now()
            }
        except Exception as e:
            logger.error(f"Error collecting market data for {symbol}: {e}", exc_info=True)
            return {}
    
    def train_ml_models(self):
        """Train ML models on historical data."""
        try:
            logger.info("Training ML models...")
            predictor = None
            
            # Find ML predictor from strategies
            for strategy in self.strategies:
                if isinstance(strategy, MLStrategy):
                    predictor = strategy.predictor
                    break
            
            if predictor is None:
                logger.warning("No ML predictor found")
                return
            
            # Collect data for training
            feature_engineer = FeatureEngineer()
            all_features = []
            all_labels = []
            
            for symbol in self.config.trading.products:
                # Try to load existing historical data first
                ohlc_df = self.data_collector.load_historical_data(
                    symbol=symbol,
                    resolution=self.config.trading.default_timeframe
                )
                
                # If not enough data, collect from API
                if ohlc_df.empty or len(ohlc_df) < 50:
                    ohlc_df = self.data_collector.collect_ohlc(
                        symbol=symbol,
                        resolution=self.config.trading.default_timeframe,
                        hours=168,  # 7 days
                        save=True  # Save for future use
                    )
                
                if not ohlc_df.empty and len(ohlc_df) > 50:
                    features = feature_engineer.prepare_features(ohlc_df)
                    labels = feature_engineer.create_labels(ohlc_df)
                    
                    # Align indices
                    common_idx = features.index.intersection(labels.index)
                    features = features.loc[common_idx]
                    labels = labels.loc[common_idx]
                    
                    all_features.append(features)
                    all_labels.append(labels)
            
            if all_features:
                import pandas as pd
                X = pd.concat(all_features)
                y = pd.concat(all_labels)
                
                metrics = predictor.train(X, y, retrain=True)
                logger.info(f"ML model training completed: {metrics}")
            else:
                logger.warning("Insufficient data for training")
        
        except Exception as e:
            logger.error(f"Error training ML models: {e}")
    
    def run_strategy(self, strategy: BaseStrategy, symbol: str):
        """Run a single strategy for a symbol."""
        if not strategy.is_active:
            logger.warning(f"Strategy {strategy.name} is not active, skipping")
            return
        
        try:
            # Collect market data
            logger.info(f"[{strategy.name}] Collecting market data for {symbol}...")
            market_data = self.collect_market_data(symbol)
            
            if not market_data or market_data.get('ohlc') is None:
                logger.warning(f"[{strategy.name}] No market data collected for {symbol}")
                return
            
            ohlc_df = market_data.get('ohlc')
            if ohlc_df is not None and not ohlc_df.empty:
                current_price = float(ohlc_df['close'].iloc[-1])
                logger.info(f"[{strategy.name}] Market data collected: {len(ohlc_df)} candles, current price: {current_price:.2f}")
            else:
                logger.warning(f"[{strategy.name}] OHLC data is empty for {symbol}")
                return
            
            # Update position in strategy
            position = self.position_manager.get_position(symbol)
            if position:
                strategy.update_position(symbol, position)
            
            # Check if position should be closed
            if position and strategy.should_close_position(position, market_data):
                product_id = self.product_map.get(symbol)
                if product_id:
                    # Get current price for logging
                    current_price = float(market_data.get('ohlc', pd.DataFrame()).iloc[-1]['close'] if not market_data.get('ohlc', pd.DataFrame()).empty else position.get('mark_price', 0))
                    
                    # Calculate P&L
                    entry_price = position.get('entry_price', 0)
                    position_size = abs(position.get('size', 0))
                    side = position.get('side', 'buy')
                    
                    if side == 'buy':
                        pnl = (current_price - entry_price) * position_size
                        pnl_pct = ((current_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
                    else:
                        pnl = (entry_price - current_price) * position_size
                        pnl_pct = ((entry_price - current_price) / entry_price) * 100 if entry_price > 0 else 0
                    
                    # Log position closure
                    self.trade_logger.log_position_closed(
                        symbol=symbol,
                        exit_price=current_price,
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                        reason=f'Strategy close: {strategy.name}'
                    )
                    
                    self.position_manager.close_position(product_id, symbol)
                    logger.info(f"Closed position for {symbol} based on strategy {strategy.name}")
                return
            
            # Generate signal
            logger.info(f"[{strategy.name}] Generating signal for {symbol}...")
            signal = strategy.generate_signal(market_data)
            
            # Log signal details (including hold signals)
            logger.info(f"[{strategy.name}] Signal generated: {signal.action.upper()} | "
                       f"Size: {signal.size:.4f} | "
                       f"Confidence: {signal.confidence:.2f} | "
                       f"Reason: {signal.reason}")
            
            if signal.action != 'hold':
                self.trade_logger.log_signal(
                    symbol=symbol,
                    strategy=strategy.name,
                    signal_action=signal.action,
                    signal_confidence=signal.confidence,
                    signal_reason=signal.reason,
                    current_price=float(market_data.get('ohlc', pd.DataFrame()).iloc[-1]['close'] if not market_data.get('ohlc', pd.DataFrame()).empty else 0)
                )
            else:
                logger.info(f"[{strategy.name}] Signal is HOLD - {signal.reason}")
            
            if signal.action != 'hold' and signal.size > 0:
                product_id = self.product_map.get(symbol)
                if product_id:
                    # Check if we already have a position
                    existing_position = self.position_manager.get_position(symbol)
                    if not existing_position:
                        # Check if there are active orders for this symbol
                        active_orders = self.order_manager.get_active_orders(product_id)
                        if active_orders:
                            logger.info(f"[{strategy.name}] Active orders already exist for {symbol}, skipping new order")
                        else:
                            # Place new order (order manager will also check for positions and orders)
                            logger.info(f"[{strategy.name}] Attempting to place {signal.action} order for {symbol} (size: {signal.size:.4f})")
                            order = self.order_manager.place_order_from_signal(
                                signal, 
                                product_id,
                                position_manager=self.position_manager
                            )
                            if order:
                                logger.info(f"[{strategy.name}] ✓ Order placed successfully: {signal.action} {signal.size:.4f} for {symbol}")
                            else:
                                logger.warning(f"[{strategy.name}] ✗ Failed to place order for {symbol}")
                    else:
                        logger.info(f"[{strategy.name}] Position already exists for {symbol} ({existing_position.get('side')} {abs(existing_position.get('size', 0)):.4f}), skipping order placement")
                else:
                    logger.error(f"[{strategy.name}] Product ID not found for {symbol}")
            elif signal.action == 'hold':
                logger.debug(f"[{strategy.name}] No action taken - signal is HOLD")
            elif signal.size == 0:
                logger.warning(f"[{strategy.name}] Signal size is 0, skipping order placement")
        
        except Exception as e:
            logger.error(f"Error running strategy {strategy.name} for {symbol}: {e}")
    
    def run_cycle(self):
        """Run one trading cycle."""
        try:
            logger.info("=" * 60)
            logger.info("Starting trading cycle")
            
            # Update positions
            positions = self.position_manager.update_positions()
            if positions:
                logger.info(f"Current positions: {list(positions.keys())}")
                for symbol, pos in positions.items():
                    logger.info(f"  {symbol}: {pos.get('side')} {abs(pos.get('size', 0)):.4f} @ {pos.get('entry_price', 0):.2f} (P&L: {pos.get('pnl', 0):.2f})")
            else:
                logger.info("No open positions")
            
            # Run each strategy for each product
            logger.info(f"Running {len(self.strategies)} strategies")
            for strategy in self.strategies:
                # Extract symbol from strategy name (format: ML_SYMBOL)
                symbol = strategy.name.split('_', 1)[1] if '_' in strategy.name else None
                if symbol and symbol in self.product_map:
                    logger.info(f"Running strategy {strategy.name} for {symbol}")
                    self.run_strategy(strategy, symbol)
                else:
                    logger.warning(f"Strategy {strategy.name}: symbol {symbol} not found in product map")
            
            logger.info("Trading cycle completed")
            logger.info("=" * 60)
        
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}", exc_info=True)
    
    def start(self):
        """Start the trading bot."""
        logger.info("Starting trading bot...")
        
        # Initialize
        self.initialize_products()
        self.initialize_strategies()
        
        # Train ML models on first run
        self.train_ml_models()
        
        self.running = True
        cycle_interval = 60  # Run every 60 seconds
        last_retrain_time = time.time()
        retrain_interval_seconds = self.config.ml.retrain_interval_hours * 3600
        
        logger.info("Trading bot started")
        logger.info(f"Model retrain interval: {self.config.ml.retrain_interval_hours} hours")
        
        while self.running:
            try:
                start_time = time.time()
                
                # Run trading cycle
                self.run_cycle()
                
                # Check if it's time to retrain models
                current_time = time.time()
                time_since_last_retrain = current_time - last_retrain_time
                if time_since_last_retrain >= retrain_interval_seconds:
                    logger.info(f"Retrain interval reached ({self.config.ml.retrain_interval_hours} hours), retraining models...")
                    self.train_ml_models()
                    last_retrain_time = current_time
                    logger.info(f"Next retrain scheduled in {self.config.ml.retrain_interval_hours} hours")
                
                # Log status
                total_pnl = self.position_manager.get_total_pnl()
                num_positions = len(self.position_manager.get_all_positions())
                logger.info(f"Cycle completed. Total P&L: {total_pnl:.2f} | Open positions: {num_positions}")
                
                # Print trade summary periodically (every 10 cycles)
                if int(time.time()) % 600 == 0:  # Every 10 minutes
                    self.trade_analyzer.print_summary()
                
                # Sleep until next cycle
                elapsed = time.time() - start_time
                sleep_time = max(0, cycle_interval - elapsed)
                time.sleep(sleep_time)
            
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(10)  # Wait before retrying
    
    def stop(self):
        """Stop the trading bot."""
        logger.info("Stopping trading bot...")
        self.running = False
        
        # Cancel all active orders
        for symbol in self.config.trading.products:
            product_id = self.product_map.get(symbol)
            if product_id:
                cancelled = self.order_manager.cancel_all_orders(product_id)
                logger.info(f"Cancelled {cancelled} orders for {symbol}")
        
        # Deactivate strategies
        for strategy in self.strategies:
            strategy.deactivate()
        
        logger.info("Trading bot stopped")


def main():
    """Main entry point."""
    try:
        config = Config()
        bot = TradingBot(config)
        bot.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

