"""ML models for trading predictions."""
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
import logging
from pathlib import Path
import pickle
import joblib

try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import accuracy_score, classification_report
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logging.warning("scikit-learn not available. ML features will be limited.")

logger = logging.getLogger(__name__)


class MLPredictor:
    """ML model for price prediction."""
    
    def __init__(self, model_path: str = "models", model_type: str = "random_forest"):
        """
        Initialize ML predictor.
        
        Args:
            model_path: Path to save/load models
            model_type: Type of model ("random_forest" or "gradient_boosting")
        """
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn is required for ML features. Install with: pip install scikit-learn")
        
        self.model_path = Path(model_path)
        self.model_path.mkdir(parents=True, exist_ok=True)
        self.model_type = model_type
        
        # Validate model type
        if model_type not in ["random_forest", "gradient_boosting"]:
            raise ValueError(f"Unknown model type: {model_type}. Must be 'random_forest' or 'gradient_boosting'")
        
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
    
    def _create_model(self):
        """Create the ML model."""
        if self.model_type == "random_forest":
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
        elif self.model_type == "gradient_boosting":
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                random_state=42
            )
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")
    
    def train(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        test_size: float = 0.2,
        retrain: bool = False
    ) -> Dict:
        """
        Train the ML model.
        
        Args:
            X: Feature matrix
            y: Target labels
            test_size: Proportion of data for testing
            retrain: Whether to retrain existing model
            
        Returns:
            Training metrics
        """
        if self.model is None or retrain:
            self._create_model()
        
        # Prepare data
        X = X.fillna(0)
        y = y.fillna(0)
        
        # Remove rows with NaN in target
        valid_idx = ~(y.isna() | X.isna().any(axis=1))
        X = X[valid_idx]
        y = y[valid_idx]
        
        if len(X) < 10:
            logger.warning("Insufficient data for training")
            return {"error": "Insufficient data"}
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y if len(y.unique()) > 1 else None
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train model
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate
        train_pred = self.model.predict(X_train_scaled)
        test_pred = self.model.predict(X_test_scaled)
        
        train_accuracy = accuracy_score(y_train, train_pred)
        test_accuracy = accuracy_score(y_test, test_pred)
        
        self.is_trained = True
        
        metrics = {
            "train_accuracy": train_accuracy,
            "test_accuracy": test_accuracy,
            "model_type": self.model_type
        }
        
        logger.info(f"Model trained. Train accuracy: {train_accuracy:.4f}, Test accuracy: {test_accuracy:.4f}")
        
        # Save model
        self.save_model()
        
        return metrics
    
    def predict(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Make predictions.
        
        Args:
            X: Feature matrix
            
        Returns:
            Tuple of (predictions, probabilities)
        """
        if not self.is_trained or self.model is None:
            logger.warning("Model not trained. Returning default predictions.")
            return np.zeros(len(X)), np.zeros((len(X), 3))
        
        X = X.fillna(0)
        X_scaled = self.scaler.transform(X)
        
        predictions = self.model.predict(X_scaled)
        
        # Get probabilities if available
        if hasattr(self.model, 'predict_proba'):
            probabilities = self.model.predict_proba(X_scaled)
        else:
            probabilities = np.zeros((len(X), len(np.unique(predictions))))
        
        return predictions, probabilities
    
    def predict_signal(self, X: pd.DataFrame, threshold: float = 0.6) -> int:
        """
        Predict trading signal.
        
        Args:
            X: Feature matrix (single row or multiple rows)
            threshold: Confidence threshold
            
        Returns:
            Signal: 1 (buy), -1 (sell), 0 (hold)
        """
        predictions, probabilities = self.predict(X)
        
        if len(X) == 1:
            pred = predictions[0]
            prob = probabilities[0]
            max_prob = np.max(prob)
            
            if max_prob >= threshold:
                return int(pred)
            else:
                return 0  # Hold if confidence is low
        else:
            # For multiple predictions, return the last one
            return int(predictions[-1])
    
    def save_model(self, name: str = "model"):
        """Save model to disk."""
        model_file = self.model_path / f"{name}.pkl"
        scaler_file = self.model_path / f"{name}_scaler.pkl"
        
        if self.model is not None:
            joblib.dump(self.model, model_file)
            joblib.dump(self.scaler, scaler_file)
            logger.info(f"Model saved to {model_file}")
    
    def load_model(self, name: str = "model") -> bool:
        """
        Load model from disk.
        
        Args:
            name: Model name
            
        Returns:
            True if loaded successfully
        """
        model_file = self.model_path / f"{name}.pkl"
        scaler_file = self.model_path / f"{name}_scaler.pkl"
        
        if model_file.exists() and scaler_file.exists():
            try:
                self.model = joblib.load(model_file)
                self.scaler = joblib.load(scaler_file)
                self.is_trained = True
                logger.info(f"Model loaded from {model_file}")
                return True
            except Exception as e:
                logger.error(f"Error loading model: {e}")
                return False
        return False

