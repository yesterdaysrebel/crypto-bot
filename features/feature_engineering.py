"""Feature engineering for ML models."""
import pandas as pd
import numpy as np
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """Feature engineering for trading signals."""
    
    @staticmethod
    def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators.
        
        Args:
            df: DataFrame with OHLC data
            
        Returns:
            DataFrame with added indicators
        """
        df = df.copy()
        
        # Moving averages
        df['sma_10'] = df['close'].rolling(window=10).mean()
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        
        # MACD
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        df['bb_width'] = df['bb_upper'] - df['bb_lower']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # ATR (Average True Range)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(window=14).mean()
        
        # Volume indicators
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Price change
        df['price_change'] = df['close'].pct_change()
        df['price_change_5'] = df['close'].pct_change(5)
        df['price_change_10'] = df['close'].pct_change(10)
        
        # Volatility
        df['volatility'] = df['close'].rolling(window=20).std()
        df['volatility_ratio'] = df['volatility'] / df['close'].rolling(window=20).mean()
        
        # Momentum
        df['momentum'] = df['close'].pct_change(10)
        df['momentum_5'] = df['close'].pct_change(5)
        
        # Support/Resistance levels (simplified)
        df['high_20'] = df['high'].rolling(window=20).max()
        df['low_20'] = df['low'].rolling(window=20).min()
        
        return df
    
    @staticmethod
    def calculate_orderbook_features(orderbook: Dict) -> Dict:
        """
        Calculate features from orderbook data.
        
        Args:
            orderbook: Orderbook data
            
        Returns:
            Dictionary of features
        """
        features = {}
        
        try:
            bids = orderbook.get('buy', [])
            asks = orderbook.get('sell', [])
            
            if bids and asks:
                best_bid = float(bids[0][0])
                best_ask = float(asks[0][0])
                
                features['spread'] = best_ask - best_bid
                features['spread_pct'] = (features['spread'] / best_bid) * 100
                features['mid_price'] = (best_bid + best_ask) / 2
                
                # Bid/Ask volumes
                bid_volume = sum(float(b[1]) for b in bids[:10])
                ask_volume = sum(float(a[1]) for a in asks[:10])
                features['bid_ask_ratio'] = bid_volume / ask_volume if ask_volume > 0 else 0
                
                # Orderbook imbalance
                features['orderbook_imbalance'] = (bid_volume - ask_volume) / (bid_volume + ask_volume) if (bid_volume + ask_volume) > 0 else 0
                
        except Exception as e:
            logger.error(f"Error calculating orderbook features: {e}")
        
        return features
    
    @staticmethod
    def prepare_features(df: pd.DataFrame, window: int = 100) -> pd.DataFrame:
        """
        Prepare features for ML model.
        
        Args:
            df: DataFrame with OHLC and indicators
            window: Number of periods to use
            
        Returns:
            DataFrame with features ready for ML
        """
        df = df.copy()
        
        # Calculate indicators
        df = FeatureEngineer.calculate_technical_indicators(df)
        
        # Select relevant features
        feature_cols = [
            'open', 'high', 'low', 'close', 'volume',
            'sma_10', 'sma_20', 'sma_50',
            'macd', 'macd_signal', 'macd_hist',
            'rsi',
            'bb_upper', 'bb_lower', 'bb_position',
            'atr',
            'volume_ratio',
            'price_change', 'price_change_5', 'price_change_10',
            'volatility', 'volatility_ratio',
            'momentum', 'momentum_5'
        ]
        
        # Filter to available columns
        available_cols = [col for col in feature_cols if col in df.columns]
        df_features = df[available_cols].copy()
        
        # Fill NaN values
        df_features = df_features.ffill().fillna(0)
        
        # Take last window rows
        if len(df_features) > window:
            df_features = df_features.tail(window)
        
        return df_features
    
    @staticmethod
    def create_labels(df: pd.DataFrame, forward_periods: int = 5, threshold: float = 0.02) -> pd.Series:
        """
        Create labels for supervised learning (predict future price direction).
        
        Args:
            df: DataFrame with price data
            forward_periods: Number of periods to look ahead
            threshold: Minimum price change to consider as signal
            
        Returns:
            Series with labels (1 for buy, -1 for sell, 0 for hold)
        """
        future_return = df['close'].shift(-forward_periods) / df['close'] - 1
        
        labels = pd.Series(0, index=df.index)
        labels[future_return > threshold] = 1  # Buy signal
        labels[future_return < -threshold] = -1  # Sell signal
        
        return labels

