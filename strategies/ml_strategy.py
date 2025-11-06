"""ML-based trading strategy."""
from typing import Dict
import logging
import numpy as np

from strategies.base_strategy import BaseStrategy, Signal
from features.feature_engineering import FeatureEngineer
from features.ml_models import MLPredictor

logger = logging.getLogger(__name__)


class MLStrategy(BaseStrategy):
    """ML-based trading strategy."""
    
    def __init__(self, name: str, config: Dict, predictor: MLPredictor):
        """
        Initialize ML strategy.
        
        Args:
            name: Strategy name
            config: Strategy configuration
            predictor: ML predictor instance
        """
        super().__init__(name, config)
        self.predictor = predictor
        self.feature_engineer = FeatureEngineer()
        self.confidence_threshold = config.get('confidence_threshold', 0.6)
        self.position_size = config.get('position_size', 0.1)
        self.stop_loss_pct = config.get('stop_loss_pct', 0.02)
        self.take_profit_pct = config.get('take_profit_pct', 0.04)
    
    def generate_signal(self, data: Dict) -> Signal:
        """
        Generate signal using ML model.
        
        Args:
            data: Market data
            
        Returns:
            Trading signal
        """
        try:
            ohlc_df = data.get('ohlc')
            if ohlc_df is None or ohlc_df.empty:
                return Signal(
                    symbol=data.get('symbol', ''),
                    action='hold',
                    size=0,
                    reason='No OHLC data'
                )
            
            # Prepare features
            features_df = self.feature_engineer.prepare_features(ohlc_df)
            
            if features_df.empty or len(features_df) < 10:
                return Signal(
                    symbol=data.get('symbol', ''),
                    action='hold',
                    size=0,
                    reason='Insufficient features'
                )
            
            # Get prediction
            logger.debug(f"[{self.name}] Preparing features for prediction (last {len(features_df)} rows)")
            predictions, probabilities = self.predictor.predict(features_df.tail(1))
            signal_value = self.predictor.predict_signal(
                features_df.tail(1),
                threshold=self.confidence_threshold
            )
            
            # Log prediction details
            if len(probabilities) > 0 and len(probabilities[0]) >= 3:
                prob = probabilities[0]
                max_prob = float(np.max(prob))
                logger.info(f"[{self.name}] ML Prediction: {int(predictions[0])} (confidence: {max_prob:.3f}, threshold: {self.confidence_threshold:.3f})")
                logger.debug(f"[{self.name}] Class probabilities: {prob}")
            else:
                logger.warning(f"[{self.name}] Could not get prediction probabilities")
            
            # Get current price
            current_price = float(ohlc_df['close'].iloc[-1])
            
            # Determine action
            if signal_value == 1:
                action = 'buy'
                size = self.position_size
                stop_loss = current_price * (1 - self.stop_loss_pct)
                take_profit = current_price * (1 + self.take_profit_pct)
            elif signal_value == -1:
                action = 'sell'
                size = self.position_size
                stop_loss = current_price * (1 + self.stop_loss_pct)
                take_profit = current_price * (1 - self.take_profit_pct)
            else:
                action = 'hold'
                size = 0
                stop_loss = None
                take_profit = None
            
            # Check if we already have a position
            symbol = data.get('symbol', '')
            existing_position = self.get_position(symbol)
            
            if existing_position and action != 'hold':
                # Only generate signal if we don't have a position or want to close
                if existing_position.get('side') == action:
                    action = 'hold'
                    size = 0
            
            return Signal(
                symbol=symbol,
                action=action,
                size=size,
                price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence=abs(signal_value),
                reason=f'ML prediction: {signal_value}'
            )
        
        except Exception as e:
            logger.error(f"Error generating ML signal: {e}")
            return Signal(
                symbol=data.get('symbol', ''),
                action='hold',
                size=0,
                reason=f'Error: {str(e)}'
            )
    
    def should_close_position(self, position: Dict, data: Dict) -> bool:
        """
        Check if position should be closed based on stop loss/take profit.
        
        Args:
            position: Current position
            data: Market data
            
        Returns:
            True if position should be closed
        """
        try:
            ohlc_df = data.get('ohlc')
            if ohlc_df is None or ohlc_df.empty:
                return False
            
            current_price = float(ohlc_df['close'].iloc[-1])
            side = position.get('side', '')
            stop_loss = position.get('stop_loss')
            take_profit = position.get('take_profit')
            
            if side == 'buy':
                if stop_loss and current_price <= stop_loss:
                    return True
                if take_profit and current_price >= take_profit:
                    return True
            elif side == 'sell':
                if stop_loss and current_price >= stop_loss:
                    return True
                if take_profit and current_price <= take_profit:
                    return True
            
            # Check ML signal for reversal
            signal = self.generate_signal(data)
            if signal.action != 'hold' and signal.action != side:
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error checking position close: {e}")
            return False

