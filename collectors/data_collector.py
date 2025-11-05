"""Data collection module for market data."""
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
from pathlib import Path

from collectors.delta_client import DeltaExchangeClient
from config.config import Config

logger = logging.getLogger(__name__)


class DataCollector:
    """Collects and stores market data from Delta Exchange."""
    
    def __init__(self, client: DeltaExchangeClient, config: Config):
        """
        Initialize data collector.
        
        Args:
            client: Delta Exchange client
            config: Configuration object
        """
        self.client = client
        self.config = config
        self.data_dir = config.data_dir
        self.data_dir.mkdir(exist_ok=True)
    
    def collect_ohlc(
        self,
        symbol: str,
        resolution: str = "1h",
        hours: int = 24,
        save: bool = True
    ) -> pd.DataFrame:
        """
        Collect OHLC data.
        
        Args:
            symbol: Product symbol
            resolution: Timeframe
            hours: Number of hours of data to collect
            save: Whether to save to disk
            
        Returns:
            DataFrame with OHLC data
        """
        end_time = int(datetime.now().timestamp())
        start_time = int((datetime.now() - timedelta(hours=hours)).timestamp())
        
        try:
            data = self.client.get_ohlc(
                symbol=symbol,
                resolution=resolution,
                start=start_time,
                end=end_time,
                limit=1000
            )
            
            if not data:
                logger.warning(f"No OHLC data for {symbol}")
                logger.warning(f"  This may mean:")
                logger.warning(f"  - The symbol '{symbol}' doesn't exist on Delta Exchange")
                logger.warning(f"  - The symbol format is incorrect (try checking product list)")
                logger.warning(f"  - Historical data is not available for this symbol")
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            df.columns = ['open', 'high', 'low', 'close', 'volume']
            df = df.astype(float)
            
            if save:
                file_path = self.data_dir / f"{symbol}_{resolution}_ohlc.csv"
                df.to_csv(file_path)
                logger.info(f"Saved OHLC data to {file_path}")
            
            return df
        
        except Exception as e:
            logger.error(f"Error collecting OHLC data for {symbol}: {e}")
            logger.error(f"  Exception type: {type(e).__name__}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                logger.error(f"  API Response: {e.response.text}")
            return pd.DataFrame()
    
    def collect_orderbook(self, symbol: str) -> Dict:
        """
        Collect orderbook data.
        
        Args:
            symbol: Product symbol
            
        Returns:
            Orderbook data
        """
        try:
            orderbook = self.client.get_l2_orderbook(symbol)
            return orderbook
        except Exception as e:
            logger.error(f"Error collecting orderbook for {symbol}: {e}")
            return {}
    
    def collect_trades(self, symbol: str, limit: int = 100) -> pd.DataFrame:
        """
        Collect recent trades.
        
        Args:
            symbol: Product symbol
            limit: Number of trades to collect
            
        Returns:
            DataFrame with trades
        """
        try:
            trades = self.client.get_trades(symbol, limit=limit)
            if not trades:
                return pd.DataFrame()
            
            df = pd.DataFrame(trades)
            df['time'] = pd.to_datetime(df['timestamp'], unit='s')
            return df
        
        except Exception as e:
            logger.error(f"Error collecting trades for {symbol}: {e}")
            return pd.DataFrame()
    
    def collect_market_data(
        self,
        symbols: List[str],
        resolution: str = "1h",
        hours: int = 24
    ) -> Dict[str, pd.DataFrame]:
        """
        Collect market data for multiple symbols.
        
        Args:
            symbols: List of symbols
            resolution: Timeframe
            hours: Number of hours of data
            
        Returns:
            Dictionary of DataFrames keyed by symbol
        """
        data = {}
        for symbol in symbols:
            logger.info(f"Collecting data for {symbol}")
            df = self.collect_ohlc(symbol, resolution, hours)
            if not df.empty:
                data[symbol] = df
        return data
    
    def get_ticker_data(self, symbols: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Get current ticker data.
        
        Args:
            symbols: Optional list of symbols to filter
            
        Returns:
            DataFrame with ticker data
        """
        try:
            tickers = self.client.get_tickers()
            df = pd.DataFrame(tickers)
            
            if symbols:
                df = df[df['symbol'].isin(symbols)]
            
            return df
        
        except Exception as e:
            logger.error(f"Error collecting ticker data: {e}")
            return pd.DataFrame()
    
    def load_historical_data(self, symbol: str, resolution: str = "1h") -> pd.DataFrame:
        """
        Load historical data from disk.
        
        Args:
            symbol: Product symbol
            resolution: Timeframe
            
        Returns:
            DataFrame with historical data
        """
        file_path = self.data_dir / f"{symbol}_{resolution}_ohlc.csv"
        if file_path.exists():
            try:
                df = pd.read_csv(file_path, index_col='time', parse_dates=True)
                return df
            except (KeyError, ValueError):
                # Try reading without index_col if 'time' column doesn't exist
                df = pd.read_csv(file_path, parse_dates=True)
                if 'time' in df.columns:
                    df.set_index('time', inplace=True)
                elif df.index.name == 'time' or df.index.dtype == 'datetime64[ns]':
                    # Already has time index
                    pass
                return df
        return pd.DataFrame()
    
    def update_historical_data(self, symbol: str, resolution: str = "1h") -> pd.DataFrame:
        """
        Update historical data by appending new data.
        
        Args:
            symbol: Product symbol
            resolution: Timeframe
            
        Returns:
            Updated DataFrame
        """
        # Load existing data
        existing_df = self.load_historical_data(symbol, resolution)
        
        # Collect new data
        new_df = self.collect_ohlc(symbol, resolution, hours=24, save=False)
        
        if existing_df.empty:
            return new_df
        
        if new_df.empty:
            return existing_df
        
        # Combine and remove duplicates
        combined = pd.concat([existing_df, new_df])
        combined = combined[~combined.index.duplicated(keep='last')]
        combined.sort_index(inplace=True)
        
        # Save updated data
        file_path = self.data_dir / f"{symbol}_{resolution}_ohlc.csv"
        combined.to_csv(file_path)
        
        return combined

